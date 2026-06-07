from __future__ import annotations

import pytest
from google.adk.agents import LlmAgent
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types

from app import gemini_retry
from app.aegis_v1.adk_runtime import (
    EchoLlm,
    RetryFallbackGemini,
    collect_text,
    run_llm_agent_sync,
)


@pytest.mark.asyncio
async def test_retry_fallback_gemini_retries_then_succeeds(monkeypatch):
    monkeypatch.setenv("AEGIS_GEMINI_MIN_INTERVAL_SECONDS", "0")
    monkeypatch.setenv("AEGIS_GEMINI_MAX_RETRIES", "2")
    monkeypatch.setenv("AEGIS_GEMINI_BACKOFF_BASE_SECONDS", "0")
    monkeypatch.setenv("AEGIS_GEMINI_BACKOFF_MAX_SECONDS", "0")
    monkeypatch.setenv("AEGIS_GEMINI_BACKOFF_JITTER_SECONDS", "0")

    calls = 0
    model = RetryFallbackGemini(model="gemini-3.1-pro-preview")

    async def flaky_generate(self, llm_request, stream=False):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise RuntimeError("503 UNAVAILABLE")
        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text="ok")],
            ),
            partial=False,
        )

    from google.adk.models.google_llm import Gemini

    monkeypatch.setattr(Gemini, "generate_content_async", flaky_generate)

    request = LlmRequest(
        model="gemini-3.1-pro-preview",
        contents=[
            types.Content(role="user", parts=[types.Part.from_text(text="ping")])
        ],
    )
    responses = [r async for r in model.generate_content_async(request)]
    assert calls == 3
    assert responses[-1].content.parts[0].text == "ok"


@pytest.mark.asyncio
async def test_retry_fallback_gemini_swaps_model_on_not_found(monkeypatch):
    from google.adk.models.google_llm import Gemini

    monkeypatch.setenv("AEGIS_GEMINI_MIN_INTERVAL_SECONDS", "0")
    monkeypatch.setenv("AEGIS_GEMINI_MAX_RETRIES", "0")
    monkeypatch.setenv("AEGIS_FALLBACK_MODEL", "gemini-3.5-flash")

    models_seen: list[str] = []

    async def patched_generate(self, llm_request, stream=False):
        model_name = llm_request.model or self.model
        models_seen.append(model_name)
        if model_name == "gemini-3.1-pro-preview":
            raise RuntimeError("404 NOT_FOUND: model not available")
        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text="fallback-ok")],
            ),
            partial=False,
        )

    monkeypatch.setattr(Gemini, "generate_content_async", patched_generate)

    model = RetryFallbackGemini(model="gemini-3.1-pro-preview")
    request = LlmRequest(model="gemini-3.1-pro-preview", contents=[])
    responses = [r async for r in model.generate_content_async(request)]
    assert models_seen == ["gemini-3.1-pro-preview", "gemini-3.5-flash"]
    assert responses[-1].content.parts[0].text == "fallback-ok"


def test_echo_llm_agent_runs_end_to_end():
    agent = LlmAgent(
        name="phase0_echo",
        model=EchoLlm(model="echo"),
        instruction="Reply using the echo model.",
    )
    result = run_llm_agent_sync(
        agent,
        app_name="phase0_test",
        user_id="tester",
        message="synthetic IOP denial",
    )
    text = collect_text(result["events"])
    assert "echo: synthetic IOP denial" in text


def test_gemini_retry_public_helpers_match_existing_behavior(monkeypatch):
    monkeypatch.setenv("AEGIS_GEMINI_MAX_RETRIES", "2")
    assert gemini_retry.max_retries() == 2
    assert gemini_retry.is_retryable(RuntimeError("503 UNAVAILABLE")) is True
    assert gemini_retry.is_retryable(RuntimeError("403 PERMISSION_DENIED")) is False
