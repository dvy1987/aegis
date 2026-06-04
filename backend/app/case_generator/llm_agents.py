"""Gemini/Vertex LLM producer + critic calls for the canonical ``llm_pipeline.py``."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from google import genai
from google.genai import types

from .config import DEFAULT_MODEL
from .prompts import load_prompt

logger = logging.getLogger(__name__)

_ENVELOPE = load_prompt("_critic_envelope")


def _client() -> genai.Client:
    return genai.Client(vertexai=True, location="global")

def _format_prompt(template: str, **kwargs: Any) -> str:
    for k, v in kwargs.items():
        template = template.replace(f"{{{k}}}", str(v))
    return template


def _generate_json(
    prompt: str, model: str | None = None, temperature: float = 0.7
) -> dict[str, Any]:
    """Single JSON-strict LLM call. Returns parsed dict.

    Uses google-genai SDK with response_mime_type=application/json so the model
    is forced to emit a valid JSON object (no markdown fences).
    """
    model_name = model or DEFAULT_MODEL
    client = _client()
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=temperature,
        ),
    )
    text = response.text or ""
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error("Model returned non-JSON: %s", text[:200])
        raise RuntimeError(f"Model returned invalid JSON: {exc}") from exc


# -- Producers -----------------------------------------------------------------


def run_scenario_planner(
    matrix_cell: dict[str, str],
    sub_tactic_definition: str,
    specialty_examples: list[str],
    joint_constraints: str,
    patterns: list[dict[str, Any]],
    *,
    clinical_variants: str = "",
    model: str | None = None,
) -> dict[str, Any]:
    prompt = _format_prompt(
        load_prompt("p1_scenario_planner"),
        joint_constraints=joint_constraints,
        matrix_cell_json=json.dumps(matrix_cell, indent=2),
        sub_tactic_definition=sub_tactic_definition,
        specialty_examples=", ".join(specialty_examples) or "(none listed)",
        clinical_variants=clinical_variants or "(no curated variants; use real-world knowledge)",
        patterns_json=json.dumps(patterns, indent=2) if patterns else "[]",
    )
    return _generate_json(prompt, model=model, temperature=0.9)


def run_denial_drafter(
    scenario_brief: dict[str, Any], *, model: str | None = None
) -> dict[str, Any]:
    prompt = _format_prompt(
        load_prompt("p2_denial_drafter"),
        scenario_brief_json=json.dumps(scenario_brief, indent=2),
    )
    return _generate_json(prompt, model=model, temperature=0.75)


def run_clinical_writer(
    scenario_brief: dict[str, Any], denial_letter_text: str, *, model: str | None = None
) -> dict[str, Any]:
    prompt = _format_prompt(
        load_prompt("p3_clinical_writer"),
        scenario_brief_json=json.dumps(scenario_brief, indent=2),
        denial_letter_text=denial_letter_text,
    )
    return _generate_json(prompt, model=model, temperature=0.8)


def run_realistic_flaw_injector(
    assembled_case: dict[str, Any],
    intended_flaw_types: list[str],
    patterns: list[dict[str, Any]],
    *,
    model: str | None = None,
) -> dict[str, Any]:
    prompt = _format_prompt(
        load_prompt("p4_realistic_flaw_injector"),
        assembled_case_json=json.dumps(assembled_case, indent=2),
        intended_flaw_types=json.dumps(intended_flaw_types, indent=2),
        patterns_json=json.dumps(patterns, indent=2) if patterns else "[]",
    )
    return _generate_json(prompt, model=model, temperature=0.85)


def run_stylistic_diversifier(
    assembled_case: dict[str, Any],
    neighbour_summaries: str,
    *,
    model: str | None = None,
) -> dict[str, Any]:
    prompt = _format_prompt(
        load_prompt("p5_stylistic_diversifier"),
        assembled_case_json=json.dumps(assembled_case, indent=2),
        neighbour_summaries=neighbour_summaries or "(this is the first case in the run)",
    )
    return _generate_json(prompt, model=model, temperature=0.85)


# -- Critics -------------------------------------------------------------------


def _critic_model() -> str:
    """Critic model. Falls back to DEFAULT_MODEL.

    Backend AGENTS.md prefers a different family for critics vs drafters to
    avoid self-enhancement bias; in the current env we only have Gemini via
    Vertex, so we set a different temperature instead and document the
    limitation in the handoff.
    """
    return os.environ.get("AEGIS_CASEGEN_CRITIC_MODEL", DEFAULT_MODEL)


def _run_critic(prompt_id: str, **fmt: Any) -> dict[str, Any]:
    template = load_prompt(prompt_id)
    prompt = _format_prompt(template, envelope=_ENVELOPE, **fmt)
    return _generate_json(prompt, model=_critic_model(), temperature=0.2)


def critic_matrix_coverage(
    scenario_brief: dict[str, Any], assigned_cell: dict[str, str]
) -> dict[str, Any]:
    return _run_critic(
        "c_matrix_coverage",
        assigned_matrix_cell_json=json.dumps(assigned_cell, indent=2),
        scenario_brief_json=json.dumps(scenario_brief, indent=2),
    )


def critic_scenario_realism(scenario_brief: dict[str, Any]) -> dict[str, Any]:
    return _run_critic(
        "c_scenario_realism",
        scenario_brief_json=json.dumps(scenario_brief, indent=2),
    )


def critic_insurer_voice(insurer: str, denial_letter_text: str) -> dict[str, Any]:
    return _run_critic(
        "c_insurer_voice",
        insurer=insurer,
        denial_letter_text=denial_letter_text,
    )


def critic_denial_logic(
    sub_tactic: str, sub_tactic_definition: str, denial_letter_text: str
) -> dict[str, Any]:
    return _run_critic(
        "c_denial_logic",
        sub_tactic=sub_tactic,
        sub_tactic_definition=sub_tactic_definition,
        denial_letter_text=denial_letter_text,
    )


def critic_clinical_realism(
    diagnosis: str, treatment_requested: str, clinical_context: str
) -> dict[str, Any]:
    return _run_critic(
        "c_clinical_realism",
        diagnosis=diagnosis,
        treatment_requested=treatment_requested,
        clinical_context=clinical_context,
    )


def critic_diagnosis_treatment_match(
    diagnosis: str, treatment_requested: str
) -> dict[str, Any]:
    return _run_critic(
        "c_diagnosis_treatment_match",
        diagnosis=diagnosis,
        treatment_requested=treatment_requested,
    )


def critic_diversity_delta(
    this_case_summary: str, neighbour_summaries: str
) -> dict[str, Any]:
    return _run_critic(
        "c_diversity_delta",
        this_case_summary=this_case_summary,
        neighbour_summaries=neighbour_summaries or "(no neighbours yet)",
    )


def critic_safety_redactor(
    banned_topic_briefs: str, denial_letter_text: str, clinical_context: str
) -> dict[str, Any]:
    return _run_critic(
        "c_safety_redactor",
        banned_topic_briefs=banned_topic_briefs,
        denial_letter_text=denial_letter_text,
        clinical_context=clinical_context,
    )


def critic_contradiction_hunter(
    patient_profile: dict[str, Any],
    diagnosis: str,
    treatment_requested: str,
    denial_letter_text: str,
    clinical_context: str,
) -> dict[str, Any]:
    return _run_critic(
        "c_contradiction_hunter",
        patient_profile_json=json.dumps(patient_profile, indent=2),
        diagnosis=diagnosis,
        treatment_requested=treatment_requested,
        denial_letter_text=denial_letter_text,
        clinical_context=clinical_context,
    )


def critic_llm_tell_detector(
    denial_letter_text: str, clinical_context: str
) -> dict[str, Any]:
    return _run_critic(
        "c_llm_tell_detector",
        denial_letter_text=denial_letter_text,
        clinical_context=clinical_context,
    )


def critic_overall_tone(
    denial_letter_text: str, clinical_context: str
) -> dict[str, Any]:
    return _run_critic(
        "c_overall_tone",
        denial_letter_text=denial_letter_text,
        clinical_context=clinical_context,
    )


def critic_financial_auditor(
    denial_letter_text: str, clinical_context: str
) -> dict[str, Any]:
    return _run_critic(
        "c_financial_auditor",
        denial_letter_text=denial_letter_text,
        clinical_context=clinical_context,
    )


def critic_legal_auditor(
    denial_letter_text: str, clinical_context: str
) -> dict[str, Any]:
    return _run_critic(
        "c_legal_auditor",
        denial_letter_text=denial_letter_text,
        clinical_context=clinical_context,
    )


def critic_demographic_validator(
    patient_profile: dict[str, Any], denial_letter_text: str, clinical_context: str
) -> dict[str, Any]:
    return _run_critic(
        "c_demographic_validator",
        patient_profile_json=json.dumps(patient_profile, indent=2),
        denial_letter_text=denial_letter_text,
        clinical_context=clinical_context,
    )


def critic_scope_guard(
    patient_profile: dict[str, Any],
    insurer: str,
    denial_type: str,
    denial_letter_text: str,
    clinical_context: str,
) -> dict[str, Any]:
    return _run_critic(
        "c_scope_guard",
        patient_profile_json=json.dumps(patient_profile, indent=2),
        insurer=insurer,
        denial_type=denial_type,
        denial_letter_text=denial_letter_text,
        clinical_context=clinical_context,
    )


def critic_date_sanity(
    denial_letter_text: str, clinical_context: str
) -> dict[str, Any]:
    return _run_critic(
        "c_date_sanity",
        denial_letter_text=denial_letter_text,
        clinical_context=clinical_context,
    )


def critic_citation_traceability(denial_letter_text: str) -> dict[str, Any]:
    return _run_critic(
        "c_citation_traceability",
        denial_letter_text=denial_letter_text,
    )


def critic_appeal_difficulty(
    denial_letter_text: str, clinical_context: str
) -> dict[str, Any]:
    return _run_critic(
        "c_appeal_difficulty",
        denial_letter_text=denial_letter_text,
        clinical_context=clinical_context,
    )


def critic_flaw_injection_verifier(
    denial_letter_text: str,
    clinical_context: str,
    patterns_to_check: list[dict[str, Any]],
    *,
    submission_timestamp: str | None = None,
    denial_timestamp: str | None = None,
) -> dict[str, Any]:
    """LLM check that each semantic ('needs_llm') flaw is discoverable in student-visible text.

    Returns {"verification_results": [{pattern_id, status, evidence}], "absent": [...]}.
    """
    prompt = _format_prompt(
        load_prompt("c_flaw_injection_verifier"),
        denial_letter_text=denial_letter_text,
        clinical_context=clinical_context,
        patterns_to_check=json.dumps(patterns_to_check, indent=2),
        submission_timestamp=submission_timestamp or "null",
        denial_timestamp=denial_timestamp or "null",
    )
    return _generate_json(prompt, model=_critic_model(), temperature=0.2)
