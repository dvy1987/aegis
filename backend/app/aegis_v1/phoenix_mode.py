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
