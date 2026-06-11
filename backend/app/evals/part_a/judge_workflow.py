"""ADK Workflow graph for the Part A judge panel (Phase 3)."""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from google.adk import Workflow
from google.adk.workflow import START, node
from google.genai import types

from app.evals.part_a.deterministic_gates import citation_precheck
from app.evals.part_a.judge_context import grounding_judge_context
from app.evals.part_a.judge_agents import (
    build_faithfulness_judge,
    build_quality_judge_agents,
    judge_instruction,
    parse_judge_response,
)
from app.evals.part_a.schemas import JudgeResult, TeacherGradingPacket

logger = logging.getLogger(__name__)

_injected_judge_model: Any | None = None

QUALITY_DIMENSIONS = (
    "grounding",
    "case_specific_clinical_rebuttal",
    "appeal_vector_capture",
    "persuasive_coherence",
)

_JUDGE_ID_BY_DIMENSION = {
    "faithfulness_hallucination_gate": "j2_faithfulness_hallucination",
    "grounding": "j3_grounding",
    "case_specific_clinical_rebuttal": "j4_case_specific_rebuttal",
    "appeal_vector_capture": "j6_appeal_vector_capture",
    "persuasive_coherence": "j7_persuasive_coherence",
}

_PANEL_DIMENSIONS = ("faithfulness_hallucination_gate", *QUALITY_DIMENSIONS)


class JudgePanelState(BaseModel):
    """Shared state for the judge-panel Workflow."""

    panel_context_json: str = ""
    citation_precheck_json: str = ""
    faithfulness_hallucination_gate_json: str = ""
    grounding_json: str = ""
    case_specific_clinical_rebuttal_json: str = ""
    appeal_vector_capture_json: str = ""
    persuasive_coherence_json: str = ""
    judge_results_json: str = ""


def _context_from_state(ctx) -> dict[str, Any]:
    raw = ctx.state.get("panel_context_json", "")
    if not raw:
        raise ValueError("panel_context_json missing from judge workflow state")
    return json.loads(raw)


def _teacher_from_context(context: dict[str, Any]) -> TeacherGradingPacket:
    return TeacherGradingPacket.model_validate(context["teacher_packet"])


def _appeal_from_context(context: dict[str, Any]) -> dict[str, Any]:
    return dict(context["appeal_package"])


def _store_judge_result(ctx, dimension: str, result: JudgeResult) -> None:
    ctx.state[f"{dimension}_json"] = result.model_dump_json()


def _judge_message(context: dict[str, Any], judge_id: str) -> types.Content:
    if judge_id == "j3_grounding":
        context = grounding_judge_context(context)
    prompt = judge_instruction(judge_id)
    payload = json.dumps(context, indent=2, default=str)
    text = f"{prompt}\n\nCONTEXT JSON:\n{payload}"
    return types.Content(role="user", parts=[types.Part.from_text(text=text)])


def _dimension_for_judge_id(judge_id: str) -> str:
    for dimension, mapped in _JUDGE_ID_BY_DIMENSION.items():
        if mapped == judge_id:
            return dimension
    raise ValueError(f"Unknown judge id: {judge_id}")


def _collect_text_from_join_value(value: Any) -> str:
    if isinstance(value, dict):
        return json.dumps(value)
    if isinstance(value, str):
        return value
    if isinstance(value, types.Content):
        parts: list[str] = []
        for part in value.parts or []:
            if part.text:
                parts.append(part.text)
        return "".join(parts)
    return str(value)


@node
def citation_precheck_node(ctx, node_input):
    context = _context_from_state(ctx)
    teacher = _teacher_from_context(context)
    appeal = _appeal_from_context(context)
    citation = citation_precheck(appeal, teacher)
    ctx.state["citation_precheck_json"] = citation.model_dump_json()
    context["deterministic_results"] = {"citation_precheck": citation.model_dump()}
    ctx.state["panel_context_json"] = json.dumps(context, default=str)
    ctx.route = "fail" if citation.score == "FAIL" else "pass"
    return node_input


@node
def faithfulness_shortcut_node(ctx, node_input):
    citation = json.loads(ctx.state["citation_precheck_json"])
    result = JudgeResult(
        dimension="faithfulness_hallucination_gate",
        reasoning=str(citation.get("reasoning", "")),
        score="FAIL",
        confidence=float(citation.get("confidence", 0.0)),
        evidence_quotes=list(citation.get("evidence_quotes", []) or []),
        improvement=citation.get("improvement"),
    )
    _store_judge_result(ctx, "faithfulness_hallucination_gate", result)
    return node_input


@node
def faithfulness_prep_node(ctx, node_input):
    return _judge_message(_context_from_state(ctx), "j2_faithfulness_hallucination")


@node
def faithfulness_finalize_node(ctx, node_input):
    text = _collect_text_from_join_value(node_input)
    result = parse_judge_response(text, "faithfulness_hallucination_gate")
    _store_judge_result(ctx, "faithfulness_hallucination_gate", result)
    return node_input


@node
def quality_judges_prep_node(ctx, node_input):
    return _quality_prep_content(ctx, for_dimension="grounding")


def _quality_prep_content(ctx, *, for_dimension: str | None = None) -> types.Content:
    context = _context_from_state(ctx)
    if for_dimension == "grounding":
        context = grounding_judge_context(context)
    payload = json.dumps(context, indent=2, default=str)
    return types.Content(
        role="user",
        parts=[types.Part.from_text(text=f"CONTEXT JSON:\n{payload}")],
    )


@node
def grounding_finalize_node(ctx, node_input):
    _store_judge_result(
        ctx, "grounding", parse_judge_response(_collect_text_from_join_value(node_input), "grounding")
    )
    return _quality_prep_content(ctx)


@node
def case_specific_finalize_node(ctx, node_input):
    _store_judge_result(
        ctx,
        "case_specific_clinical_rebuttal",
        parse_judge_response(
            _collect_text_from_join_value(node_input), "case_specific_clinical_rebuttal"
        ),
    )
    return _quality_prep_content(ctx)


@node
def appeal_vector_finalize_node(ctx, node_input):
    _store_judge_result(
        ctx,
        "appeal_vector_capture",
        parse_judge_response(
            _collect_text_from_join_value(node_input), "appeal_vector_capture"
        ),
    )
    return _quality_prep_content(ctx)


@node
def persuasive_finalize_node(ctx, node_input):
    _store_judge_result(
        ctx,
        "persuasive_coherence",
        parse_judge_response(
            _collect_text_from_join_value(node_input), "persuasive_coherence"
        ),
    )
    return node_input


@node
def aggregate_panel_node(ctx, node_input):
    del node_input
    results: dict[str, Any] = {}
    for dimension in _PANEL_DIMENSIONS:
        raw = ctx.state.get(f"{dimension}_json", "")
        if raw:
            results[dimension] = json.loads(raw)
    ctx.state["judge_results_json"] = json.dumps(results)
    return "done"


def build_judge_panel_workflow() -> Workflow:
    """Construct the judge-panel Workflow (sequential quality judges for prod stability)."""
    from app.aegis_v1.adk_runtime import make_retry_model

    model = _injected_judge_model or make_retry_model()
    faithfulness = build_faithfulness_judge(model=model)
    quality = build_quality_judge_agents(model=model)

    return Workflow(
        name="judge_panel_workflow",
        state_schema=JudgePanelState,
        edges=[
            (START, citation_precheck_node),
            (
                citation_precheck_node,
                {
                    "fail": faithfulness_shortcut_node,
                    "pass": faithfulness_prep_node,
                },
            ),
            (faithfulness_prep_node, faithfulness, faithfulness_finalize_node),
            (faithfulness_shortcut_node, quality_judges_prep_node),
            (faithfulness_finalize_node, quality_judges_prep_node),
            (quality_judges_prep_node, quality["grounding"], grounding_finalize_node),
            (grounding_finalize_node, quality["case_specific_clinical_rebuttal"], case_specific_finalize_node),
            (case_specific_finalize_node, quality["appeal_vector_capture"], appeal_vector_finalize_node),
            (appeal_vector_finalize_node, quality["persuasive_coherence"], persuasive_finalize_node),
            (persuasive_finalize_node, aggregate_panel_node),
        ],
    )


def _configure_judge_model(model: Any | None) -> None:
    global _injected_judge_model
    _injected_judge_model = model


def _clear_judge_model() -> None:
    global _injected_judge_model
    _injected_judge_model = None


def _assemble_judge_results(
    state: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, JudgeResult]:
    """Build a complete judge map from workflow state with deterministic fallbacks."""
    del context
    assembled: dict[str, JudgeResult] = {}

    bundled_raw = state.get("judge_results_json", "")
    if bundled_raw:
        try:
            bundled = json.loads(bundled_raw)
            if isinstance(bundled, dict):
                for dimension, payload in bundled.items():
                    assembled[str(dimension)] = JudgeResult.model_validate(payload)
        except Exception:
            logger.warning("judge_results_json parse failed", exc_info=True)

    for dimension in _PANEL_DIMENSIONS:
        if dimension in assembled:
            continue
        chunk = state.get(f"{dimension}_json", "")
        if not chunk:
            continue
        assembled[dimension] = JudgeResult.model_validate(json.loads(chunk))

    missing = [dimension for dimension in _PANEL_DIMENSIONS if dimension not in assembled]
    if missing:
        raise ValueError(f"judge panel incomplete after workflow: missing {missing}")
    return assembled


def _run_judge_panel_workflow_once(
    *,
    context: dict[str, Any],
    model: Any | None,
) -> dict[str, JudgeResult]:
    import uuid

    from app.aegis_v1.adk_runtime import run_workflow_sync

    _configure_judge_model(model)
    try:
        workflow = build_judge_panel_workflow()
        result = run_workflow_sync(
            workflow,
            app_name="aegis_judge_panel",
            user_id=f"judge_panel_{uuid.uuid4().hex[:10]}",
            initial_state={"panel_context_json": json.dumps(context, default=str)},
            message="judge",
        )
    finally:
        _clear_judge_model()

    return _assemble_judge_results(dict(result.get("state") or {}), context)


def run_judge_panel_workflow(
    *,
    context: dict[str, Any],
    model: Any | None = None,
    max_attempts: int = 2,
) -> dict[str, JudgeResult]:
    """Run the full judge-panel ADK Workflow and return all judge results."""
    import time

    from app import gemini_retry

    last_error: Exception | None = None
    attempts = max(1, max_attempts)
    for attempt in range(attempts):
        if attempt > 0:
            gemini_retry.pace_gemini_call()
            time.sleep(1.0)
            logger.warning(
                "retrying judge_panel_workflow after incomplete/failed attempt %s",
                attempt,
            )
        try:
            return _run_judge_panel_workflow_once(context=context, model=model)
        except ValueError as exc:
            last_error = exc
            if "incomplete" not in str(exc) or attempt >= attempts - 1:
                raise
        except Exception as exc:
            last_error = exc
            if attempt >= attempts - 1:
                raise
    if last_error is not None:
        raise last_error
    raise RuntimeError("judge_panel_workflow failed without raising")


def run_single_judge_sync(
    *,
    judge_id: str,
    dimension: str,
    context: dict[str, Any],
    model: Any | None = None,
) -> JudgeResult:
    """Run one judge LlmAgent outside the panel Workflow (legacy helper)."""
    from app.aegis_v1.adk_runtime import collect_text, run_llm_agent_sync
    from app.evals.part_a.judge_agents import build_judge_agent

    agent = build_judge_agent(
        judge_id=judge_id,
        dimension=dimension,
        name=f"{dimension}_single",
        model=model,
    )
    message = _judge_message(context, judge_id).parts[0].text or ""
    result = run_llm_agent_sync(
        agent,
        app_name="aegis_judge_single",
        user_id="judge_single",
        message=message,
    )
    text = collect_text(result.get("events", [])).strip()
    if not text:
        raise ValueError(f"{dimension} judge returned empty response")
    return parse_judge_response(text, dimension)
