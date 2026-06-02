from __future__ import annotations

import re
from typing import Any

from app.aegis_v1.planner_refinement_client import (
    PlannerRefinementClient,
    StubPlannerRefinementClient,
    load_search_planner_prompt,
)

_BROAD_QUERY_RE = re.compile(
    r"(search\s+(?:the\s+)?entire\s+web|whole\s+internet|all\s+websites|google\s+everything)",
    re.IGNORECASE,
)

CURRENT_SEARCH_PLANNER_VERSION = "search_planner_v1"
MAX_QUERY_CHARS = 240

_DENIAL_REFINEMENT_HINTS: dict[str, tuple[str, ...]] = {
    "medical_necessity": ("clinical guideline", "medical necessity"),
    "prior_authorization": ("prior authorization", "coverage criteria"),
    "coverage_exclusion": ("coverage policy", "plan language"),
}


def build_baseline_query(parsed_case: dict[str, Any]) -> str:
    """Layer 1: versioned deterministic recipe from structured case facts."""
    parts = [
        str(parsed_case.get("insurer", "")),
        str(parsed_case.get("denial_type", "")).replace("_", " "),
        str(parsed_case.get("service_or_procedure", "")),
        str(parsed_case.get("diagnosis_summary", "")),
        str(parsed_case.get("cited_denial_reason", "")),
    ]
    return " ".join(p.strip() for p in parts if p and p.strip())


def apply_query_guardrails(phrase: str, *, fallback: str) -> tuple[str, bool]:
    """Reject overly broad phrases (EC-6). Returns (phrase, refinement_rejected)."""
    cleaned = " ".join((phrase or "").split())
    if not cleaned or len(cleaned) > MAX_QUERY_CHARS or _BROAD_QUERY_RE.search(cleaned):
        return fallback, True
    return cleaned, False


def refine_discovery_query(
    *,
    parsed_case: dict[str, Any],
    fetch_index: int,
    prior_queries: list[str],
    hit_count: int,
    ingest_count: int,
    reject_count: int,
    client: PlannerRefinementClient | None = None,
    prompt_version: str = CURRENT_SEARCH_PLANNER_VERSION,
) -> tuple[str, bool]:
    """Layer 3: next discovery phrase for fetch 2..5. Returns (phrase, layer3_ran)."""
    if fetch_index < 1:
        return prior_queries[-1] if prior_queries else build_baseline_query(parsed_case), False

    fallback = _deterministic_refine(parsed_case, fetch_index, prior_queries)
    active = client or StubPlannerRefinementClient()
    prompt = load_search_planner_prompt(prompt_version)
    try:
        raw = active.refine(
            prompt=prompt,
            parsed_case=parsed_case,
            fetch_index=fetch_index,
            prior_queries=prior_queries,
            hit_count=hit_count,
            ingest_count=ingest_count,
            reject_count=reject_count,
        )
    except Exception:
        return fallback, True

    phrase, _rejected = apply_query_guardrails(raw, fallback=fallback)
    return phrase, True


def _deterministic_refine(
    parsed_case: dict[str, Any], fetch_index: int, prior_queries: list[str]
) -> str:
    base = prior_queries[0] if prior_queries else build_baseline_query(parsed_case)
    denial = str(parsed_case.get("denial_type", "unknown"))
    hints = _DENIAL_REFINEMENT_HINTS.get(denial, ("authoritative source",))
    hint = hints[min(fetch_index - 1, len(hints) - 1)]
    return f"{base} {hint}".strip()


def discovery_domain_for_denial(denial_type: str) -> str:
    if denial_type == "medical_necessity":
        return "clinical"
    if denial_type in {"prior_authorization", "coverage_exclusion"}:
        return "insurer"
    return "legal"
