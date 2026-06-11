from __future__ import annotations

import json
import logging
import os
from typing import Any, Literal, Protocol

from app.aegis_v1.schemas import (
    FeatureAssessment,
    FeatureMark,
)


class SimulatorClient(Protocol):
    name: str

    def assess(self, denial_text: str, appeal_letter: str) -> FeatureAssessment:
        """Return critique + per-feature 1/3/5 marks (no score, no verdict).

        Insurer-visible inputs only: the denial letter and appeal letter (INV-S4).
        """


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

    def assess(self, denial_text: str, appeal_letter: str) -> FeatureAssessment:
        return self._assessment or uniform_assessment(1)


def _simulator_profile() -> str:
    return os.environ.get("AEGIS_SIMULATOR_PROFILE", "").strip().lower()


def _build_demo_assess_prompt(denial_text: str, appeal_letter: str) -> str:
    return f"""
    You are a Utilization Management reviewer scoring a draft appeal for a showcase demo.
    Credit good-faith medical-necessity arguments when the letter engages the denial with
    patient-specific facts, a clear overturn ask, and professional tone. Default to partial
    credit (anchor 3) when work is directionally right but thin; use 5 when strong.

    Score features 1/3/5. Leave unrebutted_denial_points empty when the letter makes a
    reasonable attempt to address the main denial hooks (demo leniency).

    Denial letter:
    {denial_text}

    Appeal letter:
    {appeal_letter}

    Critique first, then output features. Do NOT output a score or verdict.
    """


def _build_assess_prompt(denial_text: str, appeal_letter: str) -> str:
    if _simulator_profile() == "demo":
        return _build_demo_assess_prompt(denial_text, appeal_letter)
    return f"""
    You are a skeptical Utilization Management reviewer. Your job is to UPHOLD the
    denial unless the appeal proves — with specific documented facts in the letter —
    that the determination was wrong. Default stance: deny. Look for the slightest
    gap, deferral, or hand-wave.

    You see ONLY the denial letter and appeal letter — what a Utilization Management
    reviewer would see. No teacher packet, parsed case metadata, or backend citation
    attachments. Credit clinical facts only when they appear in the appeal letter
    itself — not from assumptions or unstated records.

    Scoring discipline (1 = absent/poor, 3 = partial/generic, 5 = strong/specific).
    Each feature is weighted in the published rubric — partial credit is allowed:
    - addresses_denial_rationale: engages each denial reason; 5 = all rebutted.
    - rebuts_specific_flaw: 5 = every denial hook factually rebutted in the letter.
    - cites_clinical_evidence: 5 only for concrete patient-specific facts IN THE APPEAL
      LETTER (symptoms, scores, failed treatments, diagnosis, age, protocol). Promises
      that records "will be submitted" or "are attached" without summarizing facts = 1.
    - medical_director_persuasion: 5 if a skeptical medical director would overturn
      from the clinical argument IN THE LETTER; 1 for boilerplate or deferrals only.
    - cites_applicable_authority: 5 when the letter cites NO external authority, OR when
      EVERY authority named is real, fairly represented, and applicable. Score below 5
      only for false, invented, wrong-insurer, or misrepresented sources invoked.
    - cites_binding_policy: 5 when no binding policy is invoked, OR when invoked policy
      is accurately applied to THIS case — not generic padding without case tie-in.
    - specific_requested_action: clear overturn/reprocess ask.
    - credible_tone: professional and internally consistent.

    Quote evidence verbatim from the appeal letter (empty string if absent).

    After marking features, list "unrebutted_denial_points": denial hooks still not
    rebutted with concrete facts in the letter ([] when all are rebutted). This list
    is advisory for the critique — the composite score comes from weighted anchors only.

    Denial letter you originally sent:
    {denial_text}

    Appeal letter drafted by the patient's agent:
    {appeal_letter}

    Critique first, then output the features. Do NOT output a score or verdict.
    """


class AdkSimulatorClient:
    """ADK LlmAgent-backed Insurer Persona (Phase 2)."""

    name = "adk_simulator"

    def __init__(self, model: Any | None = None) -> None:
        self._model = model

    def assess(self, denial_text: str, appeal_letter: str) -> FeatureAssessment:
        from app.aegis_v1.simulator_agent import run_simulator_agent

        try:
            return run_simulator_agent(
                denial_text=denial_text,
                appeal_letter=appeal_letter,
                model=self._model,
            )
        except Exception:
            logging.getLogger(__name__).warning(
                "AdkSimulatorClient.assess failed; retrying via GeminiSimulatorClient",
                exc_info=True,
            )
            try:
                return GeminiSimulatorClient().assess(
                    denial_text=denial_text,
                    appeal_letter=appeal_letter,
                )
            except Exception:
                logging.getLogger(__name__).warning(
                    "GeminiSimulatorClient fallback failed; using weak assessment",
                    exc_info=True,
                )
                return uniform_assessment(
                    1,
                    critique="Insurer Simulator unavailable; treated as weak.",
                )


class GeminiSimulatorClient:
    """Vertex/Gemini-backed Insurer Persona. Emits a critique-first FeatureAssessment
    (per-feature 1/3/5 marks); the APPROVE/DENY verdict is computed downstream by the
    deterministic `score_outcome`, never by this class (INV-S2/S3).

    Live generation is exercised in a GCP integration session; this class is
    unit-tested only for construction/config offline.
    """

    name = "gemini_simulator"

    def __init__(self, model: str | None = None, location: str | None = None) -> None:
        # Prefer the newest stable name when available, but allow graceful fallback
        # in projects/regions that don't have access yet.
        self.model = model or os.environ.get("AEGIS_SIMULATOR_MODEL", "gemini-3.1-pro-preview")
        self.location = location or os.environ.get("GOOGLE_CLOUD_LOCATION", "global")

    def assess(self, denial_text: str, appeal_letter: str) -> FeatureAssessment:
        from google import genai
        from google.genai import types
        from pydantic import BaseModel, Field

        from app.aegis_v1.simulator_scoring import load_simulator_rules

        # google-genai + pydantic 2.13 require string enum values in JSON schemas.
        class _Mark(BaseModel):
            anchor: Literal["1", "3", "5"]
            evidence: str = ""

        class _Assessment(BaseModel):
            critique: str = Field(description="Critique the appeal as a strict adjuster BEFORE marking features.")
            addresses_denial_rationale: _Mark
            cites_clinical_evidence: _Mark
            cites_applicable_authority: _Mark
            cites_binding_policy: _Mark
            rebuts_specific_flaw: _Mark
            medical_director_persuasion: _Mark
            specific_requested_action: _Mark
            credible_tone: _Mark
            unrebutted_denial_points: list[str] = Field(
                default_factory=list,
                description="Denial hooks from the denial letter still not rebutted with facts in the appeal.",
            )

        keys = list(load_simulator_rules().features.keys())
        prompt = _build_assess_prompt(denial_text, appeal_letter)
        try:
            from app.gemini_retry import generate_content_with_fallback

            client = genai.Client(vertexai=True, location=self.location)
            response = generate_content_with_fallback(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_Assessment,
                    temperature=0.2,
                ),
            )
            data = json.loads(response.text)

            def _anchor_int(mark: dict) -> int:
                raw = mark.get("anchor", 1)
                return int(raw) if isinstance(raw, str) else raw

            return FeatureAssessment(
                critique=data.get("critique", ""),
                features={
                    k: FeatureMark(
                        anchor=_anchor_int(data.get(k, {})),
                        evidence=data.get(k, {}).get("evidence", ""),
                    )
                    for k in keys
                },
                unrebutted_denial_points=[
                    str(point).strip()
                    for point in data.get("unrebutted_denial_points", []) or []
                    if str(point).strip()
                ],
            )
        except Exception:
            logging.getLogger(__name__).warning(
                "GeminiSimulatorClient.assess failed; falling back to weak assessment",
                exc_info=True,
            )
            return uniform_assessment(1, critique="LLM Insurer Simulator unavailable; treated as weak.")
