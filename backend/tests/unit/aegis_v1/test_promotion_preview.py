from app.aegis_v1.promotion_preview import US_PLAYBOOK_TITLE, build_promotion_preview
from app.learning.models import (
    Candidate,
    Component,
    ExperimentResult,
    PromotionProposal,
)


def _proposal_with_drafter_change() -> PromotionProposal:
    candidate = Candidate(
        candidate_id="c1",
        components={
            "drafter_system_prompt": Component(
                component_id="drafter_system_prompt",
                kind="prompt",
                version="drafter_v_test",
                text="Revised drafter prompt for showcase review.",
            ),
            "playbook:Cigna:medical_necessity:not_evidence_based": Component(
                component_id="playbook:Cigna:medical_necessity:not_evidence_based",
                kind="playbook",
                version="cigna_v_test",
                playbook={
                    "tactics": ["Quote the cited criteria directly."],
                    "required_evidence": ["physician letter"],
                },
            ),
        },
        origin="reflect",
        diff_summary="Updated drafter and Cigna slice playbook.",
    )
    return PromotionProposal(
        candidate=candidate,
        before=ExperimentResult(candidate_id="seed", dataset_split="pre", composite=0.4),
        after=ExperimentResult(candidate_id="c1", dataset_split="post", composite=0.72),
        per_dimension_deltas={"grounding": 0.1},
        vetoes=[],
    )


def test_build_promotion_preview_includes_changed_sections() -> None:
    preview = build_promotion_preview(_proposal_with_drafter_change())

    assert preview["lift"]["is_promotable"] is True
    kinds = {section["kind"] for section in preview["sections"]}
    assert "drafter" in kinds
    assert "slice_playbook" in kinds
    drafter = next(s for s in preview["sections"] if s["kind"] == "drafter")
    assert drafter["after_text"].startswith("Revised drafter")


def test_us_playbook_rule_diff() -> None:
    from app.aegis_v1.promotion_preview import _us_playbook_rule_changes

    before = {
        "rules": [
            {
                "rule_id": "us_001",
                "scope": "US federal",
                "text": "Old rule text.",
                "status": "active",
            }
        ]
    }
    after = {
        "rules": [
            {
                "rule_id": "us_001",
                "scope": "US federal",
                "text": "Old rule text.",
                "status": "active",
            },
            {
                "rule_id": "us_010",
                "scope": "California",
                "text": "California-only filing note.",
                "status": "active",
            },
        ]
    }
    changes = _us_playbook_rule_changes(before, after)
    assert any(c["change"] == "appended" and c["scope"] == "California" for c in changes)


def test_us_playbook_edit_includes_notice() -> None:
    from app.aegis_v1.promotion_preview import _us_playbook_rule_changes

    before = {"rules": [{"rule_id": "us_001", "scope": "US federal", "text": "Old.", "status": "active"}]}
    after = {"rules": [{"rule_id": "us_001", "scope": "US federal", "text": "New.", "status": "active"}]}
    changes = _us_playbook_rule_changes(before, after)
    assert changes[0]["change"] == "edited"
    assert changes[0].get("notice")


def test_us_playbook_title_constant() -> None:
    assert US_PLAYBOOK_TITLE == "US-playbook"
