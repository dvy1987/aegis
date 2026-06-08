"""Phase 3: ADK judge-panel Workflow + firewall tests."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types

from app.aegis_v1.adk_runtime import VertexGemini
from app.aegis_v1.student_workflow import build_student_workflow
from app.evals.part_a.judge_agents import AdkJudgeClient, parse_judge_response
from app.evals.part_a.judge_workflow import build_judge_panel_workflow
from app.evals.part_a.llm_judges import OfflineHeuristicJudgeClient
from app.evals.part_a.panel import run_panel
from app.evals.part_a.schemas import CANONICAL_DISCLAIMER
from app.evals.part_a.teacher_packet import build_teacher_grading_packet


class _StubJudgeLlm(VertexGemini):
    """Returns valid JudgeResult JSON for each judge dimension."""

    model: str = "stub-judge"

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r"stub-judge.*"]

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        del stream
        instruction = ""
        for content in llm_request.contents:
            for part in content.parts or []:
                if part.text:
                    instruction += part.text
        dimension = "grounding"
        for key in (
            "faithfulness_hallucination_gate",
            "grounding",
            "case_specific_clinical_rebuttal",
            "evidence_completeness",
            "appeal_vector_capture",
            "persuasive_coherence",
        ):
            if key in instruction:
                dimension = key
                break
        score: Any = "PASS" if dimension == "faithfulness_hallucination_gate" else 3
        payload = {
            "dimension": dimension,
            "reasoning": f"Stub reasoning for {dimension}.",
            "score": score,
            "confidence": 0.75,
            "evidence_quotes": [],
            "improvement": "Stub improvement.",
        }
        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=json.dumps(payload))],
            ),
            partial=False,
        )


def _graph_llm_agent_names(workflow) -> set[str]:
    found: set[str] = set()
    for edge_tuple in workflow.edges:
        for item in edge_tuple:
            if isinstance(item, LlmAgent):
                found.add(item.name)
    return found


def _graph_node_names(workflow) -> set[str]:
    names: set[str] = set()
    for edge_tuple in workflow.edges:
        for item in edge_tuple:
            name = getattr(item, "name", None)
            if name:
                names.add(name)
    return names


def test_judge_workflow_not_reachable_from_student_graph() -> None:
    student_names = _graph_node_names(build_student_workflow())
    judge_names = _graph_node_names(build_judge_panel_workflow()) - {"__START__"}
    assert "judge_panel_workflow" not in student_names
    assert not judge_names & student_names


def test_judge_workflow_includes_six_llm_agents() -> None:
    llm_names = _graph_llm_agent_names(build_judge_panel_workflow())
    assert llm_names == {
        "faithfulness_hallucination_judge",
        "grounding_judge",
        "case_specific_clinical_rebuttal_judge",
        "evidence_completeness_judge",
        "appeal_vector_capture_judge",
        "persuasive_coherence_judge",
    }


def test_run_panel_adk_client_returns_panel_report_shape() -> None:
    case = {
        "case_id": "phase3_adk",
        "insurer": "Cigna",
        "denial_type": "Medical Necessity",
        "patient_profile": {"plan_funding_type": "fully_insured"},
        "denial_letter_text": "Cigna denied IOP.",
        "clinical_context": "Severe OCD with failed outpatient therapy.",
        "denial_pattern_sources": [],
        "synthetic_provenance": {
            "matrix_cell": {},
            "appeal_difficulty": {"exploitable_weaknesses": ["ignored failed therapy"]},
        },
    }
    letter = (
        f"{CANONICAL_DISCLAIMER} I am appealing the denial of IOP. "
        "Six months of weekly outpatient therapy failed. Requested action: approve IOP."
    )
    appeal = {
        "appeal_package_draft": {
            "appeal_letter": letter,
            "citations_used": [
                {"corpus_doc_id": "erisa_503.md", "title": "ERISA", "quote": "review"}
            ],
            "missing_evidence_checklist": ["clinical notes"],
        }
    }
    teacher = build_teacher_grading_packet(case, appeal)
    client = AdkJudgeClient(model=_StubJudgeLlm())

    report = run_panel(appeal, teacher, judge_client=client)

    assert report.verdict == "PASS"
    assert len(report.judge_results) == 7
    assert report.dimension_scores
    assert report.metadata["judge_client"] == "adk"


def test_adk_judge_context_excludes_simulator() -> None:
    """D13: ADK judge workflow state must not include simulator fields."""

    captured: list[str] = []

    class _CapturingStub(_StubJudgeLlm):
        async def generate_content_async(self, llm_request, stream=False):
            for content in llm_request.contents:
                for part in content.parts or []:
                    if part.text:
                        captured.append(part.text)
            async for item in super().generate_content_async(llm_request, stream=stream):
                yield item

    case = {
        "case_id": "judge_adk_firewall",
        "insurer": "Cigna",
        "denial_type": "Medical Necessity",
        "patient_profile": {"plan_funding_type": "fully_insured"},
        "denial_letter_text": "Denied.",
        "clinical_context": "Severe OCD.",
        "denial_pattern_sources": [],
        "synthetic_provenance": {"appeal_difficulty": {}},
    }
    appeal = {
        "appeal_package_draft": {
            "appeal_letter": f"{CANONICAL_DISCLAIMER} Please review.",
            "citations_used": [],
            "missing_evidence_checklist": [],
        },
        "simulator_result": {"verdict": "APPROVE", "score": 0.95},
    }
    teacher = build_teacher_grading_packet(case, appeal)
    run_panel(appeal, teacher, judge_client=AdkJudgeClient(model=_CapturingStub()))
    blob = "\n".join(captured)
    assert "simulator_result" not in blob
    assert "simulator_verdict" not in blob


def test_parse_judge_response_strips_json_fence() -> None:
    raw = """```json
{"dimension": "grounding", "reasoning": "ok", "score": 5, "confidence": 0.9,
 "evidence_quotes": [], "improvement": null}
```"""
    result = parse_judge_response(raw, "grounding")
    assert result.dimension == "grounding"
    assert result.score == 5


def test_offline_panel_still_uses_heuristic_client() -> None:
    case = {
        "case_id": "offline_still",
        "insurer": "Cigna",
        "denial_type": "Medical Necessity",
        "patient_profile": {"plan_funding_type": "fully_insured"},
        "denial_letter_text": "Denied.",
        "clinical_context": "Severe OCD.",
        "denial_pattern_sources": [],
        "synthetic_provenance": {"appeal_difficulty": {}},
    }
    appeal = {
        "appeal_package_draft": {
            "appeal_letter": f"{CANONICAL_DISCLAIMER} Please review.",
            "citations_used": [],
            "missing_evidence_checklist": [],
        }
    }
    teacher = build_teacher_grading_packet(case, appeal)
    report = run_panel(appeal, teacher, OfflineHeuristicJudgeClient())
    assert "offline_scores_not_official" in report.risk_flags
