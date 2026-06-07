from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, Iterable
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.models import LlmRequest, LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app import gemini_retry
from app.app_utils.vertex_gemini import VertexGemini

logger = logging.getLogger(__name__)


class EchoLlm(VertexGemini):
    """Deterministic fake model for offline ADK smoke tests."""

    model: str = "echo"

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r"echo.*"]

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        del stream
        text = _last_user_text(llm_request) or "echo"
        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=f"echo: {text}")],
            ),
            partial=False,
        )


class RetryFallbackGemini(VertexGemini):
    """Vertex Gemini with gemini_retry pacing, backoff, and model fallback."""

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        primary_model = llm_request.model or self.model
        fallback_model = gemini_retry.fallback_model_name()
        models_to_try = [primary_model]
        if fallback_model and fallback_model != primary_model:
            models_to_try.append(fallback_model)

        last_exc: Exception | None = None
        for model_index, model_name in enumerate(models_to_try):
            request = _request_for_model(llm_request, model_name, use_fallback=model_index > 0)
            try:
                async for response in self._generate_with_retry(request, stream=stream):
                    yield response
                return
            except Exception as exc:
                last_exc = exc
                if model_index == 0 and _should_try_fallback(exc, primary_model, fallback_model):
                    logger.warning(
                        "model %s unavailable; retrying on fallback %s",
                        primary_model,
                        fallback_model,
                    )
                    continue
                raise

        if last_exc is not None:
            raise last_exc

    async def _generate_with_retry(
        self, llm_request: LlmRequest, *, stream: bool
    ) -> AsyncGenerator[LlmResponse, None]:
        max_retries = gemini_retry.max_retries()
        for attempt in range(max_retries + 1):
            await asyncio.to_thread(gemini_retry.pace_gemini_call)
            try:
                async for response in super().generate_content_async(
                    llm_request, stream=stream
                ):
                    yield response
                return
            except Exception as exc:
                if attempt >= max_retries or not gemini_retry.is_retryable(exc):
                    raise
                delay = gemini_retry.backoff_seconds(attempt)
                await asyncio.sleep(delay)


# Plan name alias (D5: custom BaseLlm wrapper).
RetryFallbackLlm = RetryFallbackGemini


def make_retry_model(model: str | None = None) -> RetryFallbackGemini:
    """Factory for the production ADK model wrapper."""
    resolved = model or "gemini-3.1-pro-preview"
    return RetryFallbackGemini(model=resolved)


def run_llm_agent_sync(
    agent: LlmAgent,
    *,
    app_name: str,
    user_id: str,
    message: str,
    initial_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a trivial LlmAgent to completion (Phase 0 smoke helper)."""
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(
        app_name=app_name,
        user_id=user_id,
        state=initial_state or {},
    )
    runner = Runner(agent=agent, session_service=session_service, app_name=app_name)
    content = types.Content(role="user", parts=[types.Part.from_text(text=message)])
    events = list(
        runner.run(user_id=user_id, session_id=session.id, new_message=content)
    )
    updated = session_service.get_session_sync(
        app_name=app_name, user_id=user_id, session_id=session.id
    )
    return {"events": events, "state": updated.state if updated else {}}


def _last_user_text(llm_request: LlmRequest) -> str | None:
    for content in reversed(llm_request.contents):
        if content.role != "user" or not content.parts:
            continue
        for part in content.parts:
            if part.text:
                return part.text
    return None


def _request_for_model(
    llm_request: LlmRequest, model_name: str, *, use_fallback: bool
) -> LlmRequest:
    request = llm_request.model_copy(deep=True)
    request.model = model_name
    if use_fallback:
        request.config = _fallback_config(request.config)
    return request


def _fallback_config(
    config: types.GenerateContentConfig,
) -> types.GenerateContentConfig:
    thinking = types.ThinkingConfig(
        thinking_level=gemini_retry.fallback_thinking_level()
    )
    if config is None:
        return types.GenerateContentConfig(thinking_config=thinking)
    return config.model_copy(update={"thinking_config": thinking})


def _should_try_fallback(
    exc: Exception, primary_model: str, fallback_model: str | None
) -> bool:
    if not fallback_model or fallback_model == primary_model:
        return False
    message = str(exc)
    return ("404" in message or "NOT_FOUND" in message) and "gemini-3.1" in (
        primary_model or ""
    )


def run_workflow_sync(
    workflow: Any,
    *,
    app_name: str = "aegis_v1",
    user_id: str = "pipeline",
    initial_state: dict[str, Any] | None = None,
    message: str = "run",
) -> dict[str, Any]:
    """Run an ADK 2.2 Workflow graph to completion (Phase 1).

    Returns ``{"events": [...], "state": {...}}`` where *state* is the final
    ``ctx.state`` dict after all nodes have executed.
    """
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(
        app_name=app_name,
        user_id=user_id,
        state=initial_state or {},
    )
    runner = Runner(
        agent=workflow,
        session_service=session_service,
        app_name=app_name,
    )
    content = types.Content(
        role="user", parts=[types.Part.from_text(text=message)]
    )
    events = list(
        runner.run(user_id=user_id, session_id=session.id, new_message=content)
    )
    updated = session_service.get_session_sync(
        app_name=app_name, user_id=user_id, session_id=session.id
    )
    return {"events": events, "state": dict(updated.state) if updated else {}}


def collect_text(events: Iterable[Any]) -> str:
    chunks: list[str] = []
    for event in events:
        content = getattr(event, "content", None)
        if not content or not content.parts:
            continue
        for part in content.parts:
            if part.text:
                chunks.append(part.text)
    return "".join(chunks)
