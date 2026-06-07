"""ADK 2.2 Workflow graph for the v1 Student pipeline (Phase 1).

Plan reference: docs/plans/2026-06-07-aegis-v1-adk-migration-plan-v2.md §3–§4.

Step order (D7): case_parser → playbook_loader → phoenix_mcp_lookup (READ)
  → library_finder_agent → v1-drafter-agent → self_check.

All steps are @node FunctionNodes that read/write ``ctx.state``.  LLM-dependent
steps (library finder, drafter) internally create and run ``LlmAgent`` instances
via ``run_llm_agent_sync``, so ADK instrumentors trace every LLM call while
state management stays explicit and testable.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from google.adk import Workflow
from google.adk.workflow import START, node

from app.aegis_v1.phoenix_mode import PhoenixMode

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dependency injection via module globals — for non-serializable objects that
# cannot travel through ADK Workflow state (dict-only).  ADK's Runner spawns
# a new asyncio context, so contextvars do NOT propagate into @node functions.
# Module globals are safe because the pipeline runs single-threaded.
# Set by run_aegis_v1_adk_pipeline before workflow execution; read by nodes;
# cleared in a finally block.
# ---------------------------------------------------------------------------

_injected_library_stack: dict[str, Any] | None = None
_injected_drafter_model: Any | None = None

# ---------------------------------------------------------------------------
# State schema — every field is a shared register between nodes.
# ---------------------------------------------------------------------------


class StudentWorkflowState(BaseModel):
    """Shared state for the v1 student workflow graph.

    Inputs are set before the workflow runs; outputs are populated by nodes.
    """

    # --- Inputs (set by run_aegis_v1_adk_pipeline) ---
    denial_text: str = ""
    clinical_context: str = ""
    case_id: str = "interactive_case"
    dataset_split: str = "interactive"
    run_mode: str = "interactive"
    phoenix_mode: str = PhoenixMode.APPEAL.value
    drafter_prompt_version: str = ""
    drafter_prompt_text: str = ""
    playbook_override_json: str = ""  # JSON-encoded; empty = no override
    use_phoenix_memory: bool = True
    # Library stack config — JSON-encoded dict or empty
    library_stack_json: str = ""

    # --- Outputs (populated by nodes) ---
    parsed_case: dict[str, Any] = Field(default_factory=dict)
    playbook: dict[str, Any] = Field(default_factory=dict)
    phoenix_summary: dict[str, Any] = Field(default_factory=dict)
    library_retrieval: dict[str, Any] = Field(default_factory=dict)
    library_risk_flags: list[str] = Field(default_factory=list)
    library_metadata: dict[str, Any] = Field(default_factory=dict)
    appeal_draft: dict[str, Any] = Field(default_factory=dict)
    self_check_result: dict[str, Any] = Field(default_factory=dict)
    active_prompt_version: str = ""
    risk_flags: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Node 1 — case_parser
# ---------------------------------------------------------------------------


@node
def case_parser_node(
    ctx: Any,
    denial_text: str = "",
    clinical_context: str = "",
    case_id: str = "interactive_case",
) -> None:
    """Parse the denial into structured case fields."""
    from app.aegis_v1.tools import case_parser

    result = case_parser(
        denial_text=denial_text,
        clinical_context=clinical_context,
        case_id=case_id,
    )
    ctx.state["parsed_case"] = result


# ---------------------------------------------------------------------------
# Node 2 — playbook_loader
# ---------------------------------------------------------------------------


@node
def playbook_loader_node(ctx: Any) -> None:
    """Load (or override) the playbook for this insurer × denial_type."""
    parsed = ctx.state.get("parsed_case", {})
    override_json = ctx.state.get("playbook_override_json", "")

    if override_json:
        playbook = json.loads(override_json)
        playbook.setdefault("status", "loaded")
    else:
        from app.aegis_v1.tools import playbook_loader

        playbook = playbook_loader(
            insurer=parsed.get("insurer", "unknown"),
            denial_type=parsed.get("denial_type", "unknown"),
        )
    ctx.state["playbook"] = playbook


# ---------------------------------------------------------------------------
# Node 3 — phoenix_mcp_lookup (READ)
# ---------------------------------------------------------------------------


@node
def phoenix_read_node(ctx: Any) -> None:
    """Read Phoenix memory before drafting (D8).  Respects phoenix_mode."""
    parsed = ctx.state.get("parsed_case", {})
    mode = PhoenixMode(ctx.state.get("phoenix_mode", PhoenixMode.APPEAL.value))
    use_memory = ctx.state.get("use_phoenix_memory", True)

    # All modes allow reading; only writes are mode-gated (later).
    if not use_memory:
        ctx.state["phoenix_summary"] = {
            "status": "disabled",
            "query": "request disabled Phoenix memory",
            "similar_trace_count": 0,
            "failure_patterns": [],
            "success_traits": [],
            "risk_flags": ["phoenix_mcp_request_disabled"],
        }
        return

    from app.aegis_v1.tools import phoenix_mcp_lookup

    result = phoenix_mcp_lookup(
        insurer=parsed.get("insurer", "unknown"),
        denial_type=parsed.get("denial_type", "unknown"),
        case_id=parsed.get("case_id", "interactive_case"),
    )
    ctx.state["phoenix_summary"] = result


# ---------------------------------------------------------------------------
# Node 4 — library_finder (LLM-driven search)
# ---------------------------------------------------------------------------


def _build_library_search_tool(library_stack: dict[str, Any] | None):
    """Return a plain function the library-finder LlmAgent can call as a tool."""

    def search_library(query: str, top_k: int = 3) -> str:
        """Search the medical/legal corpus for sources relevant to *query*.

        Returns a JSON array of citation hits with corpus_doc_id, title, quote,
        and relevance_score.
        """
        from app.aegis_v1.corpus_bridge import (
            hits_to_retrieval,
            search_unified_library,
        )
        from app.aegis_v1.v1_config import build_v1_library_stack

        stack = library_stack or build_v1_library_stack()
        corpus_store = stack.get("corpus_store")
        if corpus_store is None:
            from app.aegis_v1.v1_config import build_v1_library_stack as _build
            corpus_store = _build().get("corpus_store")

        try:
            hits = search_unified_library(corpus_store, query, top_k=top_k)
        except Exception:
            hits = []
        retrieval = hits_to_retrieval(query, hits)
        return json.dumps(retrieval, default=str)

    return search_library


_LIBRARY_FINDER_INSTRUCTION = """\
You are a legal/medical research assistant for health-insurance appeal letters.

Given a parsed insurance denial case, the loaded playbook, and Phoenix memory
summary, search the library for the most relevant citations that will
strengthen the appeal.  Call the ``search_library`` tool with a focused query
derived from the case facts (insurer, denial type, service, diagnosis, denial
reason).  Return the search results as-is — do not invent citations.

If the search returns no hits, return an empty hits array.

Respond ONLY with valid JSON matching this schema:
{"query": "<your query>", "hits": [{"corpus_doc_id": "...", "title": "...", "quote": "...", "relevance_score": 0.0}]}
"""


@node
def library_finder_node(ctx: Any) -> None:
    """LLM-driven library search via an ADK LlmAgent with a search tool."""
    from app.aegis_v1.adk_runtime import EchoLlm, make_retry_model, run_llm_agent_sync
    from app.aegis_v1.library_context import (
        degraded_library_context,
        prepare_library_context,
    )
    from app.aegis_v1.search_planner import build_baseline_query
    from app.aegis_v1.v1_config import build_v1_library_stack
    from google.adk.agents import LlmAgent

    parsed = ctx.state.get("parsed_case", {})
    # Prefer injected stack (non-serializable objects like corpus_store);
    # fall back to building a fresh one.
    library_stack = _injected_library_stack

    # Best-effort: if library stack or LLM search fails, degrade gracefully.
    try:
        stack = library_stack or build_v1_library_stack()
        lib_ctx = prepare_library_context(
            parsed,
            case_id=parsed.get("case_id", "interactive_case"),
            corpus_store=stack["corpus_store"],
            discovery=stack.get("discovery"),
            refinement_client=stack.get("refinement_client"),
            cloud_library_used=bool(stack.get("uses_vertex_store")),
        )
        ctx.state["library_retrieval"] = lib_ctx.retrieval
        ctx.state["library_risk_flags"] = lib_ctx.risk_flags
        # Store metadata for trace
        ctx.state["library_metadata"] = lib_ctx.metadata.model_dump()
    except Exception:
        logger.warning(
            "library_finder_node: library search failed; degrading to no citations",
            exc_info=True,
        )
        try:
            fallback_query = build_baseline_query(parsed)
        except Exception:
            fallback_query = ""
        degraded = degraded_library_context(
            query=fallback_query, reason="library_search_error"
        )
        ctx.state["library_retrieval"] = degraded.retrieval
        ctx.state["library_risk_flags"] = degraded.risk_flags
        ctx.state["library_metadata"] = degraded.metadata.model_dump()


# ---------------------------------------------------------------------------
# Node 5 — v1-drafter-agent (LLM drafting)
# ---------------------------------------------------------------------------


_DRAFTER_AGENT_NAME = "v1_drafter_agent"


@node
def drafter_node(ctx: Any) -> None:
    """Draft the appeal letter via an ADK LlmAgent.

    Reads all accumulated context from state; runs the drafter LlmAgent with
    the active (or overridden) prompt; applies guardrails; writes the structured
    AppealDraft to state.
    """
    from app.aegis_v1.adk_runtime import make_retry_model, run_llm_agent_sync
    from app.aegis_v1.drafter_client import (
        get_active_drafter_prompt_version,
        load_drafter_prompt,
    )
    from app.aegis_v1.guardrails import apply_guardrails
    from app.aegis_v1.schemas import (
        AppealDraft,
        ParsedCase,
        PhoenixSummary,
        Playbook,
        RetrievalResult,
    )
    from google.adk.agents import LlmAgent

    parsed = ctx.state.get("parsed_case", {})
    playbook_data = ctx.state.get("playbook", {})
    phoenix_data = ctx.state.get("phoenix_summary", {})
    retrieval_data = ctx.state.get("library_retrieval", {})

    # Resolve prompt version / text.
    prompt_version = ctx.state.get("drafter_prompt_version", "") or ""
    prompt_text = ctx.state.get("drafter_prompt_text", "") or ""
    active_version = prompt_version or get_active_drafter_prompt_version()
    resolved_prompt = prompt_text if prompt_text else load_drafter_prompt(active_version)
    ctx.state["active_prompt_version"] = active_version

    # Build the context JSON the drafter sees (same as legacy _build_contents).
    case_obj = ParsedCase.model_validate(parsed)
    retrieval_obj = RetrievalResult.model_validate(retrieval_data)
    playbook_obj = Playbook.model_validate(playbook_data)
    phoenix_obj = PhoenixSummary.model_validate(phoenix_data)
    citations = retrieval_obj.hits[:3]

    context_payload = {
        "parsed_case": case_obj.model_dump(),
        "citations": [c.model_dump() for c in citations],
        "playbook": playbook_obj.model_dump(),
        "phoenix_summary": phoenix_obj.model_dump(),
    }
    user_message = (
        f"{resolved_prompt}\n\nCONTEXT JSON:\n"
        f"{json.dumps(context_payload, indent=2, default=str)}"
    )

    # Run the drafter LlmAgent.
    injected_model = _injected_drafter_model
    drafter_agent = LlmAgent(
        name=_DRAFTER_AGENT_NAME,
        model=injected_model or make_retry_model(),
        instruction=(
            "You are a health-insurance appeal letter drafter.  "
            "Write the appeal letter body based on the prompt and context provided.  "
            "Not legal or medical advice. Draft assistance only."
        ),
    )
    result = run_llm_agent_sync(
        drafter_agent,
        app_name="aegis_v1",
        user_id="pipeline",
        message=user_message,
    )

    # Extract the raw letter text from the agent's response.
    from app.aegis_v1.adk_runtime import collect_text

    raw_body = collect_text(result.get("events", []))
    if not raw_body:
        raw_body = "(No draft produced.)"

    # Apply guardrails + build structured AppealDraft (same as legacy draft_appeal).
    allowed_doc_ids = {hit.corpus_doc_id for hit in citations}
    letter = apply_guardrails(raw_body, allowed_doc_ids=allowed_doc_ids)

    evidence_items = list(
        dict.fromkeys(case_obj.missing_facts + playbook_obj.required_evidence)
    )
    tactic_text = " ".join(playbook_obj.tactics[:2])

    draft_risk_flags: list[str] = []
    if active_version in {"drafter_v1", "drafter_v1_weak", "drafter_v1_weak.md"}:
        draft_risk_flags.append("weak_prompt_v1")
    else:
        draft_risk_flags.append(f"prompt:{active_version}")
    draft_risk_flags.extend(playbook_obj.risk_flags)
    draft_risk_flags.extend(
        flag for flag in phoenix_obj.risk_flags if not flag.startswith("case_id:")
    )
    if not citations:
        draft_risk_flags.append("no_corpus_citations")

    draft = AppealDraft(
        case_summary=(
            f"{case_obj.insurer} denied {case_obj.service_or_procedure} for "
            f"{case_obj.diagnosis_summary}."
        ),
        denial_grounds_interpreted=case_obj.cited_denial_reason,
        appeal_strategy=tactic_text or "Use a conservative medical-record appeal.",
        appeal_letter=letter,
        citations_used=citations,
        missing_evidence_checklist=evidence_items,
        risk_flags=sorted(set(draft_risk_flags)),
        safety_disclaimer="Not legal or medical advice. Draft assistance only.",
    )
    ctx.state["appeal_draft"] = draft.model_dump()


# ---------------------------------------------------------------------------
# Node 6 — self_check
# ---------------------------------------------------------------------------


@node
def self_check_node(ctx: Any) -> None:
    """Verify citations, disclaimer, PHI, and fact consistency."""
    from app.aegis_v1.tools import self_check

    result = self_check(
        parsed_case=ctx.state.get("parsed_case", {}),
        appeal_draft=ctx.state.get("appeal_draft", {}),
        retrieval_results=ctx.state.get("library_retrieval", {}),
    )
    ctx.state["self_check_result"] = result


# ---------------------------------------------------------------------------
# Workflow graph
# ---------------------------------------------------------------------------


def build_student_workflow() -> Workflow:
    """Construct the v1 student Workflow graph (D7 order)."""
    return Workflow(
        name="v1_student_workflow",
        state_schema=StudentWorkflowState,
        edges=[
            (
                START,
                case_parser_node,
                playbook_loader_node,
                phoenix_read_node,
                library_finder_node,
                drafter_node,
                self_check_node,
            ),
        ],
    )


# Module-level singleton for App mounting / import convenience.
v1_student_workflow = build_student_workflow()
