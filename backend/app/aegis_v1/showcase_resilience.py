from __future__ import annotations

import math
import os

# --- Minimum training data before GEPA optimization -------------------------

MIN_TRAINING_SUCCESS_RATIO = float(
    os.environ.get("AEGIS_SHOWCASE_MIN_TRAINING_RATIO", "0.5")
)
MIN_TRAINING_SUCCESS_ABSOLUTE = int(
    os.environ.get("AEGIS_SHOWCASE_MIN_TRAINING_CASES", "3")
)


def min_training_cases_required(total: int) -> int:
    """How many training cases must produce judge traces before learning runs."""
    if total <= 0:
        return 0
    by_ratio = max(1, math.ceil(total * MIN_TRAINING_SUCCESS_RATIO))
    if total < MIN_TRAINING_SUCCESS_ABSOLUTE:
        return max(1, by_ratio)
    return max(MIN_TRAINING_SUCCESS_ABSOLUTE, by_ratio)


def insufficient_training_message(*, succeeded: int, required: int, total: int) -> str:
    return (
        f"Not enough training cases succeeded for learning. "
        f"Only {succeeded} of {total} cases produced judge scores; "
        f"need at least {required} before the system can propose an improvement."
    )


def no_learning_signal_message(*, trace_count: int) -> str:
    return (
        f"Judges ran on {trace_count} case(s), but Phoenix did not return a usable "
        "learning signal — no clear weakness to improve on. "
        "Check Phoenix traces or retry the training stage."
    )


def case_failure_message(*, case_id: str, phase: str, error: str) -> str:
    return f"Case {case_id} failed during {phase}: {error}"


# --- Plain-English failure codes shown in the showcase UI -------------------

FAILURE_MESSAGES: dict[str, str] = {
    "missing_live_credentials": (
        "Live credentials are missing. This run needs PHOENIX_API_KEY and "
        "Google application-default credentials."
    ),
    "insufficient_training_data": (
        "Too few training cases produced usable judge scores to learn safely."
    ),
    "no_learning_signal": (
        "Phoenix did not return a usable learning signal after judging."
    ),
    "cancelled": "This run was cancelled and cannot be promoted.",
    "missing_proposal": "No improvement proposal is ready for approval yet.",
}


def failure_message(code: str, *, detail: str | None = None) -> str:
    base = FAILURE_MESSAGES.get(code, detail or code)
    if detail and code in FAILURE_MESSAGES:
        return f"{base} {detail}"
    return base
