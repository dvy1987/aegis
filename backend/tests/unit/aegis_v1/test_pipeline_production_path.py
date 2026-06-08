"""Regression: production paths must not treat GeminiDrafterClient as offline Echo mode."""

from __future__ import annotations

from app.aegis_v1.drafter_client import (
    GeminiDrafterClient,
    StubDrafterClient,
    is_offline_pipeline_client,
)
from app.aegis_v1.pipeline import (
    _clear_workflow_injection,
    _configure_workflow_injection,
)
import app.aegis_v1.student_workflow as _sw


def test_is_offline_pipeline_client_only_stub() -> None:
    assert is_offline_pipeline_client(StubDrafterClient())
    assert not is_offline_pipeline_client(None)
    assert not is_offline_pipeline_client(GeminiDrafterClient())


def test_configure_workflow_injection_production_path() -> None:
    try:
        offline = _configure_workflow_injection(GeminiDrafterClient(), None)
        assert offline is False
        assert _sw._injected_offline_pipeline is False
        assert _sw._injected_drafter_model is None
    finally:
        _clear_workflow_injection()


def test_configure_workflow_injection_offline_stub() -> None:
    try:
        offline = _configure_workflow_injection(StubDrafterClient(), None)
        assert offline is True
        assert _sw._injected_offline_pipeline is True
        assert _sw._injected_drafter_model is not None
    finally:
        _clear_workflow_injection()


def test_configure_workflow_injection_none_is_production() -> None:
    try:
        offline = _configure_workflow_injection(None, None)
        assert offline is False
        assert _sw._injected_drafter_model is None
    finally:
        _clear_workflow_injection()
