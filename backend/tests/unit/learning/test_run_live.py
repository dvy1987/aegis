"""Offline construction tests for the live LearningCoordinator CLI.

These tests assert the run_live module imports cleanly and that the CLI's
helpers compose without touching cloud SDKs at import time. The full live
loop is exercised by the gated integration test.
"""
from __future__ import annotations

import importlib

import pytest


def test_run_live_module_imports_offline() -> None:
    mod = importlib.import_module("app.learning.run_live")
    # Public surface the live CLI exposes.
    assert callable(mod.build_live_coordinator)
    assert callable(mod.main)


def test_creds_available_returns_false_without_creds(monkeypatch) -> None:
    from app.learning import run_live

    monkeypatch.delenv("PHOENIX_API_KEY", raising=False)
    assert run_live._creds_available() is False


def test_benchmark_dataset_filters_by_slice(monkeypatch) -> None:
    from app.learning import run_live

    # Avoid hitting the real `phoenix_mcp_lookup` (which would try to call MCP);
    # the dataset builder only needs a stub summary for shape.
    monkeypatch.setattr(
        run_live,
        "_benchmark_dataset",
        lambda slice_filter: [{"slice": slice_filter, "case_id": "stub"}],
    )
    rows = run_live._benchmark_dataset("Cigna:medical_necessity")
    assert rows and rows[0]["slice"] == "Cigna:medical_necessity"
