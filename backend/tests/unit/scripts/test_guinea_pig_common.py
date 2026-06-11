from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_common():
    path = Path(__file__).resolve().parents[3] / "scripts" / "guinea_pig_common.py"
    spec = importlib.util.spec_from_file_location("guinea_pig_common", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_estimate_cost_usd_sums_tracked_calls() -> None:
    mod = _load_common()
    records = [
        {
            "model": "gemini-3.1-pro-preview",
            "prompt_tokens": 1_000_000,
            "output_tokens": 0,
            "total_tokens": 1_000_000,
        },
        {
            "model": "gemini-3.5-flash",
            "prompt_tokens": 0,
            "output_tokens": 1_000_000,
            "total_tokens": 1_000_000,
        },
    ]
    cost = mod.estimate_cost_usd(records)
    assert cost["gemini_calls"] == 2
    assert cost["estimated_total_usd"] == 1.85
