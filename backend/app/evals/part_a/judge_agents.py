"""ADK LlmAgent definitions for the Part A judge panel (Phase 3)."""

from __future__ import annotations

import json
import re
from typing import Any

from google.adk.agents import LlmAgent
from google.genai import types

from app.aegis_v1.adk_runtime import make_retry_model
from app.evals.part_a.llm_judges import load_judge_prompt
from app.evals.part_a.schemas import JudgeResult

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

# D17: bias toward verbose reasoning/improvement with soft caps.
_VERBOSITY_SUFFIX = """

When scoring, provide:
- Concrete `reasoning` explaining what worked or failed (2–4 sentences).
- Actionable `improvement` text when score is not perfect (max 3 bullets, 120 chars each).

Return ONLY valid JSON matching the JudgeResult schema for this dimension.
"""

_JUDGE_SPECS: tuple[tuple[str, str, str], ...] = (
    ("j2_faithfulness_hallucination", "faithfulness_hallucination_gate", "faithfulness_hallucination_judge"),
    ("j3_grounding", "grounding", "grounding_judge"),
    ("j4_case_specific_rebuttal", "case_specific_clinical_rebuttal", "case_specific_clinical_rebuttal_judge"),
    ("j5_evidence_completeness", "evidence_completeness", "evidence_completeness_judge"),
    ("j6_appeal_vector_capture", "appeal_vector_capture", "appeal_vector_capture_judge"),
    ("j7_persuasive_coherence", "persuasive_coherence", "persuasive_coherence_judge"),
)

_QUALITY_AGENT_NAMES = frozenset(
    name for _, _, name in _JUDGE_SPECS if name != "faithfulness_hallucination_judge"
)


def judge_instruction(judge_id: str) -> str:
    return load_judge_prompt(judge_id) + _VERBOSITY_SUFFIX


def _normalize_judge_payload(data: dict[str, Any], expected_dimension: str) -> dict[str, Any]:
    """Coerce common Gemini JSON quirks into JudgeResult-compatible fields."""
    payload = dict(data)
    payload["dimension"] = expected_dimension
    payload.setdefault("reasoning", "")

    confidence = payload.get("confidence", 0.5)
    try:
        payload["confidence"] = float(confidence)
    except (TypeError, ValueError):
        payload["confidence"] = 0.5

    improvement = payload.get("improvement")
    if isinstance(improvement, list):
        payload["improvement"] = "; ".join(str(item) for item in improvement if item)
    elif improvement is not None:
        payload["improvement"] = str(improvement)

    quotes = payload.get("evidence_quotes")
    if quotes is None:
        payload["evidence_quotes"] = []
    elif isinstance(quotes, str):
        payload["evidence_quotes"] = [quotes] if quotes.strip() else []
    elif isinstance(quotes, list):
        payload["evidence_quotes"] = [str(q) for q in quotes if q]

    score = payload.get("score")
    if expected_dimension in {"faithfulness_hallucination_gate", "safety_scope_gate"}:
        normalized = str(score or "FAIL").strip().upper()
        payload["score"] = normalized if normalized in {"PASS", "FAIL"} else "FAIL"
    else:
        if isinstance(score, str) and score.strip().isdigit():
            score = int(score.strip())
        if score not in (1, 3, 5):
            if isinstance(score, (int, float)):
                numeric = int(score)
                score = 1 if numeric <= 1 else 3 if numeric <= 3 else 5
            else:
                score = 3
        payload["score"] = score

    return payload


def parse_judge_response(text: str, expected_dimension: str) -> JudgeResult:
    """Parse judge LlmAgent JSON output into JudgeResult."""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError(f"{expected_dimension} judge returned empty response")
    fence = _JSON_FENCE_RE.search(cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError(f"{expected_dimension} judge returned non-object JSON")
    return JudgeResult.model_validate(
        _normalize_judge_payload(data, expected_dimension)
    )


def build_judge_agent(*, judge_id: str, dimension: str, name: str, model: Any | None = None) -> LlmAgent:
    return LlmAgent(
        name=name,
        model=model or make_retry_model(),
        instruction=judge_instruction(judge_id),
        generate_content_config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0,
        ),
    )


def build_faithfulness_judge(*, model: Any | None = None) -> LlmAgent:
    judge_id, dimension, name = _JUDGE_SPECS[0]
    return build_judge_agent(judge_id=judge_id, dimension=dimension, name=name, model=model)


def build_quality_judge_agents(*, model: Any | None = None) -> dict[str, LlmAgent]:
    agents: dict[str, LlmAgent] = {}
    for judge_id, dimension, name in _JUDGE_SPECS[1:]:
        agents[dimension] = build_judge_agent(
            judge_id=judge_id, dimension=dimension, name=name, model=model
        )
    return agents


class AdkJudgeClient:
    """ADK Workflow-backed judge client for production eval paths."""

    name = "adk"

    def __init__(self, model: Any | None = None, location: str = "global") -> None:
        del location  # model wrapper owns transport; kept for GeminiJudgeClient compat.
        self.model = model or make_retry_model()

    def judge(self, judge_id: str, context: dict[str, Any]) -> JudgeResult:
        """Single-judge entry (tests/legacy); production uses judge Workflow batch."""
        from app.evals.part_a.judge_workflow import run_single_judge_sync

        dimension = _dimension_for_judge_id(judge_id)
        return run_single_judge_sync(judge_id=judge_id, dimension=dimension, context=context, model=self.model)


class GeminiJudgeClient(AdkJudgeClient):
    """Backward-compatible alias; uses ADK judge agents under the hood."""

    name = "gemini"

    def __init__(self, model: str | None = None, location: str = "global") -> None:
        import os

        resolved = model or os.environ.get("AEGIS_JUDGE_MODEL", "gemini-3.1-pro-preview")
        super().__init__(model=make_retry_model(model=resolved), location=location)


def _dimension_for_judge_id(judge_id: str) -> str:
    for spec_id, dimension, _ in _JUDGE_SPECS:
        if spec_id == judge_id:
            return dimension
    raise ValueError(f"Unknown judge id: {judge_id}")
