from __future__ import annotations

from pathlib import Path


def test_gepa_script_calls_setup_phoenix_telemetry_before_showcase_run() -> None:
    path = Path(__file__).resolve().parents[3] / "scripts" / "run_guinea_pig_gepa.py"
    source = path.read_text(encoding="utf-8")
    setup_at = source.index("setup_phoenix_telemetry()")
    showcase_import_at = source.index("from app.aegis_v1.showcase_manifest")
    session_run_at = source.index("run_guinea_pig_session(")
    assert setup_at < showcase_import_at < session_run_at


def test_setup_phoenix_telemetry_registers_real_provider(monkeypatch) -> None:
    import importlib.util

    path = Path(__file__).resolve().parents[3] / "scripts" / "guinea_pig_common.py"
    spec = importlib.util.spec_from_file_location("guinea_pig_common", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    monkeypatch.setenv("PHOENIX_API_KEY", "test-key")
    monkeypatch.setenv("PHOENIX_HOST", "https://app.phoenix.arize.com")
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "https://example.test/v1/traces")
    monkeypatch.setenv("PHOENIX_PROJECT_NAME", "default")

    mod.setup_phoenix_telemetry()

    from opentelemetry import trace
    from opentelemetry.trace import NoOpTracerProvider

    assert not isinstance(trace.get_tracer_provider(), NoOpTracerProvider)
