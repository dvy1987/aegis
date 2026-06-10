from __future__ import annotations

from app.evals.part_a.deterministic_gates import faithfulness_citation_precheck
from app.evals.part_a.llm_judges import OfflineHeuristicJudgeClient
from app.evals.part_a.panel import run_panel
from app.evals.part_a.schemas import CANONICAL_DISCLAIMER
from app.evals.part_a.teacher_packet import build_teacher_grading_packet


def _case_obj() -> dict:
    return {
        "case_id": "case_07_cigna_mednec",
        "insurer": "Cigna",
        "denial_type": "Medical Necessity",
        "patient_profile": {"plan_funding_type": "self_funded"},
        "denial_pattern_sources": ["missing_erisa_disclosures: DOL EBSA"],
        "denial_letter_text": "Cigna denied A1 pulley release as not medically necessary.",
        "clinical_context": "Trigger finger; failed conservative care.",
        "synthetic_provenance": {
            "matrix_cell": {},
            "appeal_difficulty": {"exploitable_weaknesses": []},
        },
    }


def test_faithfulness_precheck_passes_when_no_structured_citations() -> None:
    appeal = {
        "appeal_package_draft": {
            "appeal_letter": f"{CANONICAL_DISCLAIMER} Appeal text.",
            "citations_used": [],
        }
    }
    teacher = build_teacher_grading_packet(_case_obj(), appeal)

    result = faithfulness_citation_precheck(appeal, teacher)

    assert result.score == "PASS"


def test_faithfulness_precheck_ignores_bad_metadata_citations() -> None:
    appeal = {
        "appeal_package_draft": {
            "appeal_letter": f"{CANONICAL_DISCLAIMER} Appeal text with clinical support.",
            "citations_used": [
                {
                    "corpus_doc_id": "cigna_policy_0000-fake.md",
                    "title": "Fake policy",
                    "quote": "not real",
                }
            ],
        }
    }
    teacher = build_teacher_grading_packet(_case_obj(), appeal)

    result = faithfulness_citation_precheck(appeal, teacher)

    assert result.score == "PASS"
    assert "not scored" in result.reasoning.lower()


def test_faithfulness_precheck_fails_invented_source_in_letter() -> None:
    appeal = {
        "appeal_package_draft": {
            "appeal_letter": (
                f"{CANONICAL_DISCLAIMER} Under 42 U.S.C. 9999 the denial must be overturned."
            ),
            "citations_used": [],
        }
    }
    teacher = build_teacher_grading_packet(_case_obj(), appeal)

    result = faithfulness_citation_precheck(appeal, teacher)

    assert result.score == "FAIL"
    assert "invented" in result.reasoning.lower()


def test_offline_panel_passes_prose_erisa_without_corpus_citation() -> None:
    letter = (
        f"{CANONICAL_DISCLAIMER} Under 29 U.S.C. § 1133, the denial omitted required "
        "ERISA disclosures regarding external review and civil action rights."
    )
    appeal = {
        "appeal_package_draft": {
            "appeal_letter": letter,
            "citations_used": [
                {
                    "corpus_doc_id": "cigna_policy_0000-fake.md",
                    "title": "Wrong insurer metadata",
                    "quote": "ignored",
                }
            ],
            "missing_evidence_checklist": [],
        }
    }
    teacher = build_teacher_grading_packet(_case_obj(), appeal)

    report = run_panel(
        appeal,
        teacher,
        OfflineHeuristicJudgeClient(),
        run_mode="gepa_seed",
    )

    assert report.judge_results["faithfulness_hallucination_gate"].score == "PASS"
