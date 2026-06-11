"""Read-only day-zero prompts and playbooks from ``backend/baseline_day_zero/``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.aegis_v1.patient_context import normalize_insurer
from app.aegis_v1.tools import Playbook, _normalize_denial_type, _slug
from app.learning.slice_key import normalize_denial_type_for_slice, playbook_filename

SNAPSHOT_ROOT = Path(__file__).resolve().parents[2] / "baseline_day_zero"
DAY_ZERO_DRAFTER_VERSION = "drafter_v1"


def load_day_zero_drafter_prompt() -> tuple[str, str]:
    path = SNAPSHOT_ROOT / "prompts" / f"{DAY_ZERO_DRAFTER_VERSION}.md"
    if not path.exists():
        raise FileNotFoundError(f"Day-zero drafter prompt missing: {path}")
    return DAY_ZERO_DRAFTER_VERSION, path.read_text(encoding="utf-8")


def _snapshot_playbook_path(insurer: str, denial_type: str, sub_tactic: str = "unknown") -> Path:
    filename = playbook_filename(insurer, denial_type, sub_tactic)
    specific = SNAPSHOT_ROOT / "playbooks" / filename
    if specific.exists():
        return specific
    legacy = (
        SNAPSHOT_ROOT
        / "playbooks"
        / f"{_slug(normalize_insurer(insurer))}__{normalize_denial_type_for_slice(denial_type)}.json"
    )
    return legacy


def load_day_zero_playbook(
    insurer: str,
    denial_type: str,
    *,
    sub_tactic: str = "unknown",
) -> dict[str, Any]:
    path = _snapshot_playbook_path(insurer, denial_type, sub_tactic)
    if not path.exists():
        raise FileNotFoundError(f"Day-zero playbook missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    normalized_type = _normalize_denial_type(denial_type.replace("_", " "))
    if normalized_type == "unknown":
        normalized_type = _slug(denial_type)
    playbook = Playbook(
        insurer=data.get("insurer", insurer),
        denial_type=data.get("denial_type", normalized_type),
        version=data.get("version", "day_zero"),
        status="loaded",
        tactics=data.get("tactics", []),
        required_evidence=data.get("required_evidence", []),
        risk_flags=list(data.get("risk_flags", [])),
    )
    return playbook.model_dump()


def load_day_zero_geo_playbook() -> dict[str, Any]:
    snapshot_path = SNAPSHOT_ROOT / "geo_playbooks" / "us_playbook.json"
    if snapshot_path.exists():
        return json.loads(snapshot_path.read_text(encoding="utf-8"))

    from app.aegis_v1.geo_playbook import load_us_playbook

    data = load_us_playbook()
    rules = [
        rule
        for rule in data.get("rules", [])
        if str(rule.get("added_in_version") or "") == "day_zero"
    ]
    return {
        **data,
        "version": "day_zero",
        "rules": rules,
    }
