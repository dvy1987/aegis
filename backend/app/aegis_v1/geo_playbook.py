"""US-playbook — insurer-agnostic US rules (federal + state-scoped tags)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
US_PLAYBOOK_PATH = REPO_ROOT / "geo_playbooks" / "us_playbook.json"
US_PLAYBOOK_COMPONENT_ID = "geo_playbook:us"
US_PLAYBOOK_DISPLAY_NAME = "US-playbook"


def load_us_playbook() -> dict[str, Any]:
    if US_PLAYBOOK_PATH.exists():
        return json.loads(US_PLAYBOOK_PATH.read_text(encoding="utf-8"))
    return {
        "playbook_id": "us",
        "display_name": US_PLAYBOOK_DISPLAY_NAME,
        "version": "cold-start",
        "rules": [],
    }
