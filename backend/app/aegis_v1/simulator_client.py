from __future__ import annotations

import json
import os
from typing import Any, Protocol

from app.aegis_v1.schemas import AppealDraft, ParsedCase, SimulatorResult

# Weak-v1 demo arc: the Insurer Persona must score a perfect 10 to APPROVE, so the
# deliberately weak baseline reliably DENYs in the simulator during the initial
# demo recording. Do NOT lower without checking the PRD demo arc (Section 15.5).
DEFAULT_SIMULATOR_THRESHOLD = 10


class SimulatorClient(Protocol):
    name: str

    def simulate(
        self, parsed_case: dict[str, Any], appeal_draft: dict[str, Any]
    ) -> dict[str, Any]:
        """Return a SimulatorResult-shaped dict (verdict/score/threshold/features/rationale)."""


class StubSimulatorClient:
    """Deterministic offline Insurer Persona simulator for tests/dry-runs."""

    name = "stub_simulator"

    def __init__(
        self,
        verdict: str = "DENY",
        score: int = 0,
        threshold: int = DEFAULT_SIMULATOR_THRESHOLD,
    ) -> None:
        self.verdict = verdict
        self.score = score
        self.threshold = threshold

    def simulate(self, parsed_case, appeal_draft) -> dict[str, Any]:
        return SimulatorResult(
            verdict=self.verdict,
            score=self.score,
            threshold=self.threshold,
            features={"stub": True},
            rationale=["Deterministic stub simulator outcome (offline)."],
        ).model_dump()


def _build_simulator_prompt(case: ParsedCase, draft: AppealDraft) -> str:
    return f"""
    You are a strict Insurer Claims Adjuster evaluating an appeal.

    Denial Letter you originally sent:
    {case.denial_text}

    Clinical Context provided by provider:
    {case.clinical_context}

    Appeal Letter drafted by the patient's agent:
    {draft.appeal_letter}

    INSTRUCTIONS:
    1. CRITIQUE FIRST: Analyze if the appeal actually addresses your specific denial reason. Does it cite real clinical evidence from the context? Does it cite binding policy?
    2. SCORE: 1 to 10.
    3. VERDICT: "APPROVE" or "DENY".
    NOTE: You look for any reason to DENY unless the appeal is absolutely flawless.
    """


class GeminiSimulatorClient:
    """Vertex/Gemini-backed Insurer Persona simulator. Returns the outcome verdict.

    Live generation is exercised in a GCP integration session; this class is
    unit-tested only for construction/config offline.
    """

    name = "gemini_simulator"

    def __init__(
        self,
        model: str | None = None,
        location: str = "global",
        threshold: int = DEFAULT_SIMULATOR_THRESHOLD,
    ) -> None:
        self.model = model or os.environ.get("AEGIS_SIMULATOR_MODEL", "gemini-3.1-pro")
        self.location = location
        self.threshold = threshold

    def simulate(self, parsed_case, appeal_draft) -> dict[str, Any]:
        from google import genai
        from google.genai import types
        from pydantic import BaseModel, Field
        from typing import Literal

        class LLMSimulatorResponse(BaseModel):
            critique: str = Field(description="Analysis-first critique of the appeal against the denial letter. Be ruthless.")
            score: int = Field(description="Score from 1 to 10, where 10 means undeniable and forces approval.")
            verdict: Literal["APPROVE", "DENY"]
            features_extracted: dict[str, bool] = Field(default_factory=dict, description="Features found in the letter")

        case = ParsedCase.model_validate(parsed_case)
        draft = AppealDraft.model_validate(appeal_draft)
        prompt = _build_simulator_prompt(case, draft)

        try:
            client = genai.Client(vertexai=True, location=self.location)
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=LLMSimulatorResponse,
                    temperature=0.2,
                ),
            )
            data = json.loads(response.text)
            score = data.get("score", 1)
            verdict = "APPROVE" if score >= self.threshold else "DENY"
            return SimulatorResult(
                verdict=verdict,
                score=score,
                threshold=self.threshold,
                features=data.get("features_extracted", {}),
                rationale=[data.get("critique", "No critique provided")],
            ).model_dump()
        except Exception as e:
            # Fallback to a failing deterministic result if the API is unavailable.
            return SimulatorResult(
                verdict="DENY",
                score=0,
                threshold=self.threshold,
                features={"llm_fallback": True},
                rationale=["LLM Insurer Simulator failed.", str(e)],
            ).model_dump()
