"""Whether costly showcase training runs may be started (preview / production)."""
from __future__ import annotations

import os


def showcase_runs_enabled() -> bool:
    """False when AEGIS_SHOWCASE_RUNS_DISABLED is truthy (set on public Cloud Run)."""
    return os.environ.get("AEGIS_SHOWCASE_RUNS_DISABLED", "").lower() not in {
        "1",
        "true",
        "yes",
    }
