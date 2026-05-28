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
