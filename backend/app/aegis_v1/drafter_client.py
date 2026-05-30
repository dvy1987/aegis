from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Protocol


# Part A prompts are colocated with the aegis_v1 backend (matching the
# case_generator pattern). Swarm/Part B prompts live under aegis_swarm/prompts/.
PROMPT_DIR = Path(__file__).resolve().parent / "prompts"


def load_drafter_prompt(version: str = "drafter_v1") -> str:
    return (PROMPT_DIR / f"{version}.md").read_text(encoding="utf-8")


class DrafterLLMClient(Protocol):
    name: str

    def draft(
        self,
        prompt: str,
        parsed_case: dict[str, Any],
        citations: list[dict[str, Any]],
        playbook: dict[str, Any],
        phoenix_summary: dict[str, Any],
    ) -> str:
        """Return the appeal-letter body text (no schema wrapping)."""


class StubDrafterClient:
    """Deterministic offline drafter for tests/dry-runs. NOT for benchmarks."""

    name = "stub_drafter"

    def draft(self, prompt, parsed_case, citations, playbook, phoenix_summary) -> str:
        insurer = parsed_case.get("insurer", "the insurer")
        service = parsed_case.get("service_or_procedure", "the requested service")
        reason = parsed_case.get("cited_denial_reason", "the stated reason")
        tactics = " ".join(playbook.get("tactics", [])[:2])
        cites = "; ".join(
            f"{c.get('title','')} ({c.get('corpus_doc_id','')})" for c in citations[:3]
        )
        context = parsed_case.get("clinical_context", "")
        return (
            f"To the appeals reviewer: I am appealing {insurer}'s denial of {service}. "
            f"The denial rests on: {reason}. {('Clinical context: ' + context + '. ') if context else ''}"
            f"Basis for appeal: {tactics} "
            f"Supporting sources: {cites or 'none retrieved'}. "
            f"Requested action: please conduct a full and fair review and have a "
            f"qualified reviewer reassess whether the service meets plan criteria."
        )


def _build_contents(prompt, parsed_case, citations, playbook, phoenix_summary) -> str:
    context = {
        "parsed_case": parsed_case,
        "citations": citations,
        "playbook": playbook,
        "phoenix_summary": phoenix_summary,
    }
    return f"{prompt}\n\nCONTEXT JSON:\n{json.dumps(context, indent=2, default=str)}"


class GeminiDrafterClient:
    """Vertex/Gemini-backed drafter. Returns the appeal-letter body text."""

    name = "gemini"

    def __init__(self, model: str | None = None, location: str = "global") -> None:
        self.model = model or os.environ.get("AEGIS_DRAFTER_MODEL", "gemini-3.1-pro")
        self.location = location

    def draft(self, prompt, parsed_case, citations, playbook, phoenix_summary) -> str:
        from google import genai
        from google.genai import types

        client = genai.Client(vertexai=True, location=self.location)
        response = client.models.generate_content(
            model=self.model,
            contents=_build_contents(prompt, parsed_case, citations, playbook, phoenix_summary),
            config=types.GenerateContentConfig(temperature=0.3),
        )
        return response.text or ""
