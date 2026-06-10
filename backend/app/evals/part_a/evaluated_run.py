from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from app.aegis_v1.drafter_client import DrafterLLMClient

if TYPE_CHECKING:
    from app.aegis_v1.simulator_client import SimulatorClient
from app.aegis_v1.pipeline import run_aegis_v1_pipeline
from app.evals.part_a.llm_judges import JudgeClient
from app.evals.part_a.panel import run_panel
from app.evals.part_a.recorder import PhoenixRecorder, laundered_signal
from app.evals.part_a.schemas import PanelReport
from app.evals.part_a.teacher_packet import build_teacher_grading_packet


class EvaluatedRun(BaseModel):
    appeal_package: dict[str, Any]
    panel_report: PanelReport
    simulator_result: dict[str, Any] | None = None
    trace_ref: str
    question_interview: dict[str, Any] | None = None


def _trace_metadata_dict(appeal_package: dict[str, Any], trace_tags: dict[str, Any] | None) -> dict[str, Any]:
    raw = appeal_package.get("trace_metadata") or {}
    if hasattr(raw, "model_dump"):
        meta = dict(raw.model_dump())
    elif isinstance(raw, dict):
        meta = dict(raw)
    else:
        meta = {}
    if trace_tags:
        meta.update({k: str(v) for k, v in trace_tags.items() if v is not None and v != ""})
    return meta


def run_evaluated_case(
    case_obj: dict[str, Any],
    recorder: PhoenixRecorder,
    drafter_client: DrafterLLMClient | None = None,
    judge_client: JudgeClient | None = None,
    run_simulator: bool = True,
    simulator_client: "SimulatorClient | None" = None,
    drafter_prompt_version: str | None = None,
    drafter_prompt_text: str | None = None,
    playbook_override: dict[str, Any] | None = None,
    geo_playbook_override: dict[str, Any] | None = None,
    run_mode: str = "benchmark",
    trace_tags: dict[str, Any] | None = None,
    run_question_agent: bool = False,
    question_agent_client: Any | None = None,
    patient_simulator_client: Any | None = None,
) -> EvaluatedRun:
    """Student → record run → eval layer (judges [+ simulator]) → annotate trace.

    When ``run_question_agent`` is set (showcase), the question agent runs as a
    node INSIDE the Student workflow (after playbook/Phoenix/library prep,
    before the drafter). The patient simulator answers from the teacher
    clinical file, which lives ONLY in the responder closure below — it never
    enters workflow state or the Student's inputs (firewall INV-QA).
    """

    dataset_split = str(case_obj.get("dataset_split", "benchmark"))

    from app.aegis_v1.patient_context import pipeline_inputs_from_case

    student_inputs = pipeline_inputs_from_case(case_obj)

    question_responder = None
    if run_question_agent:
        from app.aegis_v1.patient_simulator import GeminiPatientSimulatorClient
        from app.aegis_v1.question_agent import responder_from_simulator

        simulator = patient_simulator_client or GeminiPatientSimulatorClient()
        question_responder = responder_from_simulator(
            simulator,
            clinical_context=str(case_obj.get("clinical_context") or ""),
            patient_profile=case_obj.get("patient_profile"),
        )

    # 1. Student (blind to answer key): produce the appeal package. The
    #    question agent runs inside this workflow when enabled.
    appeal_package = run_aegis_v1_pipeline(
        **student_inputs,
        dataset_split=dataset_split,
        run_mode=run_mode,
        drafter_client=drafter_client,
        drafter_prompt_version=drafter_prompt_version,
        drafter_prompt_text=drafter_prompt_text,
        playbook_override=playbook_override,
        geo_playbook_override=geo_playbook_override,
        run_question_agent=run_question_agent,
        question_responder=question_responder,
        question_agent_client=question_agent_client,
    )

    question_interview: dict[str, Any] | None = appeal_package.get("question_interview")
    if question_interview:
        trace_tags = {
            **(trace_tags or {}),
            "question_turn_count": len(question_interview.get("qa_transcript") or []),
            "question_skipped": bool(question_interview.get("skipped")),
        }

    # 2. Record the run trace (tagged metadata) BEFORE evaluation.
    trace_ref = recorder.record_run(
        appeal_package,
        _trace_metadata_dict(appeal_package, trace_tags),
    )

    # 3. Eval layer — independent of the Student.
    teacher = build_teacher_grading_packet(case_obj, appeal_package)
    panel_report = run_panel(
        appeal_package,
        teacher,
        judge_client=judge_client,
        run_mode=run_mode,
        question_interview=question_interview,
    )

    simulator_result = None
    if run_simulator:
        from app.aegis_v1.tools import simulator
        simulator_result = simulator(
            parsed_case=appeal_package["parsed_case"],
            appeal_draft=appeal_package["appeal_package_draft"],
            self_check_result=appeal_package["self_check"],
            client=simulator_client,
        )

    # 4. Annotate the trace with the LAUNDERED signal + sim verdict (INV-2/INV-3).
    letter = appeal_package["appeal_package_draft"]["appeal_letter"]
    trace_meta = _trace_metadata_dict(appeal_package, trace_tags)
    parsed = appeal_package.get("parsed_case") or {}
    from app.learning.slice_key import format_slice_key, sub_tactic_from_case

    trace_meta.setdefault("case_id", str(parsed.get("case_id") or case_obj.get("case_id") or ""))
    trace_meta.setdefault("insurer", str(parsed.get("insurer") or ""))
    trace_meta.setdefault("denial_type", str(parsed.get("denial_type") or ""))
    sub_tactic = sub_tactic_from_case(case_obj)
    trace_meta.setdefault("sub_tactic", sub_tactic)
    if trace_meta.get("insurer") and trace_meta.get("denial_type"):
        trace_meta.setdefault(
            "slice",
            format_slice_key(
                str(trace_meta["insurer"]),
                str(trace_meta["denial_type"]),
                sub_tactic,
            ),
        )
    raw_tm = appeal_package.get("trace_metadata")
    if not trace_meta.get("prompt_version") and raw_tm is not None:
        trace_meta["prompt_version"] = str(
            getattr(raw_tm, "prompt_version", None) or (raw_tm or {}).get("prompt_version") or ""
        )
    if not trace_meta.get("playbook_version") and raw_tm is not None:
        trace_meta["playbook_version"] = str(
            getattr(raw_tm, "playbook_version", None) or (raw_tm or {}).get("playbook_version") or ""
        )
    annotations = laundered_signal(
        panel_report,
        appeal_letter=letter,
        trace_metadata=trace_meta,
    )
    recorder.annotate(trace_ref, annotations)

    return EvaluatedRun(
        appeal_package=appeal_package,
        panel_report=panel_report,
        simulator_result=simulator_result,
        trace_ref=trace_ref,
        question_interview=question_interview,
    )
