from __future__ import annotations

import json

from google.adk.agents import LlmAgent
from google.genai import types

from app.aegis_v1.adk_runtime import make_retry_model
from app.aegis_v1.schemas import FeatureAssessment
from app.aegis_v1.simulator_client import _build_assess_prompt

_SIMULATOR_INSTRUCTION = """\
You are a strict Insurer Claims Adjuster reviewing an appeal letter.

You can see ONLY the denial letter, clinical context, and appeal letter provided.
First CRITIQUE the appeal, then mark each rubric feature on a 1/3/5 scale with
evidence quoted verbatim from the appeal letter.

Do NOT output a final APPROVE/DENY verdict or numeric composite score.
"""


def build_simulator_agent(*, model=None) -> LlmAgent:
    """Construct the Outcome Simulator ADK agent (single-shot, outside student graph)."""
    return LlmAgent(
        name="simulator_agent",
        model=model or make_retry_model(),
        instruction=_SIMULATOR_INSTRUCTION,
        output_schema=FeatureAssessment,
        generate_content_config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )


def run_simulator_agent(
    *,
    denial_text: str,
    clinical_context: str,
    appeal_letter: str,
    model=None,
) -> FeatureAssessment:
    """Run simulator_agent via ADK and return FeatureAssessment."""
    from app.aegis_v1.adk_runtime import collect_text, run_llm_agent_sync

    agent = build_simulator_agent(model=model)
    message = _build_assess_prompt(denial_text, clinical_context, appeal_letter)
    result = run_llm_agent_sync(
        agent,
        app_name="aegis_v1",
        user_id="simulator",
        message=message,
    )
    raw = collect_text(result.get("events", [])).strip()
    if not raw:
        raise ValueError("simulator_agent returned empty response")
    data = json.loads(raw)
    return FeatureAssessment.model_validate(data)
