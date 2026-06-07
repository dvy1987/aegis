from __future__ import annotations

from app import gemini_retry


def test_generate_content_with_retry_backs_off_on_retryable_errors(monkeypatch):
    monkeypatch.setenv("AEGIS_GEMINI_MIN_INTERVAL_SECONDS", "0")
    monkeypatch.setenv("AEGIS_GEMINI_MAX_RETRIES", "2")
    monkeypatch.setenv("AEGIS_GEMINI_BACKOFF_BASE_SECONDS", "5")
    monkeypatch.setenv("AEGIS_GEMINI_BACKOFF_MAX_SECONDS", "60")
    monkeypatch.setenv("AEGIS_GEMINI_BACKOFF_JITTER_SECONDS", "0")
    monkeypatch.setattr(gemini_retry.time, "sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(gemini_retry.random, "uniform", lambda low, high: 0)

    sleeps: list[float] = []
    calls = 0

    def flaky_call(**kwargs):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise RuntimeError("503 UNAVAILABLE")
        return kwargs["result"]

    assert gemini_retry.generate_content_with_retry(flaky_call, result="ok") == "ok"
    assert calls == 3
    assert sleeps == [5, 10]


def test_fallback_swaps_model_on_not_found(monkeypatch):
    monkeypatch.setenv("AEGIS_GEMINI_MIN_INTERVAL_SECONDS", "0")
    monkeypatch.setenv("AEGIS_GEMINI_MAX_RETRIES", "0")
    models_tried: list[str] = []
    thinking_levels: list[object] = []

    def call(**kwargs):
        models_tried.append(kwargs["model"])
        config = kwargs.get("config")
        thinking = getattr(config, "thinking_config", None)
        thinking_levels.append(getattr(thinking, "thinking_level", None))
        if kwargs["model"] == "gemini-3.1-pro-preview":
            raise RuntimeError("404 NOT_FOUND: model not available")
        return "ok"

    result = gemini_retry.generate_content_with_fallback(
        call, model="gemini-3.1-pro-preview"
    )
    assert result == "ok"
    assert models_tried == ["gemini-3.1-pro-preview", "gemini-3.5-flash"]
    # The fallback request must carry thinking_level=high.
    fallback_thinking = thinking_levels[-1]
    assert str(getattr(fallback_thinking, "value", fallback_thinking)).lower() == "high"


def test_fallback_does_not_swap_on_other_errors(monkeypatch):
    monkeypatch.setenv("AEGIS_GEMINI_MIN_INTERVAL_SECONDS", "0")
    monkeypatch.setenv("AEGIS_GEMINI_MAX_RETRIES", "0")
    models_tried: list[str] = []

    def call(**kwargs):
        models_tried.append(kwargs["model"])
        raise RuntimeError("403 PERMISSION_DENIED")

    try:
        gemini_retry.generate_content_with_fallback(
            call, model="gemini-3.1-pro-preview"
        )
        raised = False
    except RuntimeError:
        raised = True
    assert raised is True
    assert models_tried == ["gemini-3.1-pro-preview"]
