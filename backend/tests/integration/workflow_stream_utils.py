from __future__ import annotations

from typing import Any


def _text_from_event_dict(event: dict[str, Any]) -> str:
    content = event.get("content") or {}
    parts = content.get("parts") or []
    return "".join(str(part.get("text", "")) for part in parts if part.get("text"))


def _text_from_event_object(event: Any) -> str:
    content = getattr(event, "content", None)
    if not content or not getattr(content, "parts", None):
        return ""
    return "".join(
        part.text for part in content.parts if getattr(part, "text", None)
    )


def stream_has_user_visible_text(events: list[Any]) -> bool:
    """True when ADK stream includes model text (Workflow publish node or LlmAgent)."""
    for event in events:
        if isinstance(event, dict):
            if _text_from_event_dict(event).strip():
                return True
            actions = event.get("actions") or {}
            delta = actions.get("stateDelta") or actions.get("state_delta") or {}
            draft = delta.get("appealDraft") or delta.get("appeal_draft") or {}
            if draft.get("appeal_letter"):
                return True
            continue
        if _text_from_event_object(event).strip():
            return True
        actions = getattr(event, "actions", None)
        delta = getattr(actions, "state_delta", None) if actions else None
        if isinstance(delta, dict):
            draft = delta.get("appeal_draft") or {}
            if draft.get("appeal_letter"):
                return True
    return False
