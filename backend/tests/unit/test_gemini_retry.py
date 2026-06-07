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
