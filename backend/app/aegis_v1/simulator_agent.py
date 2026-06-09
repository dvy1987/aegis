from __future__ import annotations

import json
import re
from typing import Any

from google.adk.agents import LlmAgent
from google.genai import types

from app.aegis_v1.adk_runtime import make_retry_model
from app.aegis_v1.schemas import FeatureAssessment, FeatureMark
from app.aegis_v1.simulator_client import _build_assess_prompt
from app.aegis_v1.simulator_scoring import load_simulator_rules

_SIMULATOR_INSTRUCTION = """\
You are a strict Insurer Claims Adjuster reviewing an appeal letter.

You can see ONLY the denial letter, clinical context, and appeal letter provided.
First CRITIQUE the appeal, then mark each rubric feature on a 1/3/5 scale with
evidence quoted verbatim from the appeal letter.

Return JSON with:
- "critique": string
- "features": object mapping each feature name to {"anchor": 1|3|5, "evidence": "..."}

Do NOT output a final APPROVE/DENY verdict or numeric composite score.
"""

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

_FEATURE_KEYS = tuple(load_simulator_rules().features.keys())


def parse_simulator_response(text: str) -> FeatureAssessment:
    """Parse simulator LlmAgent JSON (nested or legacy flat feature keys)."""
    cleaned = text.strip()
    fence = _JSON_FENCE_RE.search(cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    data = json.loads(cleaned)

    if "features" in data and isinstance(data["features"], dict):
        return FeatureAssessment.model_validate(data)

    features: dict[str, FeatureMark] = {}
    for key in _FEATURE_KEYS:
        mark = data.get(key)
        if not isinstance(mark, dict):
            continue
        raw_anchor = mark.get("anchor", 1)
        anchor = int(raw_anchor) if not isinstance(raw_anchor, str) else int(raw_anchor)
        features[key] = FeatureMark(anchor=anchor, evidence=str(mark.get("evidence", "")))
    return FeatureAssessment(critique=str(data.get("critique", "")), features=features)


def build_simulator_agent(*, model: Any | None = None) -> LlmAgent:
    """Construct the Outcome Simulator ADK agent (single-shot, outside student graph)."""
    # Do not set output_schema here — ADK structured output often leaves
    # event.content.parts empty, which broke collect_text() in production.
    # Match the judge-panel pattern: JSON mime + parse_simulator_response().
    return LlmAgent(
        name="simulator_agent",
        model=model or make_retry_model(),
        instruction=_SIMULATOR_INSTRUCTION,
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
    model: Any | None = None,
) -> FeatureAssessment:
    """Run simulator_agent via ADK and return FeatureAssessment."""
    from app.aegis_v1.adk_runtime import collect_llm_response_text, run_llm_agent_sync

    agent = build_simulator_agent(model=model)
    message = _build_assess_prompt(denial_text, clinical_context, appeal_letter)
    result = run_llm_agent_sync(
        agent,
        app_name="aegis_v1",
        user_id="simulator",
        message=message,
    )
    raw = collect_llm_response_text(
        result.get("events", []),
        state=result.get("state"),
    ).strip()
    if not raw:
        raise ValueError("simulator_agent returned empty response")
    return parse_simulator_response(raw)
