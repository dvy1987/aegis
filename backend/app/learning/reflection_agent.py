"""ADK reflector for GEPA component mutation (Phase 4 — outside student graph)."""
from __future__ import annotations

import logging
from typing import Any

from google.adk.agents import LlmAgent
from google.genai import types

from app.aegis_v1.adk_runtime import collect_text, make_retry_model, run_llm_agent_sync
from app.learning.models import Component, DimensionSignal, ScoredRun
from app.learning.reflection_client import (
    ReflectionClient,
    _apply_text_edit,
    build_reflection_prompt,
)

logger = logging.getLogger(__name__)

_REFLECTION_INSTRUCTION = """\
You improve one component of an appeal-drafting system.

Return ONLY the full revised component text (for prompts) or JSON (for playbooks).
Do not wrap the answer in markdown fences unless the component itself requires them.
"""


def build_reflection_agent(*, model: Any | None = None) -> LlmAgent:
    return LlmAgent(
        name="reflection_agent",
        model=model or make_retry_model(),
        instruction=_REFLECTION_INSTRUCTION,
        generate_content_config=types.GenerateContentConfig(temperature=0.7),
    )


def run_reflection_agent(
    *,
    component: Component,
    signal: DimensionSignal,
    minibatch: list[ScoredRun],
    model: Any | None = None,
    variant: str = "base",
) -> str:
    prompt = build_reflection_prompt(
        component=component,
        signal=signal,
        minibatch=minibatch,
        variant=variant,
    )
    agent = build_reflection_agent(model=model)
    result = run_llm_agent_sync(
        agent,
        app_name="aegis_v1",
        user_id="reflection",
        message=prompt,
    )
    text = collect_text(result.get("events", [])).strip()
    if not text:
        raise ValueError("reflection_agent returned empty response")
    return text


class AdkReflectionClient:
    """GEPA reflector via ADK LlmAgent (firewall preserved in build_reflection_prompt)."""

    name = "adk_reflection"

    def __init__(self, model: Any | None = None, *, variant: str = "base") -> None:
        self.model = model
        self.variant = variant

    def reflect(
        self,
        *,
        component: Component,
        signal: DimensionSignal,
        minibatch: list[ScoredRun],
    ) -> Component:
        try:
            revised = run_reflection_agent(
                component=component,
                signal=signal,
                minibatch=minibatch,
                model=self.model,
                variant=self.variant,
            )
            return _apply_text_edit(component, revised)
        except Exception:
            logger.warning(
                "ADK reflection failed for component=%s; returning unchanged",
                component.component_id,
                exc_info=True,
            )
            return component
