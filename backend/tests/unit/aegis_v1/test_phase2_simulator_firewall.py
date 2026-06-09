"""Phase 2 firewall tests: simulator outside student graph and judge context."""

from __future__ import annotations

import json

from app.aegis_v1.simulator_agent import build_simulator_agent, parse_simulator_response
from app.aegis_v1.student_workflow import build_student_workflow
from app.evals.part_a.llm_judges import OfflineHeuristicJudgeClient
from app.evals.part_a.panel import run_panel
from app.evals.part_a.teacher_packet import build_teacher_grading_packet


def test_simulator_agent_not_in_student_workflow_graph() -> None:
    wf = build_student_workflow()
    names: set[str] = set()
    for edge_tuple in wf.edges:
        for item in edge_tuple:
            name = getattr(item, "name", str(item)).lower()
            names.add(name)
    assert "simulator" not in "".join(names)


def test_judge_panel_context_excludes_simulator_fields() -> None:
    """D13: judges must never receive simulator verdict/score in context."""

    class CapturingJudge(OfflineHeuristicJudgeClient):
        def judge(self, judge_id: str, context: dict) -> object:
            blob = json.dumps(context, default=str)
            assert "simulator_verdict" not in blob
            assert "simulator_score" not in blob
            assert "simulator_result" not in blob
            return super().judge(judge_id, context)

    case = {
        "case_id": "judge_firewall",
        "denial_letter_text": "Cigna denied IOP as not medically necessary.",
        "clinical_context": "Severe OCD.",
        "patient_profile": {},
        "denial_pattern_sources": [],
        "synthetic_provenance": {"appeal_difficulty": {}},
    }
    teacher = build_teacher_grading_packet(case, {"parsed_case": {"case_id": "judge_firewall"}})
    appeal_package = {
        "appeal_package_draft": {
            "appeal_letter": "We appeal the denial with clinical support.",
            "missing_evidence_checklist": [],
            "citations_used": [],
        },
        "simulator_result": {"verdict": "APPROVE", "score": 0.9},
    }
    run_panel(appeal_package, teacher, judge_client=CapturingJudge())


def test_parse_simulator_response_accepts_nested_features() -> None:
    raw = json.dumps(
        {
            "critique": "Weak policy cite.",
            "features": {
                "addresses_denial_rationale": {"anchor": 3, "evidence": "mentions denial"},
                "cites_clinical_evidence": {"anchor": 1, "evidence": ""},
                "cites_binding_policy": {"anchor": 1, "evidence": ""},
                "rebuts_specific_flaw": {"anchor": 1, "evidence": ""},
                "specific_requested_action": {"anchor": 3, "evidence": "asks overturn"},
                "credible_tone": {"anchor": 5, "evidence": "professional"},
            },
        }
    )
    assessment = parse_simulator_response(raw)
    assert assessment.critique == "Weak policy cite."
    assert assessment.features["credible_tone"].anchor == 5


def test_build_simulator_agent_uses_json_mime_without_output_schema() -> None:
    agent = build_simulator_agent()
    assert agent.name == "simulator_agent"
    assert agent.output_schema is None
    assert agent.generate_content_config.response_mime_type == "application/json"
