"""ADK 2.2 Workflow graph for the v1 Student pipeline (Phase 1).

Plan reference: docs/plans/2026-06-07-aegis-v1-adk-migration-plan-v2.md §3–§4.

Step order (D7): case_parser → playbook_loader → phoenix_mcp_lookup (READ)
  → library_prep → library_finder_agent → library_finalize
  → drafter_prep → v1_drafter_agent → drafter_finalize
  → self_check → appeal_publish.

``library_finder_agent`` and ``v1_drafter_agent`` are ``LlmAgent`` instances
passed directly in ``Workflow`` edges (plan §3.4). Prep/finalize ``@node``
steps bind state and post-process structured outputs.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from google.adk import Workflow
from google.adk.workflow import START, node
from google.genai import types

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
_injected_offline_pipeline: bool = False
# Question-agent seams. The responder is a closure; on showcase it wraps the
# patient simulator seeded with the TEACHER clinical file — that file lives
# ONLY inside the closure, never in workflow state (INV-QA).
_injected_question_responder: Any | None = None
_injected_question_client: Any | None = None

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
    insurer: str = ""
    patient_age: int = -1
    patient_gender: str = ""
    dataset_split: str = "interactive"
    run_mode: str = "interactive"
    phoenix_mode: str = PhoenixMode.APPEAL.value
    drafter_prompt_version: str = ""
    drafter_prompt_text: str = ""
    playbook_override_json: str = ""  # JSON-encoded; empty = no override
    geo_playbook_override_json: str = ""  # JSON-encoded US-playbook override (GEPA)
    use_phoenix_memory: bool = True
    # Library stack config — JSON-encoded dict or empty
    library_stack_json: str = ""
    # Pre-draft question agent (D-QA). On appeal the turn-based interview ran
    # over HTTP already and is injected as JSON; on showcase the node runs the
    # interview live against the injected simulator responder.
    run_question_agent: bool = False
    question_interview_json: str = ""

    # --- Outputs (populated by nodes) ---
    parsed_case: dict[str, Any] = Field(default_factory=dict)
    playbook: dict[str, Any] = Field(default_factory=dict)
    geo_playbook: dict[str, Any] = Field(default_factory=dict)
    phoenix_summary: dict[str, Any] = Field(default_factory=dict)
    library_retrieval: dict[str, Any] = Field(default_factory=dict)
    library_risk_flags: list[str] = Field(default_factory=list)
    library_metadata: dict[str, Any] = Field(default_factory=dict)
    library_agent_done: bool = False
    question_interview: dict[str, Any] = Field(default_factory=dict)
    appeal_draft: dict[str, Any] = Field(default_factory=dict)
    self_check_result: dict[str, Any] = Field(default_factory=dict)
    active_prompt_version: str = ""
    risk_flags: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers — ADK chat passes user text via node_input; pipeline via state.
# ---------------------------------------------------------------------------


def _node_input_to_text(node_input: Any) -> str:
    """Extract user text from ADK START node_input (Content, str, or dict)."""
    if node_input is None:
        return ""
    if isinstance(node_input, str):
        return node_input
    if isinstance(node_input, types.Content):
        parts: list[str] = []
        for part in node_input.parts or []:
            if part.text:
                parts.append(part.text)
        return "".join(parts)
    if isinstance(node_input, dict):
        content = node_input.get("content")
        if isinstance(content, dict):
            text_parts: list[str] = []
            for part in content.get("parts") or []:
                if isinstance(part, dict) and part.get("text"):
                    text_parts.append(str(part["text"]))
            if text_parts:
                return "".join(text_parts)
        text = node_input.get("text")
        if text:
            return str(text)
    return str(node_input)


# ---------------------------------------------------------------------------
# Node 1 — case_parser
# ---------------------------------------------------------------------------


@node
def case_parser_node(
    ctx: Any,
    node_input: Any = None,
    denial_text: str = "",
    clinical_context: str = "",
    case_id: str = "interactive_case",
    insurer: str = "",
    patient_age: int = -1,
    patient_gender: str = "",
) -> None:
    """Parse the denial into structured case fields."""
    from app.aegis_v1.tools import case_parser

    if not (denial_text or "").strip():
        denial_text = _node_input_to_text(node_input)
    ctx.state["denial_text"] = denial_text
    ctx.state["clinical_context"] = clinical_context
    ctx.state["case_id"] = case_id
    ctx.state["insurer"] = insurer
    ctx.state["patient_age"] = patient_age
    ctx.state["patient_gender"] = patient_gender

    structured = bool(insurer) and patient_age >= 1 and bool(patient_gender)
    result = case_parser(
        denial_text=denial_text,
        clinical_context=clinical_context,
        case_id=case_id,
        insurer=insurer if structured else None,
        patient_age=patient_age if structured else None,
        patient_gender=patient_gender if structured else None,
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
            sub_tactic=parsed.get("sub_tactic"),
        )
    ctx.state["playbook"] = playbook


# ---------------------------------------------------------------------------
# Node 2b — geo_playbook_loader (US-wide rules)
# ---------------------------------------------------------------------------


@node
def geo_playbook_loader_node(ctx: Any) -> None:
    """Load insurer-agnostic US-playbook rules for this case."""
    from app.aegis_v1.geo_playbook import geo_playbook_for_case

    parsed = ctx.state.get("parsed_case", {})
    override_json = ctx.state.get("geo_playbook_override_json", "")
    override = json.loads(override_json) if override_json else None
    ctx.state["geo_playbook"] = geo_playbook_for_case(parsed, override=override)


# ---------------------------------------------------------------------------
# Node 3 — phoenix_mcp_lookup (READ)
# ---------------------------------------------------------------------------


@node
def phoenix_read_node(ctx: Any) -> None:
    """Read Phoenix memory before drafting (D8).  Respects phoenix_mode."""
    parsed = ctx.state.get("parsed_case", {})
    use_memory = ctx.state.get("use_phoenix_memory", True)

    # All modes allow reading; app-level writes are gated via can_write_phoenix().
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
# Node 4 — library prep / finalize (LlmAgent graph node between them)
# ---------------------------------------------------------------------------


@node
def library_prep_node(ctx: Any) -> str:
    """Build library-finder input, or run offline search when tests inject stub."""
    from app.aegis_v1.library_context import (
        degraded_library_context,
        finalize_library_from_agent_retrieval,
    )
    from app.aegis_v1.library_finder_agent import run_offline_library_search
    from app.aegis_v1.search_planner import build_baseline_query
    from app.aegis_v1.v1_config import build_v1_library_stack

    parsed = ctx.state.get("parsed_case", {})
    playbook = ctx.state.get("playbook", {})
    phoenix_summary = ctx.state.get("phoenix_summary", {})
    case_id = parsed.get("case_id", "interactive_case")
    library_stack = _injected_library_stack

    if _injected_offline_pipeline:
        try:
            stack = library_stack or build_v1_library_stack()
            retrieval, search_error = run_offline_library_search(parsed, stack)
            lib_ctx = finalize_library_from_agent_retrieval(
                parsed,
                retrieval,
                case_id=case_id,
                corpus_store=stack["corpus_store"],
                discovery=stack.get("discovery"),
                refinement_client=stack.get("refinement_client"),
                cloud_library_used=bool(stack.get("uses_vertex_store")),
                search_error=search_error,
            )
            ctx.state["library_retrieval"] = lib_ctx.retrieval
            ctx.state["library_risk_flags"] = lib_ctx.risk_flags
            ctx.state["library_metadata"] = lib_ctx.metadata.model_dump()
            ctx.state["library_agent_done"] = True
        except Exception:
            logger.warning(
                "library_prep_node: offline library failed; degrading",
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
            ctx.state["library_agent_done"] = True
        return ""

    context_payload = {
        "parsed_case": parsed,
        "playbook": playbook,
        "phoenix_summary": phoenix_summary,
    }
    return (
        "Find library citations for this appeal case.\n\nCONTEXT JSON:\n"
        f"{json.dumps(context_payload, indent=2, default=str)}"
    )


@node
def library_finalize_node(ctx: Any, node_input: Any = None) -> None:
    """Parse library_finder_agent output and finalize library context in state."""
    if ctx.state.get("library_agent_done"):
        return

    from app.aegis_v1.adk_runtime import collect_text
    from app.aegis_v1.library_context import (
        degraded_library_context,
        finalize_library_from_agent_retrieval,
    )
    from app.aegis_v1.library_finder_agent import parse_library_finder_response
    from app.aegis_v1.search_planner import build_baseline_query
    from app.aegis_v1.v1_config import build_v1_library_stack

    parsed = ctx.state.get("parsed_case", {})
    case_id = parsed.get("case_id", "interactive_case")
    library_stack = _injected_library_stack

    raw = _node_input_to_text(node_input)
    if not raw.strip():
        raw = collect_text([node_input]) if node_input is not None else ""

    try:
        stack = library_stack or build_v1_library_stack()
        retrieval, search_error = parse_library_finder_response(raw)
        lib_ctx = finalize_library_from_agent_retrieval(
            parsed,
            retrieval,
            case_id=case_id,
            corpus_store=stack["corpus_store"],
            discovery=stack.get("discovery"),
            refinement_client=stack.get("refinement_client"),
            cloud_library_used=bool(stack.get("uses_vertex_store")),
            search_error=search_error,
        )
        ctx.state["library_retrieval"] = lib_ctx.retrieval
        ctx.state["library_risk_flags"] = lib_ctx.risk_flags
        ctx.state["library_metadata"] = lib_ctx.metadata.model_dump()
    except Exception:
        logger.warning(
            "library_finalize_node: library agent failed; degrading to no citations",
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
# Node 5 — question_agent (pre-draft interview, INSIDE the student workflow)
# ---------------------------------------------------------------------------


@node
def question_agent_node(ctx: Any) -> None:
    """Pre-draft question agent: runs after playbook/Phoenix/library prep and
    before the drafter (D7+ — part of the Student workflow, not a wrapper).

    - Appeal: the turn-based interview already happened over HTTP; the result
      arrives via ``question_interview_json`` and is recorded for the trace
      (traced, not graded).
    - Showcase: the patient-simulator responder is injected as a module global;
      the teacher clinical file exists ONLY inside that closure (INV-QA).
    - Prep sources: the COMPLETE insurer playbook bundle (denial type is not
      knowable a priori), Phoenix memory, and library retrieval — the agent
      must not ask the patient anything those already answer; max 5 questions.

    Best-effort: any failure leaves the draft path untouched.
    """
    pre = ctx.state.get("question_interview_json", "")
    if pre:
        try:
            from app.aegis_v1.question_agent import refresh_interview_artifact

            parsed = ctx.state.get("parsed_case", {})
            notes = str(
                parsed.get("clinical_context") or ctx.state.get("clinical_context", "")
            )
            interview = refresh_interview_artifact(json.loads(pre), notes=notes)
            ctx.state["question_interview"] = interview
            if interview.get("qa_transcript"):
                ctx.state["clinical_context"] = interview["enriched_context"]
                updated = dict(parsed)
                updated["clinical_context"] = interview["enriched_context"]
                ctx.state["parsed_case"] = updated
        except Exception:
            logger.warning(
                "question_agent_node: invalid question_interview_json; ignoring",
                exc_info=True,
            )
        return

    if not ctx.state.get("run_question_agent"):
        return

    try:
        from app.aegis_v1.geo_playbook import question_agent_prep_bundle
        from app.aegis_v1.question_agent import run_question_interview

        parsed = ctx.state.get("parsed_case", {})
        override_json = ctx.state.get("geo_playbook_override_json", "")
        geo_override = json.loads(override_json) if override_json else None
        retrieval = ctx.state.get("library_retrieval", {})
        library_context = "\n".join(
            f"- {hit.get('title', '')}: {hit.get('quote', '')}"
            for hit in (retrieval.get("hits") or [])
            if isinstance(hit, dict)
        )
        result = run_question_interview(
            denial_text=str(ctx.state.get("denial_text", "")),
            notes=str(
                parsed.get("clinical_context")
                or ctx.state.get("clinical_context", "")
            ),
            playbook=question_agent_prep_bundle(
                str(parsed.get("insurer", "unknown")),
                us_playbook_override=geo_override,
            ),
            phoenix_summary=ctx.state.get("phoenix_summary", {}),
            library_context=library_context,
            responder=_injected_question_responder,
            client=_injected_question_client,
        )
        ctx.state["question_interview"] = result.model_dump()
        if result.qa_transcript:
            # Drafter sees notes + full patient Q&A transcript (minus blank/unsure).
            ctx.state["clinical_context"] = result.enriched_context
            updated = dict(parsed)
            updated["clinical_context"] = result.enriched_context
            ctx.state["parsed_case"] = updated
    except Exception:
        logger.warning(
            "question_agent_node failed; drafting without interview",
            exc_info=True,
        )


# ---------------------------------------------------------------------------
# Node 6 — drafter prep / finalize (LlmAgent graph node between them)
# ---------------------------------------------------------------------------


@node
def drafter_prep_node(ctx: Any) -> str:
    """Resolve prompt + build drafter context message for v1_drafter_agent."""
    from app.aegis_v1.drafter_client import (
        build_drafter_message,
        get_active_drafter_prompt_version,
        load_drafter_prompt,
    )
    from app.aegis_v1.schemas import Playbook, PhoenixSummary, RetrievalResult

    parsed = ctx.state.get("parsed_case", {})
    playbook_data = ctx.state.get("playbook", {})
    geo_playbook_data = ctx.state.get("geo_playbook", {})
    phoenix_data = ctx.state.get("phoenix_summary", {})
    retrieval_data = ctx.state.get("library_retrieval", {})

    prompt_version = ctx.state.get("drafter_prompt_version", "") or ""
    prompt_text = ctx.state.get("drafter_prompt_text", "") or ""
    active_version = prompt_version or get_active_drafter_prompt_version()
    resolved_prompt = prompt_text if prompt_text else load_drafter_prompt(active_version)
    ctx.state["active_prompt_version"] = active_version

    retrieval_obj = RetrievalResult.model_validate(retrieval_data)
    playbook_obj = Playbook.model_validate(playbook_data)
    phoenix_obj = PhoenixSummary.model_validate(phoenix_data)
    citations = [c.model_dump() for c in retrieval_obj.hits[:3]]

    message = build_drafter_message(
        denial_text=str(parsed.get("denial_text", "")),
        clinical_context=str(parsed.get("clinical_context", "")),
        citations=citations,
        playbook=playbook_obj.model_dump(),
        geo_playbook=geo_playbook_data or None,
        phoenix_summary=phoenix_obj.model_dump(),
    )
    return f"{resolved_prompt}\n\n{message}"


@node
def drafter_finalize_node(ctx: Any, node_input: Any = None) -> None:
    """Apply guardrails and build structured AppealDraft from drafter output."""
    from app.aegis_v1.adk_runtime import collect_text
    from app.aegis_v1.guardrails import apply_guardrails
    from app.aegis_v1.schemas import (
        AppealDraft,
        ParsedCase,
        PhoenixSummary,
        Playbook,
        RetrievalResult,
    )

    parsed = ctx.state.get("parsed_case", {})
    playbook_data = ctx.state.get("playbook", {})
    phoenix_data = ctx.state.get("phoenix_summary", {})
    retrieval_data = ctx.state.get("library_retrieval", {})
    active_version = ctx.state.get("active_prompt_version", "drafter_v1")

    case_obj = ParsedCase.model_validate(parsed)
    retrieval_obj = RetrievalResult.model_validate(retrieval_data)
    playbook_obj = Playbook.model_validate(playbook_data)
    phoenix_obj = PhoenixSummary.model_validate(phoenix_data)
    citations = retrieval_obj.hits[:3]

    raw_body = _node_input_to_text(node_input)
    if not raw_body.strip() and node_input is not None:
        if hasattr(node_input, "content"):
            raw_body = collect_text([node_input])
        elif isinstance(node_input, (list, tuple)):
            raw_body = collect_text(node_input)
    if not raw_body.strip():
        raw_body = "(No draft produced.)"

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
# Node 7 — appeal_publish (chat / ADK Runner visible response)
# ---------------------------------------------------------------------------


@node
def appeal_publish_node(ctx: Any) -> types.Content:
    """Emit the drafted appeal letter as user-visible text for ADK chat streams."""
    draft = ctx.state.get("appeal_draft", {})
    letter = str(draft.get("appeal_letter", "")).strip()
    if not letter:
        letter = (
            "Not legal or medical advice. Draft assistance only.\n\n"
            "(No draft produced.)"
        )
    return types.Content(role="model", parts=[types.Part.from_text(text=letter)])


# ---------------------------------------------------------------------------
# Workflow graph
# ---------------------------------------------------------------------------


def build_student_workflow() -> Workflow:
    """Construct the v1 student Workflow graph (D7 order).

    Reads module-level injection globals set by ``run_aegis_v1_adk_pipeline``
    before this is called so offline tests and library stack are wired correctly.
    """
    from app.aegis_v1.adk_runtime import EchoLlm, make_retry_model
    from app.aegis_v1.drafter_agent import build_v1_drafter_agent
    from app.aegis_v1.library_finder_agent import build_library_finder_agent

    drafter_model = _injected_drafter_model or make_retry_model()
    library_model = EchoLlm() if _injected_offline_pipeline else make_retry_model()

    library_finder_agent = build_library_finder_agent(
        model=library_model,
        library_stack=_injected_library_stack,
    )
    v1_drafter_agent = build_v1_drafter_agent(model=drafter_model)

    return Workflow(
        name="v1_student_workflow",
        state_schema=StudentWorkflowState,
        edges=[
            (
                START,
                case_parser_node,
                playbook_loader_node,
                geo_playbook_loader_node,
                phoenix_read_node,
                library_prep_node,
                library_finder_agent,
                library_finalize_node,
                question_agent_node,
                drafter_prep_node,
                v1_drafter_agent,
                drafter_finalize_node,
                self_check_node,
                appeal_publish_node,
            ),
        ],
    )


# Default singleton for App mounting — production model; tests rebuild after injection.
v1_student_workflow = build_student_workflow()
