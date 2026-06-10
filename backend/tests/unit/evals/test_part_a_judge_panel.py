from __future__ import annotations

from app.evals.part_a.llm_judges import OfflineHeuristicJudgeClient
from app.evals.part_a.panel import run_panel
from app.evals.part_a.schemas import CANONICAL_DISCLAIMER
from app.evals.part_a.teacher_packet import (
    build_student_case_packet,
    build_teacher_grading_packet,
)


def _case_obj() -> dict:
    return {
        "case_id": "case_01_cigna_mednec",
        "insurer": "Cigna",
        "denial_type": "Medical Necessity",
        "patient_profile": {
            "age": 28,
            "gender": "F",
            "diagnosis": "Severe Obsessive-Compulsive Disorder",
            "treatment_requested": "Intensive Outpatient Program",
            "plan_funding_type": "fully_insured",
        },
        "denial_pattern_sources": ["mhpaea_step_therapy_asymmetry"],
        "denial_letter_references": [
            {
                "ref_id": "cigna-mednec-template",
                "title": "Cigna Medical Necessity Letter Template",
                "url": "https://example.com/cigna-mednec",
                "source_type": "research",
                "relevance": "Synthetic teacher fixture reference.",
            }
        ],
        "denial_letter_text": "Dear Member, Cigna denied IOP as not medically necessary.",
        "clinical_context": (
            "The person has severe OCD, failed weekly outpatient therapy for "
            "six months, and needs IOP because lower-level care has failed."
        ),
        "submission_timestamp": "2026-09-01T10:00:00Z",
        "denial_timestamp": "2026-09-01T10:03:00Z",
        "synthetic_provenance": {
            "matrix_cell": {
                "insurer": "Cigna",
                "denial_type": "Medical Necessity",
                "specialty": "behavioral_health",
                "patient_age_band": "26-40",
                "patient_gender": "F",
                "sub_tactic": "level_of_care_too_high",
            },
            "appeal_difficulty": {
                "score": 5,
                "reasoning": "Lower-level care was already tried and failed.",
                "exploitable_weaknesses": [
                    "The denial ignores six months of failed weekly outpatient therapy.",
                    "The denial applies behavioral health step therapy more stringently.",
                ],
                "strong_defenses": ["The denial cites a generic medical necessity rule."],
            },
        },
    }


def _appeal_package(letter: str, checklist: list[str] | None = None) -> dict:
    return {
        "appeal_package_draft": {
            "appeal_letter": letter,
            "citations_used": [
                {
                    "corpus_doc_id": "erisa_503.md",
                    "title": "ERISA Section 503",
                    "quote": "full and fair review",
                }
            ],
            "missing_evidence_checklist": checklist
            or ["clinical notes", "prior treatment history", "provider letter"],
        }
    }


def test_student_packet_excludes_answer_key() -> None:
    packet = build_student_case_packet(_case_obj())
    dumped = packet.model_dump()

    assert "synthetic_provenance" not in dumped
    assert "appeal_difficulty" not in dumped
    assert "expected_appeal_vectors" not in dumped
    assert dumped["denial_letter_text"]


def test_teacher_packet_includes_answer_key() -> None:
    teacher = build_teacher_grading_packet(_case_obj(), _appeal_package("x"))

    assert teacher.expected_appeal_vectors
    assert teacher.exploitable_weaknesses
    assert teacher.matrix_cell["sub_tactic"] == "level_of_care_too_high"
    assert teacher.denial_letter_references
    assert teacher.denial_letter_references[0]["title"]


def test_teacher_packet_parses_pattern_id_prefixes() -> None:
    case = _case_obj()
    case["denial_pattern_sources"] = [
        "ignored_physician_letter: AMA 2023 Prior Authorization Physician Survey",
        "missing_iro_notice: CMS External Appeal Regulations 45 CFR § 147.136; ACA § 2719",
    ]

    teacher = build_teacher_grading_packet(case, _appeal_package("x"))

    assert any("ignored evidence" in v for v in teacher.expected_appeal_vectors)
    assert any("IRO notice" in v for v in teacher.expected_appeal_vectors)


def test_question_agent_dimension_is_stubbed_at_five() -> None:
    appeal = _appeal_package(f"{CANONICAL_DISCLAIMER} Please review this denial.")
    teacher = build_teacher_grading_packet(_case_obj(), appeal)

    report = run_panel(appeal, teacher, OfflineHeuristicJudgeClient())

    assert report.dimension_scores["question_agent"] == 5
    assert report.judge_results["question_agent"].score == 5
    assert "not yet implemented" in report.judge_results["question_agent"].reasoning.lower()


def test_panel_has_no_safety_scope_gate() -> None:
    appeal = _appeal_package("This appeal will win.")
    teacher = build_teacher_grading_packet(_case_obj(), appeal)

    report = run_panel(appeal, teacher, OfflineHeuristicJudgeClient())

    assert "safety_scope_gate" not in report.judge_results
    assert len(report.judge_results) == 6


def test_panel_runs_offline_and_returns_all_dimensions() -> None:
    letter = (
        f"{CANONICAL_DISCLAIMER} I am appealing Cigna's denial of the "
        "Intensive Outpatient Program. The records show severe OCD and six "
        "months of failed weekly outpatient therapy, so the lower-level care "
        "rationale is incorrect. Under ERISA, please provide a full and fair "
        "review and consider the attached clinical notes. Requested action: "
        "approve the IOP or provide the exact criteria and reviewer credentials."
    )
    appeal = _appeal_package(
        letter,
        ["clinical notes", "prior treatment history", "provider letter", "reviewer credentials"],
    )
    teacher = build_teacher_grading_packet(_case_obj(), appeal)

    report = run_panel(appeal, teacher, OfflineHeuristicJudgeClient())

    assert len(report.judge_results) == 6
    assert report.verdict == "PASS"
    assert report.weighted_quality is not None
    assert "offline_scores_not_official" in report.risk_flags
    assert not any(
        flag.startswith("judge_evidence_quote_not_verbatim")
        for flag in report.risk_flags
    )


def test_appeal_vector_capture_rewards_flaw_aware_letter() -> None:
    teacher = build_teacher_grading_packet(_case_obj(), _appeal_package("x"))
    client = OfflineHeuristicJudgeClient()
    generic = _appeal_package(
        f"{CANONICAL_DISCLAIMER} Please review this medical necessity denial and consider the records."
    )
    flaw_aware = _appeal_package(
        f"{CANONICAL_DISCLAIMER} The denial ignores six months of failed weekly "
        "outpatient therapy and applies behavioral health step therapy more "
        "stringently than comparable medical benefits."
    )

    generic_score = run_panel(generic, teacher, client).dimension_scores[
        "appeal_vector_capture"
    ]
    flaw_score = run_panel(flaw_aware, teacher, client).dimension_scores[
        "appeal_vector_capture"
    ]

    assert flaw_score > generic_score


def test_appeal_vector_score_one_is_promotion_blocker() -> None:
    teacher = build_teacher_grading_packet(_case_obj(), _appeal_package("x"))
    generic = _appeal_package(
        f"{CANONICAL_DISCLAIMER} Please review this medical necessity denial."
    )

    report = run_panel(generic, teacher, OfflineHeuristicJudgeClient())

    assert report.verdict == "PASS"
    assert "appeal_vector_capture_score_1" in report.promotion_blockers
