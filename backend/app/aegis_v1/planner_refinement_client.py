from __future__ import annotations

import json
import os
from typing import Any, Protocol

from app.aegis_v1.drafter_client import PROMPT_DIR


def load_search_planner_prompt(version: str = "search_planner_v1") -> str:
    return (PROMPT_DIR / f"{version}.md").read_text(encoding="utf-8")


class PlannerRefinementClient(Protocol):
    name: str

    def refine(
        self,
        *,
        prompt: str,
        parsed_case: dict[str, Any],
        fetch_index: int,
        prior_queries: list[str],
        hit_count: int,
        ingest_count: int,
        reject_count: int,
    ) -> str:
        """Return the next narrow discovery search phrase."""


class StubPlannerRefinementClient:
    """Offline refinement: deterministic suffix by fetch index and denial type."""

    name = "stub_planner_refinement"

    def refine(
        self,
        *,
        prompt: str,
        parsed_case: dict[str, Any],
        fetch_index: int,
        prior_queries: list[str],
        hit_count: int,
        ingest_count: int,
        reject_count: int,
    ) -> str:
        _ = prompt, hit_count, ingest_count, reject_count
        base = prior_queries[0] if prior_queries else ""
        denial = str(parsed_case.get("denial_type", "")).replace("_", " ")
        service = str(parsed_case.get("service_or_procedure", ""))
        suffixes = {
            1: "clinical guideline medical necessity",
            2: "coverage criteria policy",
            3: "peer reviewed evidence standard",
            4: "ERISA full and fair review",
        }
        extra = suffixes.get(fetch_index, "authoritative source")
        refined = f"{base} {denial} {service} {extra}".strip()
        return " ".join(refined.split())


class GeminiPlannerRefinementClient:
    """Live Layer-3 refinement via Vertex/Gemini (credential-gated)."""

    name = "gemini_planner_refinement"

    def __init__(self, *, model: str | None = None, location: str | None = None) -> None:
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        self.location = location or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    def refine(
        self,
        *,
        prompt: str,
        parsed_case: dict[str, Any],
        fetch_index: int,
        prior_queries: list[str],
        hit_count: int,
        ingest_count: int,
        reject_count: int,
    ) -> str:
        from google import genai

        from app.gemini_retry import generate_content_with_retry

        firewall_input = {
            "insurer": parsed_case.get("insurer"),
            "denial_type": parsed_case.get("denial_type"),
            "service_or_procedure": parsed_case.get("service_or_procedure"),
            "diagnosis_summary": parsed_case.get("diagnosis_summary"),
            "cited_denial_reason": parsed_case.get("cited_denial_reason"),
            "fetch_index": fetch_index,
            "prior_queries": prior_queries,
            "library_hit_count": hit_count,
            "discovery_ingest_count": ingest_count,
            "discovery_reject_count": reject_count,
        }
        user = (
            "Propose the next narrow library-discovery search phrase.\n"
            f"Context (firewall-safe): {json.dumps(firewall_input, ensure_ascii=True)}\n"
            "Reply with the phrase only."
        )
        client = genai.Client(vertexai=True, location=self.location)
        response = generate_content_with_retry(
            client.models.generate_content,
            model=self.model,
            contents=[{"role": "user", "parts": [{"text": f"{prompt}\n\n{user}"}]}],
            config={"temperature": 0.2, "max_output_tokens": 128},
        )
        text = (response.text or "").strip().splitlines()[0].strip()
        return text
