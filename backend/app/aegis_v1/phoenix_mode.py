from __future__ import annotations

from enum import Enum


class PhoenixMode(str, Enum):
    """Controls Phoenix read/write behaviour for a student workflow run."""

    APPEAL = "appeal"
    """Read before draft; write redacted export after draft."""

    HOLDOUT_READONLY = "holdout_readonly"
    """Read allowed; no writes (holdout measure paths)."""

    TRAINING_WRITE = "training_write"
    """Synthetic training checkpoint write (no redaction)."""

    TRAINING_READWRITE = "training_readwrite"
    """Synthetic training: read before draft + write after (checkpoints A/B)."""


_WRITE_MODES = frozenset(
    {PhoenixMode.APPEAL, PhoenixMode.TRAINING_WRITE, PhoenixMode.TRAINING_READWRITE}
)


def can_write_phoenix(mode: PhoenixMode) -> bool:
    """Return True when app-level Phoenix record_run / appeal export is allowed."""
    return mode in _WRITE_MODES


def should_suppress_otel_export(mode: PhoenixMode | None) -> bool:
    """Return True when ADK/OpenInference spans must not be exported (D9 holdout)."""
    return mode == PhoenixMode.HOLDOUT_READONLY
