from __future__ import annotations

import json
import logging
import os
from typing import Any, Literal, Protocol

from app.aegis_v1.schemas import (
    AppealDraft,
    FeatureAssessment,
    FeatureMark,
    ParsedCase,
    SimulatorResult,
)

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

    def __init__(
        self,
        verdict: str = "DENY",
        score: int = 0,
        threshold: int = DEFAULT_SIMULATOR_THRESHOLD,
        assessment: FeatureAssessment | None = None,
    ) -> None:
        self.verdict = verdict
        self.score = score
        self.threshold = threshold
        self._assessment = assessment

    def assess(self, denial_text: str, clinical_context: str, appeal_letter: str) -> FeatureAssessment:
        return self._assessment or uniform_assessment(1)

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
