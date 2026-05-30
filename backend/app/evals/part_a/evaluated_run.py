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


def run_evaluated_case(
    case_obj: dict[str, Any],
    recorder: PhoenixRecorder,
    drafter_client: DrafterLLMClient | None = None,
    judge_client: JudgeClient | None = None,
    run_simulator: bool = True,
    simulator_client: "SimulatorClient | None" = None,
) -> EvaluatedRun:
    """Student → record run → eval layer (judges [+ simulator]) → annotate trace."""

    # 1. Student (blind to answer key): produce the appeal package.
    appeal_package = run_aegis_v1_pipeline(
        denial_text=case_obj.get("denial_letter_text", ""),
        clinical_context=case_obj.get("clinical_context", ""),
        case_id=case_obj.get("case_id", "interactive_case"),
        dataset_split=case_obj.get("dataset_split", "benchmark"),
        run_mode="benchmark",
        drafter_client=drafter_client,
    )

    # 2. Record the run trace (tagged metadata) BEFORE evaluation.
    trace_ref = recorder.record_run(appeal_package, appeal_package["trace_metadata"])

    # 3. Eval layer — independent of the Student.
    teacher = build_teacher_grading_packet(case_obj, appeal_package)
    panel_report = run_panel(appeal_package, teacher, judge_client=judge_client)

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
    if simulator_result is not None:
        annotations["simulator_verdict"] = simulator_result["verdict"]
        annotations["simulator_score"] = simulator_result["score"]
    recorder.annotate(trace_ref, annotations)

    return EvaluatedRun(
        appeal_package=appeal_package,
        panel_report=panel_report,
        simulator_result=simulator_result,
        trace_ref=trace_ref,
    )
