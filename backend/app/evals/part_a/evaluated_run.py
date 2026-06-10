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
    run_mode: str = "benchmark",
    trace_tags: dict[str, Any] | None = None,
) -> EvaluatedRun:
    """Student → record run → eval layer (judges [+ simulator]) → annotate trace."""

    dataset_split = str(case_obj.get("dataset_split", "benchmark"))

    from app.aegis_v1.patient_context import pipeline_inputs_from_case

    student_inputs = pipeline_inputs_from_case(case_obj)

    # 1. Student (blind to answer key): produce the appeal package.
    appeal_package = run_aegis_v1_pipeline(
        **student_inputs,
        dataset_split=dataset_split,
        run_mode=run_mode,
        drafter_client=drafter_client,
        drafter_prompt_version=drafter_prompt_version,
        drafter_prompt_text=drafter_prompt_text,
        playbook_override=playbook_override,
    )

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
    annotations = laundered_signal(panel_report, appeal_letter=letter)
    recorder.annotate(trace_ref, annotations)

    return EvaluatedRun(
        appeal_package=appeal_package,
        panel_report=panel_report,
        simulator_result=simulator_result,
        trace_ref=trace_ref,
    )
