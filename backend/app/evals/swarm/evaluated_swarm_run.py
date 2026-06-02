"""Eval layer for the Part B swarm — mirrors ``evals.part_a.evaluated_run``.

Student = ``run_swarm_pipeline``; judges + optional simulator live here only.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from app.aegis_swarm.swarm_pipeline import run_swarm_pipeline
from app.evals.part_a.llm_judges import JudgeClient
from app.evals.part_a.panel import run_panel
from app.evals.part_a.recorder import PhoenixRecorder, laundered_signal
from app.evals.part_a.schemas import PanelReport
from app.evals.part_a.teacher_packet import build_teacher_grading_packet

if TYPE_CHECKING:
    from app.aegis_swarm.client import SwarmAgentClient
    from app.aegis_swarm.corpus_store import CorpusStore
    from app.aegis_v1.simulator_client import SimulatorClient


class EvaluatedSwarmRun(BaseModel):
    appeal_package: dict[str, Any]
    artifacts: dict[str, Any] = Field(default_factory=dict)
    panel_report: PanelReport
    simulator_result: dict[str, Any] | None = None
    trace_ref: str


def _swarm_annotation_meta(artifacts: dict[str, Any]) -> dict[str, Any]:
    """Firewall-safe swarm metadata for Phoenix annotations (FR-5)."""
    signals = artifacts.get("agent_trace_signals") or []
    insurer = artifacts.get("insurer_brief") or {}
    return {
        "swarm_agent_trace_count": len(signals),
        "swarm_agent_versions": dict(artifacts.get("agent_versions") or {}),
        "swarm_weak_agents": sorted(
            s.get("role", "") for s in signals if s.get("is_weak_v1")
        ),
        "insurer_phoenix_unavailable": "phoenix_mcp_unavailable"
        in (insurer.get("risk_flags") or []),
    }


def run_evaluated_swarm_case(
    case_obj: dict[str, Any],
    recorder: PhoenixRecorder,
    swarm_client: "SwarmAgentClient | None" = None,
    judge_client: JudgeClient | None = None,
    corpus_store: "CorpusStore | None" = None,
    run_simulator: bool = True,
    simulator_client: "SimulatorClient | None" = None,
    phoenix_lookup: Callable[[str, str, str], dict[str, Any]] | None = None,
) -> EvaluatedSwarmRun:
    """Swarm Student → record run → eval layer (judges [+ simulator]) → annotate trace."""

    pipeline_result = run_swarm_pipeline(
        denial_text=case_obj.get("denial_letter_text", ""),
        clinical_context=case_obj.get("clinical_context", ""),
        case_id=case_obj.get("case_id", "interactive_case"),
        dataset_split=case_obj.get("dataset_split", "benchmark"),
        run_mode="benchmark",
        client=swarm_client,
        corpus_store=corpus_store,
        phoenix_lookup=phoenix_lookup,
    )
    appeal_package = pipeline_result["appeal_package"]
    artifacts = pipeline_result.get("artifacts") or {}

    trace_ref = recorder.record_run(
        appeal_package, appeal_package.get("trace_metadata", {})
    )

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

    letter = appeal_package["appeal_package_draft"]["appeal_letter"]
    annotations = laundered_signal(panel_report, appeal_letter=letter)
    annotations.update(_swarm_annotation_meta(artifacts))
    if simulator_result is not None:
        annotations["simulator_verdict"] = simulator_result["verdict"]
        annotations["simulator_score"] = simulator_result["score"]
    recorder.annotate(trace_ref, annotations)

    return EvaluatedSwarmRun(
        appeal_package=appeal_package,
        artifacts=artifacts,
        panel_report=panel_report,
        simulator_result=simulator_result,
        trace_ref=trace_ref,
    )
