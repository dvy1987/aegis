"""Per-judge context shaping (firewall what each dimension may see)."""

from __future__ import annotations

from typing import Any

_GROUNDING_TEACHER_KEYS = (
    "case_id",
    "denial_letter_text",
    "denial_letter_references",
    "patient_profile",
)


def grounding_judge_context(context: dict[str, Any]) -> dict[str, Any]:
    """J3 scores letter prose only — strip teacher answer-key fields from context."""
    teacher = context.get("teacher_packet") or {}
    slim_teacher = (
        {k: teacher[k] for k in _GROUNDING_TEACHER_KEYS if k in teacher}
        if isinstance(teacher, dict)
        else {}
    )
    return {
        "appeal_package": context.get("appeal_package"),
        "teacher_packet": slim_teacher,
        "deterministic_results": context.get("deterministic_results", {}),
    }
