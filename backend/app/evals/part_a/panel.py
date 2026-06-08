from __future__ import annotations

from typing import Any

from app.evals.part_a.deterministic_gates import citation_precheck
from app.evals.part_a.deterministic_gates import safety_scope_gate
from app.evals.part_a.llm_judges import JudgeClient
from app.evals.part_a.llm_judges import OfflineHeuristicJudgeClient
from app.evals.part_a.schemas import JudgeResult
from app.evals.part_a.schemas import PanelReport
from app.evals.part_a.schemas import TeacherGradingPacket


QUALITY_WEIGHTS = {
    "grounding": 0.30,
    "case_specific_clinical_rebuttal": 0.20,
    "evidence_completeness": 0.15,
    "appeal_vector_capture": 0.25,
    "persuasive_coherence": 0.10,
}

JUDGE_IDS = {
    "faithfulness_hallucination_gate": "j2_faithfulness_hallucination",
    "grounding": "j3_grounding",
    "case_specific_clinical_rebuttal": "j4_case_specific_rebuttal",
    "evidence_completeness": "j5_evidence_completeness",
    "appeal_vector_capture": "j6_appeal_vector_capture",
    "persuasive_coherence": "j7_persuasive_coherence",
}


def _normalize_anchor(score: int) -> float:
    return {1: 0.2, 3: 0.6, 5: 1.0}[score]


def _score_int(result: JudgeResult) -> int | None:
    return result.score if isinstance(result.score, int) else None


def _quote_pool(appeal_package: dict[str, Any], teacher: TeacherGradingPacket) -> str:
    draft = appeal_package.get("appeal_package_draft", {})
    parts = [
        str(draft.get("appeal_letter", "")),
        " ".join(str(item) for item in draft.get("missing_evidence_checklist", []) or []),
        teacher.denial_letter_text,
        teacher.clinical_context,
        teacher.insurer,
        teacher.denial_type,
        " ".join(teacher.denial_pattern_sources),
        " ".join(teacher.expected_appeal_vectors),
        " ".join(teacher.exploitable_weaknesses),
        " ".join(teacher.strong_defenses),
    ]
    parts.extend(str(value) for value in teacher.patient_profile.values())
    parts.extend(str(value) for value in teacher.matrix_cell.values())
    for excerpt in teacher.corpus_excerpts:
        parts.extend([excerpt.corpus_doc_id, excerpt.title, excerpt.quote])
    return "\n".join(part for part in parts if part)


def _evidence_quote_risk_flags(
    judge_results: dict[str, JudgeResult],
    appeal_package: dict[str, Any],
    teacher: TeacherGradingPacket,
) -> list[str]:
    pool = _quote_pool(appeal_package, teacher)
    risks: list[str] = []
    for dimension, result in judge_results.items():
        for quote in result.evidence_quotes:
            if quote and quote not in pool:
                risks.append(f"judge_evidence_quote_not_verbatim:{dimension}")
                break
    return risks


def run_panel(
    appeal_package: dict[str, Any],
    teacher_packet: TeacherGradingPacket | dict[str, Any],
    judge_client: JudgeClient | None = None,
) -> PanelReport:
    """Run the Part A judge panel over one appeal package."""

    teacher = (
        teacher_packet
        if isinstance(teacher_packet, TeacherGradingPacket)
        else TeacherGradingPacket.model_validate(teacher_packet)
    )
    client = judge_client or OfflineHeuristicJudgeClient()

    j1 = safety_scope_gate(appeal_package, teacher)
    citation = citation_precheck(appeal_package, teacher)
    student_package = {
        k: v for k, v in appeal_package.items() if k != "simulator_result"
    }
    context = {
        "appeal_package": student_package,
        "teacher_packet": teacher.model_dump(),
        "deterministic_results": {
            "safety_scope_gate": j1.model_dump(),
            "citation_precheck": citation.model_dump(),
        },
    }

    judge_results: dict[str, JudgeResult] = {"safety_scope_gate": j1}

    if citation.score == "FAIL":
        j2 = JudgeResult(
            dimension="faithfulness_hallucination_gate",
            reasoning=citation.reasoning,
            score="FAIL",
            confidence=citation.confidence,
            evidence_quotes=citation.evidence_quotes,
            improvement=citation.improvement,
        )
    else:
        j2 = client.judge(JUDGE_IDS["faithfulness_hallucination_gate"], context)
    judge_results["faithfulness_hallucination_gate"] = j2

    for dimension in QUALITY_WEIGHTS:
        judge_results[dimension] = client.judge(JUDGE_IDS[dimension], context)

    hard_gate_failures = [
        dimension
        for dimension in ("safety_scope_gate", "faithfulness_hallucination_gate")
        if judge_results[dimension].score == "FAIL"
    ]

    dimension_scores: dict[str, int] = {}
    weighted_quality: float | None = None
    if not hard_gate_failures:
        weighted_quality = 0.0
        for dimension, weight in QUALITY_WEIGHTS.items():
            score = _score_int(judge_results[dimension])
            if score is None:
                hard_gate_failures.append(f"{dimension}_non_numeric_score")
                weighted_quality = None
                break
            dimension_scores[dimension] = score
            weighted_quality += weight * _normalize_anchor(score)
        if weighted_quality is not None:
            weighted_quality = round(weighted_quality, 4)
    else:
        for dimension in QUALITY_WEIGHTS:
            score = _score_int(judge_results[dimension])
            if score is not None:
                dimension_scores[dimension] = score

    promotion_blockers: list[str] = []
    if dimension_scores.get("appeal_vector_capture") == 1:
        promotion_blockers.append("appeal_vector_capture_score_1")

    risk_flags = list(teacher.risk_flags)
    risk_flags.extend(_evidence_quote_risk_flags(judge_results, appeal_package, teacher))
    if getattr(client, "name", "") == "offline_heuristic_diagnostic_only":
        risk_flags.append("offline_scores_not_official")
    if getattr(client, "name", "") == "gemini":
        risk_flags.append("same_model_drafting_and_judging")

    verdict = "FAIL" if hard_gate_failures else "PASS"

    return PanelReport(
        case_id=teacher.case_id,
        verdict=verdict,
        weighted_quality=weighted_quality,
        hard_gate_failures=hard_gate_failures,
        promotion_blockers=promotion_blockers,
        dimension_scores=dimension_scores,
        judge_results=judge_results,
        weights=QUALITY_WEIGHTS,
        risk_flags=sorted(set(risk_flags)),
        metadata={
            "judge_client": getattr(client, "name", "unknown"),
            "model_constraint": "Gemini 3.1 Pro accepted for both drafting and judging",
        },
    )
