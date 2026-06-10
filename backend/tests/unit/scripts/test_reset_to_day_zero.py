from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_reset_module():
    path = Path(__file__).resolve().parents[3] / "scripts" / "reset_to_day_zero.py"
    spec = importlib.util.spec_from_file_location("reset_to_day_zero", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_planned_copies_include_all_day_zero_prompts() -> None:
    mod = _load_reset_module()
    pairs = mod._planned_copies()
    dest_names = {dest.name for _, dest in pairs}

    assert "drafter_v1.md" in dest_names
    assert "question_agent_v1.md" in dest_names
    assert "search_planner_v1.md" in dest_names
    assert "active_drafter_prompt.txt" in dest_names
    assert "active_question_agent_prompt.txt" in dest_names


def test_snapshot_has_all_day_zero_prompt_sources() -> None:
    mod = _load_reset_module()
    mod._verify_snapshot(mod._planned_copies())
