"""Phase 1 gap C: holdout measure must not export ADK/OTEL spans to Phoenix."""

from __future__ import annotations

from contextlib import nullcontext

from app.aegis_v1.adk_runtime import run_workflow_sync
from app.aegis_v1.drafter_client import StubDrafterClient
from app.aegis_v1.phoenix_mode import PhoenixMode, should_suppress_otel_export
from app.aegis_v1.student_workflow import build_student_workflow
import app.aegis_v1.pipeline as pipeline_mod


def test_should_suppress_otel_export_only_on_holdout() -> None:
    assert should_suppress_otel_export(PhoenixMode.HOLDOUT_READONLY) is True
    assert should_suppress_otel_export(PhoenixMode.APPEAL) is False
    assert should_suppress_otel_export(PhoenixMode.TRAINING_WRITE) is False
    assert should_suppress_otel_export(None) is False


def test_run_workflow_sync_holdout_enters_suppress_instrumentation(monkeypatch) -> None:
    entered: list[bool] = []

    class _FakeSuppress:
        def __enter__(self):
            entered.append(True)
            return self

        def __exit__(self, *args):
            return False

    def fake_suppress():
        return _FakeSuppress()

    monkeypatch.setattr(
        "opentelemetry.instrumentation.utils.suppress_instrumentation",
        fake_suppress,
    )

    pipeline_mod._configure_workflow_injection(StubDrafterClient(), None)
    try:
        run_workflow_sync(
            build_student_workflow(),
            app_name="aegis_v1",
            user_id="holdout_otel",
            initial_state={
                "denial_text": "Cigna denied IOP.",
                "clinical_context": "Severe OCD.",
                "phoenix_mode": PhoenixMode.HOLDOUT_READONLY.value,
            },
            phoenix_mode=PhoenixMode.HOLDOUT_READONLY,
        )
    finally:
        pipeline_mod._clear_workflow_injection()

    assert entered == [True]


def test_run_workflow_sync_appeal_does_not_suppress_otel(monkeypatch) -> None:
    entered: list[bool] = []

    class _FakeSuppress:
        def __enter__(self):
            entered.append(True)
            return self

        def __exit__(self, *args):
            return False

    def fake_suppress():
        return _FakeSuppress()

    monkeypatch.setattr(
        "opentelemetry.instrumentation.utils.suppress_instrumentation",
        fake_suppress,
    )

    pipeline_mod._configure_workflow_injection(StubDrafterClient(), None)
    try:
        run_workflow_sync(
            build_student_workflow(),
            app_name="aegis_v1",
            user_id="appeal_otel",
            initial_state={
                "denial_text": "Cigna denied IOP.",
                "clinical_context": "Severe OCD.",
                "phoenix_mode": PhoenixMode.APPEAL.value,
            },
            phoenix_mode=PhoenixMode.APPEAL,
        )
    finally:
        pipeline_mod._clear_workflow_injection()

    assert entered == []
