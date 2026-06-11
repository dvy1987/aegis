from __future__ import annotations

from typing import Any

from app.evals.part_a.deterministic_gates import citation_precheck
from app.evals.part_a.judge_context import grounding_judge_context
from app.evals.part_a.judge_agents import AdkJudgeClient
from app.evals.part_a.judge_workflow import run_judge_panel_workflow
from app.evals.part_a.llm_judges import JudgeClient
from app.evals.part_a.llm_judges import OfflineHeuristicJudgeClient
from app.evals.part_a.question_judge import judge_question_interview
from app.evals.part_a.schemas import JudgeResult
from app.evals.part_a.schemas import PanelReport
from app.evals.part_a.schemas import TeacherGradingPacket
from app.learning.models import DIMENSION_WEIGHTS as QUALITY_WEIGHTS

HARD_GATE_DIMENSIONS = ("faithfulness_hallucination_gate",)

JUDGE_IDS = {
    "faithfulness_hallucination_gate": "j2_faithfulness_hallucination",
    "grounding": "j3_grounding",
    "case_specific_clinical_rebuttal": "j4_case_specific_rebuttal",
    "appeal_vector_capture": "j6_appeal_vector_capture",
    "persuasive_coherence": "j7_persuasive_coherence",
}


def _normalize_anchor(score: int, *, dimension: str | None = None) -> float:
    if dimension == "appeal_vector_capture":
        return {1: 0.2, 2: 0.4, 3: 0.6, 4: 0.8, 5: 1.0}.get(score, 0.2)
    return {1: 0.2, 3: 0.6, 5: 1.0}.get(score, 0.2)


def _score_int(result: JudgeResult) -> int | None:
    return result.score if isinstance(result.score, int) else None


def _judge_visible_appeal_package(appeal_package: dict[str, Any]) -> dict[str, Any]:
    """Appeal package copy for judges: letter prose only, no librarian metadata."""
    pkg = {k: v for k, v in appeal_package.items() if k != "simulator_result"}
    draft = dict(pkg.get("appeal_package_draft", {}))
    draft.pop("citations_used", None)
    pkg["appeal_package_draft"] = draft
    return pkg


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


def _build_panel_report(
    *,
    appeal_package: dict[str, Any],
    teacher: TeacherGradingPacket,
    judge_results: dict[str, JudgeResult],
    client: JudgeClient,
    extra_metadata: dict[str, Any] | None = None,
) -> PanelReport:
    hard_gate_failures = [
        dimension
        for dimension in HARD_GATE_DIMENSIONS
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
            weighted_quality += weight * _normalize_anchor(score, dimension=dimension)
        if weighted_quality is not None:
            weighted_quality = round(weighted_quality, 4)
    else:
        for dimension in QUALITY_WEIGHTS:
            score = _score_int(judge_results[dimension])
            if score is not None:
                dimension_scores[dimension] = score

    promotion_blockers: list[str] = []
    avc = dimension_scores.get("appeal_vector_capture")
    if avc == 1:
        promotion_blockers.append("appeal_vector_capture_score_1")
    elif avc == 2:
        promotion_blockers.append("appeal_vector_capture_mentioned_not_rebutted")

    risk_flags = list(teacher.risk_flags)
    risk_flags.extend(_evidence_quote_risk_flags(judge_results, appeal_package, teacher))
    if getattr(client, "name", "") == "offline_heuristic_diagnostic_only":
        risk_flags.append("offline_scores_not_official")
    if getattr(client, "name", "") in {"gemini", "adk"}:
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
            **(extra_metadata or {}),
        },
    )


def _student_context(
    appeal_package: dict[str, Any],
    teacher: TeacherGradingPacket,
) -> dict[str, Any]:
    citation = citation_precheck(appeal_package, teacher)
    return {
        "appeal_package": _judge_visible_appeal_package(appeal_package),
        "teacher_packet": teacher.model_dump(),
        "deterministic_results": {"citation_precheck": citation.model_dump()},
    }


def _run_panel_offline(
    appeal_package: dict[str, Any],
    teacher: TeacherGradingPacket,
    client: OfflineHeuristicJudgeClient,
    question_interview: dict[str, Any] | None = None,
) -> PanelReport:
    context = _student_context(appeal_package, teacher)
    citation = citation_precheck(appeal_package, teacher)

    judge_results: dict[str, JudgeResult] = {}

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
        if dimension == "question_agent":
            continue
        judge_ctx = (
            grounding_judge_context(context)
            if dimension == "grounding"
            else context
        )
        judge_results[dimension] = client.judge(JUDGE_IDS[dimension], judge_ctx)
    question = judge_question_interview(question_interview, teacher=teacher)
    judge_results["question_agent"] = question.result

    return _build_panel_report(
        appeal_package=appeal_package,
        teacher=teacher,
        judge_results=judge_results,
        client=client,
        extra_metadata={
            "question_graded": question.graded,
            "question_playbook_additions": question.playbook_additions,
            "question_substantive_questions": question.substantive_questions,
            "question_gap_questions": question.gap_questions,
        },
    )


def _fresh_adk_judge_model(client: AdkJudgeClient):
    """New model instance per panel run — avoids shared async state under burst load."""
    import os

    from app.aegis_v1.adk_runtime import RetryFallbackGemini, make_retry_model

    if client.model is not None and not isinstance(client.model, RetryFallbackGemini):
        return client.model
    resolved = getattr(client.model, "model", None) or os.environ.get(
        "AEGIS_JUDGE_MODEL", "gemini-3.1-pro-preview"
    )
    return make_retry_model(model=str(resolved))


def _run_panel_adk(
    appeal_package: dict[str, Any],
    teacher: TeacherGradingPacket,
    client: AdkJudgeClient,
    question_interview: dict[str, Any] | None = None,
) -> PanelReport:
    context = _student_context(appeal_package, teacher)
    judge_results = run_judge_panel_workflow(
        context=context,
        model=_fresh_adk_judge_model(client),
    )
    # Live panel → LLM question judge (offline fallback inside on failure).
    question = judge_question_interview(
        question_interview, teacher=teacher, use_llm=True
    )
    judge_results["question_agent"] = question.result
    return _build_panel_report(
        appeal_package=appeal_package,
        teacher=teacher,
        judge_results=judge_results,
        client=client,
        extra_metadata={
            "question_graded": question.graded,
            "question_playbook_additions": question.playbook_additions,
            "question_substantive_questions": question.substantive_questions,
            "question_gap_questions": question.gap_questions,
        },
    )


def run_panel(
    appeal_package: dict[str, Any],
    teacher_packet: TeacherGradingPacket | dict[str, Any],
    judge_client: JudgeClient | None = None,
    *,
    run_mode: str | None = None,
    question_interview: dict[str, Any] | None = None,
) -> PanelReport:
    """Run the Part A judge panel over one appeal package.

    ``question_interview`` is the showcase pre-draft interview artifact; when
    present the question_agent dimension is graded for real (appeal runs pass
    None and receive the neutral default — traced, not graded).
    """

    del run_mode  # retained for call-site compatibility; safety gate removed from panel
    teacher = (
        teacher_packet
        if isinstance(teacher_packet, TeacherGradingPacket)
        else TeacherGradingPacket.model_validate(teacher_packet)
    )
    client = judge_client or OfflineHeuristicJudgeClient()

    if isinstance(client, OfflineHeuristicJudgeClient):
        return _run_panel_offline(appeal_package, teacher, client, question_interview)
    if isinstance(client, AdkJudgeClient):
        return _run_panel_adk(appeal_package, teacher, client, question_interview)

    raise TypeError(
        f"Unsupported judge client type: {type(client).__name__}. "
        "Use OfflineHeuristicJudgeClient or AdkJudgeClient."
    )
