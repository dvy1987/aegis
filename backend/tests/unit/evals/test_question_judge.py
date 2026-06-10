"""Question-agent judge tests: showcase = graded, appeal = not graded.

Part A grades the interview transcript; Part B mines regulatory/insurer/legal
facts from the hidden teacher clinical file into targeted append-first
playbook instructions (offline deterministic path — the LLM judge falls back
to this on failure).
"""

from __future__ import annotations

from typing import Any

from app.evals.part_a.question_judge import (
    advises_regulatory_patient_ask,
    extract_playbook_additions,
    filter_question_agent_reflection_notes,
    judge_question_interview,
    sanitize_question_agent_improvement,
)
from app.evals.part_a.schemas import TeacherGradingPacket

TEACHER = TeacherGradingPacket(
    case_id="case_qa_1",
    insurer="Cigna",
    denial_type="medical_necessity",
    denial_letter_text="Cigna denied TMS as not medically necessary.",
    clinical_context=(
        "Patient tried two SSRIs without improvement. "
        "Cigna plan policy requires step therapy documentation under coverage criteria. "
        "ERISA section 1133 statute requires a full and fair review on appeal."
    ),
    matrix_cell={"sub_tactic": "step_therapy"},
)


def _interview(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "qa_transcript": [
            {
                "turn": 1,
                "question": "When did your symptoms start?",
                "answer": "About a year ago; they affect work daily.",
            },
            {
                "turn": 2,
                "question": "Have you tried other treatments?",
                "answer": "Two SSRIs failed before this.",
            },
        ],
        "planned_questions": [
            "When did your symptoms start?",
            "Have you tried other treatments?",
            "Do you have recent medical records or test results?",
        ],
        "patient_gap_note": "",
        "internal_gap_analysis": "",
        "skipped": False,
    }
    base.update(overrides)
    return base


def test_no_interview_is_neutral_and_not_graded() -> None:
    out = judge_question_interview(None)
    assert out.graded is False
    assert out.result.score == 5  # appeal = traced, not graded; composite unchanged
    assert out.playbook_additions == []


def test_good_showcase_interview_scores_5_and_is_graded() -> None:
    out = judge_question_interview(_interview())
    assert out.graded is True
    assert out.result.score == 5
    assert out.result.dimension == "question_agent"
    assert len(out.substantive_questions) == 2
    assert "Do you have recent medical records" in " ".join(out.gap_questions)


def test_regulatory_question_is_firewall_breach_score_1() -> None:
    out = judge_question_interview(
        _interview(
            qa_transcript=[
                {
                    "turn": 1,
                    "question": "What is the plan language on coverage criteria?",
                    "answer": "I wouldn't know.",
                }
            ]
        )
    )
    assert out.result.score == 1
    assert "firewall" in out.result.reasoning.lower()


def test_skipped_interview_scores_3() -> None:
    out = judge_question_interview(_interview(qa_transcript=[], skipped=True))
    assert out.result.score == 3


def test_part_b_mines_regulatory_facts_from_teacher_file() -> None:
    out = judge_question_interview(_interview(), teacher=TEACHER)
    assert out.playbook_additions
    # Insurer/plan-specific rule -> targeted slice playbook instruction.
    assert any(
        a.startswith("Add to playbook:") and "Cigna" in a and "step therapy" in a
        for a in out.playbook_additions
    )
    # Broad legal/regulatory rule -> global playbook instruction.
    assert any(
        a.startswith("Add to global playbook") and "ERISA" in a
        for a in out.playbook_additions
    )
    # Rides the laundered improvement note into Phoenix/GEPA.
    assert out.result.improvement is not None
    assert "Playbook additions" in out.result.improvement


def test_part_b_ignores_plain_clinical_facts() -> None:
    additions = extract_playbook_additions(TEACHER)
    assert not any("SSRIs" in a for a in additions)


def test_no_teacher_means_no_playbook_additions() -> None:
    out = judge_question_interview(_interview())
    assert out.playbook_additions == []


def test_bad_improvement_suggesting_regulatory_ask_is_dropped() -> None:
    out = sanitize_question_agent_improvement(
        "Ask the patient about the plan coverage criteria on step therapy.",
        playbook_additions=[],
    )
    assert out is None


def test_playbook_additions_never_route_to_question_agent_improvement_as_ask() -> None:
    additions = ["Add to playbook:Cigna:medical_necessity:step_therapy: require step therapy doc"]
    out = sanitize_question_agent_improvement(
        "Ask the patient what the plan says about step therapy.",
        playbook_additions=additions,
    )
    assert out is not None
    assert out.startswith("Playbook additions")
    assert "Ask the patient" not in out


def test_filter_question_agent_reflection_notes_strips_playbook_and_regulatory_asks() -> None:
    notes = [
        "Playbook additions (append-first): Add to global playbook: ERISA 1133",
        "Ask the patient about filing deadlines for this insurer.",
        "Probe symptom timeline more directly before stopping.",
    ]
    filtered = filter_question_agent_reflection_notes(notes)
    assert filtered == ["Probe symptom timeline more directly before stopping."]
    assert advises_regulatory_patient_ask("Ask the patient about coverage criteria.")


def test_non_substantive_answers_score_low() -> None:
    out = judge_question_interview(
        _interview(
            qa_transcript=[
                {"turn": 1, "question": "When did your symptoms start?", "answer": "I don't know"},
                {"turn": 2, "question": "Have you tried other treatments?", "answer": ""},
            ]
        )
    )
    assert out.result.score == 1
