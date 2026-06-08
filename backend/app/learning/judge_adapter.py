"""Adapt the Part-A judge panel to the ExperimentRunner judge_client.score() contract
(used by LiveExperimentRunner). Offline-testable with OfflineHeuristicJudgeClient;
inject GeminiJudgeClient for the live loop. The teacher packet (answer key) is built
here — judges legitimately see it; the drafter never calls this."""
from __future__ import annotations

from typing import Any


class PanelJudgeAdapter:
    name = "panel_judge_adapter"

    def __init__(self, judge_client: Any | None = None) -> None:
        self.judge_client = judge_client  # None -> run_panel uses OfflineHeuristicJudgeClient

    def score(self, *, case: dict[str, Any], appeal_letter: str) -> dict[str, Any]:
        from app.evals.part_a.panel import run_panel
        from app.evals.part_a.teacher_packet import build_teacher_grading_packet

        appeal_package = {"appeal_package_draft": {
            "appeal_letter": appeal_letter, "missing_evidence_checklist": [], "citations_used": []}}
        teacher = build_teacher_grading_packet(case.get("_teacher_case") or case)
        report = run_panel(appeal_package, teacher, judge_client=self.judge_client)
        return {
            "dimension_scores": dict(report.dimension_scores),
            "hard_gate_pass": report.verdict == "PASS",
            "weighted_quality": report.weighted_quality,
        }
