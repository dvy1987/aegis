from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent

from app.aegis_v1.adk_runtime import make_retry_model

_DRAFTER_INSTRUCTION = """\
You are a health-insurance appeal letter drafter.

Write the appeal letter body based on the prompt and context in the user message.
Not legal or medical advice. Draft assistance only.

Return only the appeal letter body text — no JSON wrapper, no commentary.
"""


def build_v1_drafter_agent(*, model: Any | None = None) -> LlmAgent:
    """Construct the v1 drafter ADK agent for use as a Workflow graph node."""
    return LlmAgent(
        name="v1_drafter_agent",
        model=model or make_retry_model(),
        instruction=_DRAFTER_INSTRUCTION,
    )
