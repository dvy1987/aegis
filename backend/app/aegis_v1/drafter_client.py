from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


PROMPT_DIR = Path(__file__).resolve().parents[2] / "src" / "prompts"


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
