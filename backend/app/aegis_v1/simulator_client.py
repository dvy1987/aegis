from __future__ import annotations

import json
import logging
import os
from typing import Literal, Protocol

from app.aegis_v1.schemas import (
    FeatureAssessment,
    FeatureMark,
)


class SimulatorClient(Protocol):
    name: str

    def assess(
        self, denial_text: str, clinical_context: str, appeal_letter: str
    ) -> FeatureAssessment:
        """Return critique + per-feature 1/3/5 marks (no score, no verdict)."""


def uniform_assessment(anchor: int, critique: str = "stub assessment") -> FeatureAssessment:
    """Return a FeatureAssessment with every rubric feature at the same anchor value.

    Used both as a test fixture and as the safe fallback when LLM scoring is unavailable.
    """
    from app.aegis_v1.simulator_scoring import load_simulator_rules

    rules = load_simulator_rules()
    return FeatureAssessment(
        critique=critique,
        features={name: FeatureMark(anchor=anchor) for name in rules.features},
    )


class StubSimulatorClient:
    """Deterministic offline Insurer Persona simulator for tests/dry-runs."""

    name = "stub_simulator"

    def __init__(self, assessment: FeatureAssessment | None = None) -> None:
        self._assessment = assessment

    def assess(self, denial_text: str, clinical_context: str, appeal_letter: str) -> FeatureAssessment:
        return self._assessment or uniform_assessment(1)


def _build_assess_prompt(denial_text: str, clinical_context: str, appeal_letter: str) -> str:
    return f"""
    You are a strict Insurer Claims Adjuster. You can see ONLY the documents below
    (no answer key). First CRITIQUE the appeal, then mark each feature on a 1/3/5
    scale (1 = absent/poor, 3 = partial, 5 = strong) with a short evidence quote
    taken verbatim from the appeal letter (empty string if absent).

    Features:
    - addresses_denial_rationale: directly engages the specific denial reason.
    - cites_clinical_evidence: cites concrete clinical facts supporting necessity.
    - cites_binding_policy: invokes an applicable policy/plan/regulatory basis.
    - rebuts_specific_flaw: actually rebuts the core defect the denial hinges on.
    - specific_requested_action: makes a clear, specific ask.
    - credible_tone: professional, non-hyperbolic, internally consistent.

    Denial letter you originally sent:
    {denial_text}

    Clinical context provided by the provider:
    {clinical_context}

    Appeal letter drafted by the patient's agent:
    {appeal_letter}

    Critique first, then output the features. Do NOT output a score or verdict.
    """


class GeminiSimulatorClient:
    """Vertex/Gemini-backed Insurer Persona. Emits a critique-first FeatureAssessment
    (per-feature 1/3/5 marks); the APPROVE/DENY verdict is computed downstream by the
    deterministic `score_outcome`, never by this class (INV-S2/S3).

    Live generation is exercised in a GCP integration session; this class is
    unit-tested only for construction/config offline.
    """

    name = "gemini_simulator"

    def __init__(self, model: str | None = None, location: str = "global") -> None:
        self.model = model or os.environ.get("AEGIS_SIMULATOR_MODEL", "gemini-3.1-pro")
        self.location = location

    def assess(self, denial_text: str, clinical_context: str, appeal_letter: str) -> FeatureAssessment:
        from google import genai
        from google.genai import types
        from pydantic import BaseModel, Field

        class _Mark(BaseModel):
            anchor: Literal[1, 3, 5]
            evidence: str = ""

        class _Assessment(BaseModel):
            critique: str = Field(description="Critique the appeal as a strict adjuster BEFORE marking features.")
            addresses_denial_rationale: _Mark
            cites_clinical_evidence: _Mark
            cites_binding_policy: _Mark
            rebuts_specific_flaw: _Mark
            specific_requested_action: _Mark
            credible_tone: _Mark

        keys = [
            "addresses_denial_rationale", "cites_clinical_evidence", "cites_binding_policy",
            "rebuts_specific_flaw", "specific_requested_action", "credible_tone",
        ]
        prompt = _build_assess_prompt(denial_text, clinical_context, appeal_letter)
        try:
            client = genai.Client(vertexai=True, location=self.location)
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_Assessment,
                    temperature=0.2,
                ),
            )
            data = json.loads(response.text)
            return FeatureAssessment(
                critique=data.get("critique", ""),
                features={
                    k: FeatureMark(
                        anchor=data.get(k, {}).get("anchor", 1),
                        evidence=data.get(k, {}).get("evidence", ""),
                    )
                    for k in keys
                },
            )
        except Exception:
            logging.getLogger(__name__).warning(
                "GeminiSimulatorClient.assess failed; falling back to weak assessment",
                exc_info=True,
            )
            return uniform_assessment(1, critique="LLM Insurer Simulator unavailable; treated as weak.")
