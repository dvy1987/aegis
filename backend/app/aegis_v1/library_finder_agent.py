from __future__ import annotations

import json
import logging
import re
from typing import Any

from google.adk.agents import LlmAgent
from google.genai import types

from app.aegis_v1.adk_runtime import collect_text, make_retry_model, run_llm_agent_sync
from app.aegis_v1.schemas import RetrievalResult

logger = logging.getLogger(__name__)

_LIBRARY_FINDER_INSTRUCTION = """\
You are a legal/medical research assistant for health-insurance appeal letters.

You will receive a JSON context with parsed_case, playbook, and phoenix_summary.

Your job:
1. Derive a focused search query from the case (insurer, denial type, service,
   diagnosis, denial reason).
2. Call the search_library tool exactly once with that query.
3. Return ONLY valid JSON matching:
   {"query": "<your query>", "hits": [{"corpus_doc_id": "...", "title": "...",
   "quote": "...", "relevance_score": 0.0}]}

Use the tool results for hits — do not invent citations. If the tool returns no
hits, return an empty hits array with your query.
"""

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def make_search_library_tool(library_stack: dict[str, Any] | None):
    """ADK-callable tool: corpus search for the library-finder LlmAgent."""

    def search_library(query: str, top_k: int = 3) -> str:
        """Search the medical/legal corpus for sources relevant to the query.

        Returns JSON with query, hits, and search_error flag.
        """
        from app.aegis_v1.corpus_bridge import hits_to_retrieval, search_unified_library
        from app.aegis_v1.v1_config import build_v1_library_stack

        stack = library_stack or build_v1_library_stack()
        corpus_store = stack.get("corpus_store")
        if corpus_store is None:
            stack = build_v1_library_stack()
            corpus_store = stack.get("corpus_store")

        try:
            hits = search_unified_library(corpus_store, query, top_k=top_k)
            retrieval = hits_to_retrieval(query, hits)
            payload = {**retrieval, "search_error": False}
        except Exception:
            logger.warning(
                "search_library tool failed for query=%r", query, exc_info=True
            )
            retrieval = hits_to_retrieval(query, [])
            payload = {**retrieval, "search_error": True}
        return json.dumps(payload, default=str)

    return search_library


def build_library_finder_agent(
    *,
    model: Any | None = None,
    library_stack: dict[str, Any] | None = None,
) -> LlmAgent:
    """Construct the library-finder ADK agent with a corpus search tool."""
    return LlmAgent(
        name="library_finder_agent",
        model=model or make_retry_model(),
        instruction=_LIBRARY_FINDER_INSTRUCTION,
        tools=[make_search_library_tool(library_stack)],
        generate_content_config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )


def parse_library_finder_response(text: str) -> tuple[dict[str, Any], bool]:
    """Parse LlmAgent JSON output into a RetrievalResult dict + search_error flag."""
    cleaned = text.strip()
    fence = _JSON_FENCE_RE.search(cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    data = json.loads(cleaned)
    search_error = bool(data.pop("search_error", False))
    retrieval = RetrievalResult.model_validate(data).model_dump()
    return retrieval, search_error


def run_offline_library_search(
    parsed: dict[str, Any], library_stack: dict[str, Any] | None
) -> tuple[dict[str, Any], bool]:
    """Deterministic library search for offline tests (baseline query + tool)."""
    from app.aegis_v1.search_planner import build_baseline_query

    baseline = build_baseline_query(parsed)
    raw = make_search_library_tool(library_stack)(baseline, top_k=3)
    data = json.loads(raw)
    search_error = bool(data.pop("search_error", False))
    retrieval = RetrievalResult.model_validate(data).model_dump()
    return retrieval, search_error


def run_library_finder_agent(
    *,
    parsed: dict[str, Any],
    playbook: dict[str, Any],
    phoenix_summary: dict[str, Any],
    library_stack: dict[str, Any] | None,
    model: Any | None = None,
) -> tuple[dict[str, Any], bool]:
    """Run the library-finder LlmAgent; return (retrieval dict, search_error)."""
    context_payload = {
        "parsed_case": parsed,
        "playbook": playbook,
        "phoenix_summary": phoenix_summary,
    }
    message = (
        "Find library citations for this appeal case.\n\nCONTEXT JSON:\n"
        f"{json.dumps(context_payload, indent=2, default=str)}"
    )
    agent = build_library_finder_agent(model=model, library_stack=library_stack)
    result = run_llm_agent_sync(
        agent,
        app_name="aegis_v1",
        user_id="library_finder",
        message=message,
    )
    raw = collect_text(result.get("events", []))
    if not raw.strip():
        raise ValueError("library_finder_agent returned empty response")
    return parse_library_finder_response(raw)
