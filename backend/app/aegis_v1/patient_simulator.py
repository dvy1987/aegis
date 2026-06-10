"""Showcase-only patient simulator.

In showcase/benchmark runs there is no real person, so this stands in for the
patient during the pre-draft question interview. It is **omniscient** about the
synthetic case's full clinical file (the teacher `clinical_context`) and answers
in a patient's voice — but it MUST refuse regulatory / policy / legal questions.
The question agent has to look those up itself (playbook / library); if the
simulator answered them, the question agent would learn to be lazy and stop
distinguishing "ask the patient" from "look it up" (see the design doc,
2026-06-10-question-agent-design.md).

This mirrors the injectable-client pattern used by `drafter_client` and
`simulator_client`: a `Protocol` + deterministic offline `Stub*` + live `Gemini*`.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Protocol

PATIENT_REFUSAL = (
    "I wouldn't know that — that's my plan or insurer's information, "
    "not something I'd have."
)
PATIENT_UNSURE = "I'm not totally sure about that, sorry."

# Terms that mark a question as regulatory / policy / legal — NOT patient-knowable.
# The simulator refuses these so the question agent keeps looking them up itself.
_REGULATORY_TERMS = (
    "erisa",
    "statute",
    "regulation",
    "regulatory",
    "law",
    "legal",
    "lawsuit",
    "fda",
    "policy",
    "plan document",
    "plan language",
    "medical necessity standard",
    "coverage criteria",
    "coverage rule",
    "guideline",
    "deadline",
    "filing limit",
    "appeal rights",
    "mhpaea",
    "parity",
    "cfr",
    "u.s.c",
    "usc",
    "ncd",
    "lcd",
    "precedent",
    "case law",
)

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9'-]*")
_STOPWORDS = frozenset(
    {
        "the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "at", "is",
        "are", "was", "were", "do", "did", "does", "have", "has", "had", "you",
        "your", "any", "with", "about", "that", "this", "what", "when", "how",
        "before", "after", "been", "from", "did", "if", "so", "it", "i",
    }
)


def is_regulatory_question(question: str) -> bool:
    """True when the question asks for regulatory/policy/legal content.

    These are out of bounds for the patient — the question agent must look them
    up via playbook/library instead of asking the person.
    """
    q = (question or "").lower()
    return any(term in q for term in _REGULATORY_TERMS)


def _content_tokens(text: str) -> set[str]:
    return {t for t in _WORD_RE.findall((text or "").lower()) if t not in _STOPWORDS}


def _relevant_sentence(clinical_context: str, question: str) -> str:
    """Pick the clinical-context sentence with the most keyword overlap."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clinical_context) if s.strip()]
    if not sentences:
        return ""
    q_tokens = _content_tokens(question)
    if not q_tokens:
        return ""
    best = max(sentences, key=lambda s: len(_content_tokens(s) & q_tokens))
    overlap = len(_content_tokens(best) & q_tokens)
    return best if overlap else ""


class PatientSimulatorClient(Protocol):
    name: str

    def answer(
        self,
        *,
        question: str,
        clinical_context: str,
        patient_profile: dict[str, Any] | None = None,
    ) -> str:
        """Return a patient-voiced answer, or a refusal for regulatory questions."""


class StubPatientSimulatorClient:
    """Deterministic offline patient simulator for tests/dry-runs.

    Omniscient over the injected clinical context, but answers only
    patient-appropriate questions; regulatory questions are refused verbatim so
    the firewall is easy to assert in tests.
    """

    name = "stub_patient_simulator"

    def __init__(
        self,
        clinical_context: str = "",
        patient_profile: dict[str, Any] | None = None,
    ) -> None:
        self._clinical_context = clinical_context
        self._patient_profile = patient_profile or {}

    def answer(
        self,
        *,
        question: str,
        clinical_context: str = "",
        patient_profile: dict[str, Any] | None = None,
    ) -> str:
        if is_regulatory_question(question):
            return PATIENT_REFUSAL
        ctx = clinical_context or self._clinical_context
        snippet = _relevant_sentence(ctx, question)
        if snippet:
            return snippet
        return PATIENT_UNSURE


def _build_simulator_prompt(
    *,
    question: str,
    clinical_context: str,
    patient_profile: dict[str, Any] | None,
) -> str:
    profile = patient_profile or {}
    return f"""
    You are playing the PATIENT in a health-insurance appeal. Answer in the first
    person, the way an ordinary, non-expert person would — short, plain, honest.

    You have full knowledge of your own clinical situation (below). You may share
    anything a patient would personally know: your symptoms, timeline, diagnoses
    your doctor told you, treatments you've tried and how they went, tests you've
    had, and whether your doctor supports this treatment.

    HARD RULE — you must NOT answer regulatory, policy, or legal questions
    (plan language, coverage criteria, statutes/regulations, FDA rules, filing
    deadlines, appeal-rights law, clinical guidelines). A real patient would not
    know these. If asked one, reply exactly:
    "{PATIENT_REFUSAL}"
    Do not paraphrase regulatory content out of your records even if it appears below.

    Your clinical situation:
    {clinical_context}

    Patient profile: {profile}

    The question you are being asked:
    {question}

    Answer as the patient in 1–3 sentences.
    """


class GeminiPatientSimulatorClient:
    """Vertex/Gemini-backed patient simulator. Construction is unit-tested offline;
    live generation is exercised in a GCP session."""

    name = "gemini_patient_simulator"

    def __init__(self, model: str | None = None, location: str | None = None) -> None:
        self.model = model or os.environ.get(
            "AEGIS_PATIENT_SIM_MODEL", "gemini-3.1-pro-preview"
        )
        self.location = location or os.environ.get("GOOGLE_CLOUD_LOCATION", "global")

    def answer(
        self,
        *,
        question: str,
        clinical_context: str,
        patient_profile: dict[str, Any] | None = None,
    ) -> str:
        # Defense in depth: never even send a regulatory question to the model.
        if is_regulatory_question(question):
            return PATIENT_REFUSAL
        try:
            from google import genai
            from google.genai import types

            from app.gemini_retry import generate_content_with_fallback

            client = genai.Client(vertexai=True, location=self.location)
            response = generate_content_with_fallback(
                client.models.generate_content,
                model=self.model,
                contents=_build_simulator_prompt(
                    question=question,
                    clinical_context=clinical_context,
                    patient_profile=patient_profile,
                ),
                config=types.GenerateContentConfig(temperature=0.4),
            )
            return (response.text or "").strip() or PATIENT_UNSURE
        except Exception:
            logging.getLogger(__name__).warning(
                "GeminiPatientSimulatorClient.answer failed; returning unsure",
                exc_info=True,
            )
            return PATIENT_UNSURE
