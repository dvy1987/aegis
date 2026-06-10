from app.aegis_v1.geo_playbook import (
    applicable_geo_rules,
    geo_playbook_for_case,
    question_agent_prep_bundle,
)


def test_applicable_geo_rules_includes_federal_only_when_no_state() -> None:
    playbook = {
        "rules": [
            {"rule_id": "us_001", "scope": "US federal", "text": "Federal.", "status": "active"},
            {"rule_id": "us_002", "scope": "California", "text": "CA only.", "status": "active"},
        ]
    }
    rules = applicable_geo_rules(playbook, {})
    assert [r["rule_id"] for r in rules] == ["us_001"]


def test_geo_playbook_for_case_filters_rules() -> None:
    payload = geo_playbook_for_case({})
    assert payload["display_name"] == "US-playbook"
    assert payload["rules"]


def test_question_agent_prep_bundle_includes_us_playbook(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.aegis_v1.tools.insurer_playbook_bundle",
        lambda insurer: {"insurer": insurer, "playbooks": [{"tactics": []}], "count": 1},
    )
    bundle = question_agent_prep_bundle("Aetna")
    assert bundle["insurer"] == "Aetna"
    assert "us_playbook" in bundle
    assert bundle["us_playbook"]["rules"]
