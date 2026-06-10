"""US-playbook — insurer-agnostic US rules (federal + state-scoped tags)."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
US_PLAYBOOK_PATH = REPO_ROOT / "geo_playbooks" / "us_playbook.json"
US_PLAYBOOK_COMPONENT_ID = "geo_playbook:us"
US_PLAYBOOK_DISPLAY_NAME = "US-playbook"
_DEFAULT_GEO = "us"


def load_us_playbook() -> dict[str, Any]:
    if US_PLAYBOOK_PATH.exists():
        return json.loads(US_PLAYBOOK_PATH.read_text(encoding="utf-8"))
    return {
        "playbook_id": "us",
        "display_name": US_PLAYBOOK_DISPLAY_NAME,
        "version": "cold-start",
        "rules": [],
    }


def resolve_us_state(case: dict[str, Any]) -> str | None:
    """v1: cases do not carry state yet."""
    profile = case.get("patient_profile") or {}
    if isinstance(profile, dict):
        raw = profile.get("us_state") or profile.get("state")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    raw = case.get("us_state")
    return str(raw).strip() if raw else None


def resolve_plan_funding_type(case: dict[str, Any]) -> str | None:
    profile = case.get("patient_profile") or {}
    if isinstance(profile, dict):
        raw = profile.get("plan_funding_type")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


def _scope_matches(rule_scope: str, state: str | None) -> bool:
    scope = (rule_scope or "").strip()
    if not scope or scope.lower() in {"us federal", "us_federal", "federal"}:
        return True
    if state is None:
        return False
    return scope.lower() == state.lower()


def _funding_matches(rule_funding: str | None, funding: str | None) -> bool:
    if not rule_funding:
        return True
    if funding is None:
        return True
    return rule_funding.strip().lower() == funding.strip().lower()


def applicable_geo_rules(playbook: dict[str, Any], case: dict[str, Any]) -> list[dict[str, Any]]:
    """Return active rules that apply to this case's geography and funding."""
    state = resolve_us_state(case)
    funding = resolve_plan_funding_type(case)
    out: list[dict[str, Any]] = []
    for rule in playbook.get("rules") or []:
        if not isinstance(rule, dict):
            continue
        if str(rule.get("status") or "active") != "active":
            continue
        if not _scope_matches(str(rule.get("scope") or "US federal"), state):
            continue
        if not _funding_matches(rule.get("funding_scope"), funding):
            continue
        out.append(rule)
    return out


def geo_playbook_for_case(
    case: dict[str, Any],
    *,
    override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Filtered US-playbook payload for drafting / question-agent prep."""
    raw = override if override is not None else load_us_playbook()
    rules = applicable_geo_rules(raw, case)
    return {
        "playbook_id": raw.get("playbook_id", "us"),
        "display_name": raw.get("display_name", US_PLAYBOOK_DISPLAY_NAME),
        "version": raw.get("version", "cold-start"),
        "geo": _DEFAULT_GEO,
        "rules": rules,
    }


def question_agent_prep_bundle(
    insurer: str,
    *,
    us_playbook_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Insurer playbooks plus US-playbook for question-agent prep."""
    from app.aegis_v1.tools import insurer_playbook_bundle

    insurer_bundle = insurer_playbook_bundle(insurer)
    us_raw = us_playbook_override if us_playbook_override is not None else load_us_playbook()
    # Question agent runs before denial type is reliable — include all active US rules.
    us_rules = [
        r
        for r in (us_raw.get("rules") or [])
        if isinstance(r, dict) and str(r.get("status") or "active") == "active"
    ]
    return {
        **insurer_bundle,
        "us_playbook": {
            "playbook_id": us_raw.get("playbook_id", "us"),
            "display_name": us_raw.get("display_name", US_PLAYBOOK_DISPLAY_NAME),
            "version": us_raw.get("version", "cold-start"),
            "rules": us_rules,
        },
    }


def next_rule_id(playbook: dict[str, Any]) -> str:
    rules = playbook.get("rules") or []
    max_n = 0
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        match = re.match(r"us_(\d+)$", str(rule.get("rule_id") or ""))
        if match:
            max_n = max(max_n, int(match.group(1)))
    return f"us_{max_n + 1:03d}"


def bump_geo_version(version: str) -> str:
    if version.startswith("geo_v") and version[5:].isdigit():
        return f"geo_v{int(version[5:]) + 1}"
    if version.startswith("v") and version[1:].isdigit():
        return f"v{int(version[1:]) + 1}"
    return f"{version}+1"


def append_us_rule(
    playbook: dict[str, Any],
    *,
    text: str,
    scope: str = "US federal",
    funding_scope: str | None = None,
    version: str,
) -> dict[str, Any]:
    """Append-first helper for reflection stubs and offline tests."""
    pb = copy.deepcopy(playbook)
    rules = list(pb.get("rules") or [])
    entry: dict[str, Any] = {
        "rule_id": next_rule_id(pb),
        "scope": scope,
        "text": text.strip(),
        "status": "active",
        "added_in_version": version,
    }
    if funding_scope:
        entry["funding_scope"] = funding_scope
    rules.append(entry)
    pb["rules"] = rules
    pb["version"] = version
    return pb
