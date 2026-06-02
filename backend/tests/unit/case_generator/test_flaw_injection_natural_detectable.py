from __future__ import annotations

from app.case_generator.aplus.flaws import inject_flaws


def test_inject_flaws_includes_natural_detectable_anchors() -> None:
    brief = {
        "diagnosis": "Test diagnosis (X00.0)",
        "treatment_requested": "Test treatment",
        "intended_flaw_types": [],
    }
    base_letter = (
        "EXPLANATION OF DECISION\n"
        "The documentation submitted does not demonstrate that the service is medically necessary.\n\n"
        "Clinical policy applied: Coverage Policy 101 under Cigna Medical Coverage Policy.\n\n"
        "APPEAL RIGHTS\n"
        "You have the right to appeal this determination.\n"
    )
    out = inject_flaws(
        letter=base_letter,
        context="ctx",
        brief=brief,
        patterns=[
            {"id": "circular_medical_necessity", "source": "src"},
            {"id": "appeal_closed_as_withdrawn", "source": "src"},
            {"id": "wrong_benefit_category", "source": "src"},
            {"id": "superseded_guideline", "source": "src"},
        ],
        index=1,
    )
    letter = out["denial_letter_text"].lower()
    assert "plan's medical necessity criteria" in letter
    assert "administratively closed as withdrawn" in letter
    assert "benefit category classification" in letter
    assert "superseded guideline reference" in letter

