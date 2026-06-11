from __future__ import annotations

from app.aegis_v1.day_zero_snapshot import (
    load_day_zero_drafter_prompt,
    load_day_zero_geo_playbook,
    load_day_zero_playbook,
)


def test_load_day_zero_drafter_prompt() -> None:
    version, text = load_day_zero_drafter_prompt()
    assert version == "drafter_v1"
    assert "weak baseline" in text.lower() or len(text) > 40


def test_load_day_zero_playbook_for_aetna_prior_auth() -> None:
    playbook = load_day_zero_playbook("Aetna", "prior_authorization")
    assert playbook["version"] == "day_zero"
    assert playbook["insurer"] == "Aetna"


def test_load_day_zero_geo_playbook_has_day_zero_rules() -> None:
    geo = load_day_zero_geo_playbook()
    assert geo["version"] == "day_zero"
    assert geo["rules"]
