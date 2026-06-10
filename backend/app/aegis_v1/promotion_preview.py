"""Human-readable promotion preview for showcase approval UI."""

from __future__ import annotations

from typing import Any

from app.learning.models import Component, PromotionProposal
from app.learning.slice_key import parse_slice_key


US_PLAYBOOK_TITLE = "US-playbook"
US_PLAYBOOK_COMPONENT_ID = "geo_playbook:us"


def _rule_index(playbook: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not playbook:
        return {}
    rules = playbook.get("rules") or []
    out: dict[str, dict[str, Any]] = {}
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        rule_id = str(rule.get("rule_id") or "")
        if rule_id:
            out[rule_id] = rule
    return out


def _us_playbook_rule_changes(
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    before_rules = _rule_index(before)
    after_rules = _rule_index(after)
    changes: list[dict[str, Any]] = []

    for rule_id, rule in after_rules.items():
        prior = before_rules.get(rule_id)
        if prior is None:
            changes.append(
                {
                    "change": "appended",
                    "rule_id": rule_id,
                    "scope": rule.get("scope", "US federal"),
                    "funding_scope": rule.get("funding_scope"),
                    "text": str(rule.get("text") or ""),
                    "justification": rule.get("edit_justification") or rule.get("justification"),
                }
            )
            continue
        if prior.get("status") == "revoked" and rule.get("status") != "revoked":
            continue
        if prior.get("text") != rule.get("text") or prior.get("status") != rule.get("status"):
            change_type = "edited" if rule.get("status") != "revoked" else "revoked"
            changes.append(
                {
                    "change": change_type,
                    "rule_id": rule_id,
                    "scope": rule.get("scope", prior.get("scope", "US federal")),
                    "funding_scope": rule.get("funding_scope", prior.get("funding_scope")),
                    "before_text": str(prior.get("text") or ""),
                    "text": str(rule.get("text") or ""),
                    "justification": rule.get("edit_justification")
                    or rule.get("revoke_justification")
                    or rule.get("justification"),
                    "notice": (
                        "This changes an existing US rule — review the justification "
                        "before approving."
                    ),
                }
            )

    for rule_id, prior in before_rules.items():
        if rule_id in after_rules:
            continue
        if prior.get("status") == "revoked":
            continue
        changes.append(
            {
                "change": "removed",
                "rule_id": rule_id,
                "scope": prior.get("scope", "US federal"),
                "funding_scope": prior.get("funding_scope"),
                "before_text": str(prior.get("text") or ""),
                "text": "",
                "notice": (
                    "A rule was removed from the proposed playbook — review before approving."
                ),
            }
        )
    return changes


def _load_baseline_component(component_id: str) -> Component:
    from app.aegis_v1.drafter_client import get_active_drafter_prompt_version, load_drafter_prompt
    from app.aegis_v1.tools import playbook_loader

    if component_id == "drafter_system_prompt":
        version = get_active_drafter_prompt_version()
        return Component(
            component_id=component_id,
            kind="prompt",
            version=version,
            text=load_drafter_prompt(version),
        )
    if component_id.startswith("playbook:"):
        slice_key = component_id.removeprefix("playbook:")
        insurer, denial_type, sub_tactic = parse_slice_key(slice_key)
        raw = playbook_loader(insurer, denial_type, sub_tactic=sub_tactic)
        return Component(
            component_id=component_id,
            kind="playbook",
            version=str(raw.get("version") or "baseline"),
            playbook=raw,
        )
    if component_id == US_PLAYBOOK_COMPONENT_ID:
        from app.aegis_v1.geo_playbook import load_us_playbook

        raw = load_us_playbook()
        return Component(
            component_id=component_id,
            kind="playbook",
            version=str(raw.get("version") or "baseline"),
            playbook=raw,
        )
    return Component(component_id=component_id, kind="playbook", version="unknown")


def _slice_playbook_title(component_id: str) -> str:
    slice_key = component_id.removeprefix("playbook:")
    parts = slice_key.split(":")
    if len(parts) >= 3:
        return f"{parts[0]} · {parts[1].replace('_', ' ')} · {parts[2].replace('_', ' ')}"
    return slice_key.replace(":", " · ").replace("_", " ")


def _component_changed(before: Component, after: Component) -> bool:
    if before.version != after.version:
        return True
    if before.text != after.text:
        return True
    return before.playbook != after.playbook


def build_promotion_preview(proposal: PromotionProposal) -> dict[str, Any]:
    """Structured diff for the showcase approval modal."""
    sections: list[dict[str, Any]] = []

    for component_id, after in proposal.candidate.components.items():
        before = _load_baseline_component(component_id)
        if not _component_changed(before, after):
            continue

        if component_id == "drafter_system_prompt":
            sections.append(
                {
                    "kind": "drafter",
                    "title": "Drafter prompt",
                    "before_version": before.version,
                    "after_version": after.version,
                    "before_text": before.text or "",
                    "after_text": after.text or "",
                }
            )
            continue

        if component_id == US_PLAYBOOK_COMPONENT_ID:
            sections.append(
                {
                    "kind": "us_playbook",
                    "title": US_PLAYBOOK_TITLE,
                    "before_version": before.version,
                    "after_version": after.version,
                    "rule_changes": _us_playbook_rule_changes(before.playbook, after.playbook),
                    "after_playbook": after.playbook,
                }
            )
            continue

        if component_id.startswith("playbook:"):
            sections.append(
                {
                    "kind": "slice_playbook",
                    "title": _slice_playbook_title(component_id),
                    "slice_key": component_id.removeprefix("playbook:"),
                    "before_version": before.version,
                    "after_version": after.version,
                    "before_playbook": before.playbook,
                    "after_playbook": after.playbook,
                }
            )

    return {
        "lift": {
            "before_composite": proposal.before.composite,
            "after_composite": proposal.after.composite,
            "delta": round(proposal.after.composite - proposal.before.composite, 4),
            "per_dimension_deltas": proposal.per_dimension_deltas,
            "vetoes": proposal.vetoes,
            "is_promotable": proposal.is_promotable,
            "diff_summary": proposal.candidate.diff_summary,
            "candidate_id": proposal.candidate.candidate_id,
        },
        "sections": sections,
    }
