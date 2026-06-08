"""ADK Workflow graph for the Part A judge panel (Phase 3)."""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from google.adk import Workflow
from google.adk.workflow import START, JoinNode, node
from google.genai import types

from app.evals.part_a.deterministic_gates import citation_precheck, safety_scope_gate
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
    "evidence_completeness",
    "appeal_vector_capture",
    "persuasive_coherence",
)

_JUDGE_ID_BY_DIMENSION = {
    "faithfulness_hallucination_gate": "j2_faithfulness_hallucination",
    "grounding": "j3_grounding",
    "case_specific_clinical_rebuttal": "j4_case_specific_rebuttal",
    "evidence_completeness": "j5_evidence_completeness",
    "appeal_vector_capture": "j6_appeal_vector_capture",
    "persuasive_coherence": "j7_persuasive_coherence",
}


class JudgePanelState(BaseModel):
    """Shared state for the judge-panel Workflow."""

    panel_context_json: str = ""
    safety_scope_gate_json: str = ""
    citation_precheck_json: str = ""
    faithfulness_hallucination_gate_json: str = ""
    grounding_json: str = ""
    case_specific_clinical_rebuttal_json: str = ""
    evidence_completeness_json: str = ""
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
def safety_scope_gate_node(ctx, node_input):
    context = _context_from_state(ctx)
    teacher = _teacher_from_context(context)
    appeal = _appeal_from_context(context)
    result = safety_scope_gate(appeal, teacher)
    _store_judge_result(ctx, "safety_scope_gate", result)
    return node_input


@node
def citation_precheck_node(ctx, node_input):
    context = _context_from_state(ctx)
    teacher = _teacher_from_context(context)
    appeal = _appeal_from_context(context)
    citation = citation_precheck(appeal, teacher)
    ctx.state["citation_precheck_json"] = citation.model_dump_json()
    context["deterministic_results"] = {
        "safety_scope_gate": json.loads(ctx.state["safety_scope_gate_json"]),
        "citation_precheck": citation.model_dump(),
    }
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
    return _quality_prep_content(ctx)


@node
def faithfulness_prep_node(ctx, node_input):
    return _judge_message(_context_from_state(ctx), "j2_faithfulness_hallucination")


@node
def faithfulness_finalize_node(ctx, node_input):
    text = _collect_text_from_join_value(node_input)
    result = parse_judge_response(text, "faithfulness_hallucination_gate")
    _store_judge_result(ctx, "faithfulness_hallucination_gate", result)
    return _quality_prep_content(ctx)


def _quality_prep_content(ctx) -> types.Content:
    context = _context_from_state(ctx)
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
    return None


@node
def case_specific_finalize_node(ctx, node_input):
    _store_judge_result(
        ctx,
        "case_specific_clinical_rebuttal",
        parse_judge_response(
            _collect_text_from_join_value(node_input), "case_specific_clinical_rebuttal"
        ),
    )
    return None


@node
def evidence_finalize_node(ctx, node_input):
    _store_judge_result(
        ctx,
        "evidence_completeness",
        parse_judge_response(
            _collect_text_from_join_value(node_input), "evidence_completeness"
        ),
    )
    return None


@node
def appeal_vector_finalize_node(ctx, node_input):
    _store_judge_result(
        ctx,
        "appeal_vector_capture",
        parse_judge_response(
            _collect_text_from_join_value(node_input), "appeal_vector_capture"
        ),
    )
    return None


@node
def persuasive_finalize_node(ctx, node_input):
    _store_judge_result(
        ctx,
        "persuasive_coherence",
        parse_judge_response(
            _collect_text_from_join_value(node_input), "persuasive_coherence"
        ),
    )
    return None


@node
def aggregate_panel_node(ctx, node_input):
    del node_input
    results: dict[str, Any] = {}
    for dimension in ("safety_scope_gate", "faithfulness_hallucination_gate", *QUALITY_DIMENSIONS):
        raw = ctx.state.get(f"{dimension}_json", "")
        if raw:
            results[dimension] = json.loads(raw)
    ctx.state["judge_results_json"] = json.dumps(results)
    return "done"


def build_judge_panel_workflow() -> Workflow:
    """Construct the judge-panel Workflow with parallel quality fan-out."""
    from app.aegis_v1.adk_runtime import make_retry_model

    model = _injected_judge_model or make_retry_model()
    faithfulness = build_faithfulness_judge(model=model)
    quality = build_quality_judge_agents(model=model)
    join_quality = JoinNode(name="join_quality_judges")

    return Workflow(
        name="judge_panel_workflow",
        state_schema=JudgePanelState,
        edges=[
            (START, safety_scope_gate_node, citation_precheck_node),
            (
                citation_precheck_node,
                {
                    "fail": faithfulness_shortcut_node,
                    "pass": faithfulness_prep_node,
                },
            ),
            (faithfulness_prep_node, faithfulness, faithfulness_finalize_node),
            (
                faithfulness_shortcut_node,
                (
                    quality["grounding"],
                    quality["case_specific_clinical_rebuttal"],
                    quality["evidence_completeness"],
                    quality["appeal_vector_capture"],
                    quality["persuasive_coherence"],
                ),
            ),
            (
                faithfulness_finalize_node,
                (
                    quality["grounding"],
                    quality["case_specific_clinical_rebuttal"],
                    quality["evidence_completeness"],
                    quality["appeal_vector_capture"],
                    quality["persuasive_coherence"],
                ),
            ),
            (quality["grounding"], grounding_finalize_node, join_quality),
            (
                quality["case_specific_clinical_rebuttal"],
                case_specific_finalize_node,
                join_quality,
            ),
            (quality["evidence_completeness"], evidence_finalize_node, join_quality),
            (quality["appeal_vector_capture"], appeal_vector_finalize_node, join_quality),
            (quality["persuasive_coherence"], persuasive_finalize_node, join_quality),
            (join_quality, aggregate_panel_node),
        ],
    )


def _configure_judge_model(model: Any | None) -> None:
    global _injected_judge_model
    _injected_judge_model = model


def _clear_judge_model() -> None:
    global _injected_judge_model
    _injected_judge_model = None


def run_judge_panel_workflow(
    *,
    context: dict[str, Any],
    model: Any | None = None,
) -> dict[str, JudgeResult]:
    """Run the full judge-panel ADK Workflow and return all judge results."""
    from app.aegis_v1.adk_runtime import run_workflow_sync

    _configure_judge_model(model)
    try:
        workflow = build_judge_panel_workflow()
        result = run_workflow_sync(
            workflow,
            app_name="aegis_judge_panel",
            user_id="judge_panel",
            initial_state={"panel_context_json": json.dumps(context, default=str)},
            message="judge",
        )
    finally:
        _clear_judge_model()

    raw = result["state"].get("judge_results_json", "{}")
    data = json.loads(raw or "{}")
    return {dimension: JudgeResult.model_validate(payload) for dimension, payload in data.items()}


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
