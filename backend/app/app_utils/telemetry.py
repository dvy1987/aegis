from __future__ import annotations

import os

from phoenix.otel import register


def setup_telemetry() -> None:
    os.environ.setdefault("PHOENIX_PROJECT_NAME", "default")
    os.environ.setdefault(
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "true"
    )

    register(
        auto_instrument=True,
        batch=True,
        verbose=True,
        protocol="http/protobuf",
    )


def flush_phoenix_telemetry(*, timeout_millis: int = 30_000) -> None:
    """Push batched OTEL spans to Phoenix before the learning loop reads them."""
    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        force_flush = getattr(provider, "force_flush", None)
        if callable(force_flush):
            force_flush(timeout_millis=timeout_millis)
    except Exception:
        return
