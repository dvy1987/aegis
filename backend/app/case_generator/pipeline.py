"""Orchestrates the per-stage producer→critic generation swarm.

AlphaEval rules enforced in this orchestrator:
- Forced 1/3/5 anchors on weighted-dim critics; binary PASS/FAIL on hard gates.
- A 1 on any weighted-dim critic triggers up to 2 stage-local revisions.
- A FAIL on any binary hard-gate critic triggers an immediate stage rewind;
  a second FAIL discards the scenario and the planner re-rolls.
- Each critic sees only its own stage's artifact and its own rubric.
"""

from __future__ import annotations

import logging
import random
import uuid
from datetime import UTC, datetime
from typing import Any

from . import agents, config
from .prompts import PROMPT_VERSIONS
from .safety import banned_topic_briefs, scan_banned, scan_phi
from .validator import validate_case

logger = logging.getLogger(__name__)

MAX_STAGE_REVISIONS = 2
MAX_SCENARIO_RETRIES = 4

HARD_GATE_DIMS = {
    "matrix_coverage",
    "diagnosis_treatment_match",
    "safety_redactor",
    "contradiction_hunter",
    "llm_tell_detector",
    "scope_guard",
}


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_pass(verdict: dict[str, Any]) -> bool:
    score = verdict.get("score")
    if isinstance(score, str):
        return score.upper() == "PASS"
    return score in (3, 5)


def _is_fail(verdict: dict[str, Any]) -> bool:
    score = verdict.get("score")
    if isinstance(score, str):
        return score.upper() == "FAIL"
    return score == 1


def _summary_for_neighbours(case: dict[str, Any]) -> str:
    return (
        f"- [{case['matrix_cell']['insurer']} / {case['matrix_cell']['denial_type']} / "
        f"{case['matrix_cell']['specialty']} / {case['matrix_cell']['sub_tactic']}] "
        f"dx={case['diagnosis']}; tx={case['treatment_requested']}"
    )


class ScenarioDiscarded(Exception):
    """Raised when a scenario must be discarded and re-rolled by the planner."""


def _scenario_planner_stage(
    matrix_cell: dict[str, str],
    patterns: list[dict[str, Any]],
    *,
    revisions: int = 0,
    prior_brief: dict[str, Any] | None = None,
    prior_critique: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Plan + critique. Returns (scenario_brief, critic_outputs)."""
    sub_def = config.sub_tactic_definition(
        matrix_cell["denial_type"], matrix_cell["sub_tactic"]
    )
    examples = config.specialty_examples(matrix_cell["specialty"])
    constraints = config.joint_constraints_text()

    brief = agents.run_scenario_planner(
        matrix_cell=matrix_cell,
        sub_tactic_definition=sub_def,
        specialty_examples=examples,
        joint_constraints=constraints,
        patterns=patterns,
    )

    cov = agents.critic_matrix_coverage(brief, matrix_cell)
    realism = agents.critic_scenario_realism(brief)
    critics = {"matrix_coverage": cov, "scenario_realism": realism}

    if not _is_pass(cov):
        if revisions >= MAX_STAGE_REVISIONS:
            raise ScenarioDiscarded(f"matrix_coverage FAIL after {revisions} revisions")
        return _scenario_planner_stage(
            matrix_cell,
            patterns,
            revisions=revisions + 1,
            prior_brief=brief,
            prior_critique=cov.get("improvement"),
        )
    if realism.get("score") == 1:
        if revisions >= MAX_STAGE_REVISIONS:
            raise ScenarioDiscarded("scenario_realism = 1 after revisions")
        return _scenario_planner_stage(
            matrix_cell,
            patterns,
            revisions=revisions + 1,
            prior_brief=brief,
            prior_critique=realism.get("improvement"),
        )
    return brief, critics


def _denial_drafter_stage(
    brief: dict[str, Any], *, revisions: int = 0
) -> tuple[str, dict[str, Any]]:
    out = agents.run_denial_drafter(brief)
    letter = out["denial_letter_text"]
    voice = agents.critic_insurer_voice(brief["matrix_cell"]["insurer"], letter)
    logic = agents.critic_denial_logic(
        brief["matrix_cell"]["sub_tactic"],
        config.sub_tactic_definition(
            brief["matrix_cell"]["denial_type"], brief["matrix_cell"]["sub_tactic"]
        ),
        letter,
    )
    critics = {"insurer_voice": voice, "denial_logic": logic}
    fail = voice.get("score") == 1 or logic.get("score") == 1
    if fail and revisions < MAX_STAGE_REVISIONS:
        return _denial_drafter_stage(brief, revisions=revisions + 1)
    return letter, critics


def _clinical_writer_stage(
    brief: dict[str, Any], letter: str, *, revisions: int = 0
) -> tuple[str, dict[str, Any]]:
    out = agents.run_clinical_writer(brief, letter)
    ctx = out["clinical_context"]
    realism = agents.critic_clinical_realism(
        brief["diagnosis"], brief["treatment_requested"], ctx
    )
    match = agents.critic_diagnosis_treatment_match(
        brief["diagnosis"], brief["treatment_requested"]
    )
    critics = {"clinical_realism": realism, "diagnosis_treatment_match": match}
    bad = realism.get("score") == 1 or _is_fail(match)
    if bad and revisions < MAX_STAGE_REVISIONS:
        return _clinical_writer_stage(brief, letter, revisions=revisions + 1)
    return ctx, critics


def _flaw_injector_stage(
    assembled: dict[str, Any],
    intended_flaws: list[str],
    patterns: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    perturbed = agents.run_realistic_flaw_injector(assembled, intended_flaws, patterns)
    return perturbed, {}


def _stylistic_diversifier_stage(
    assembled: dict[str, Any],
    neighbour_summaries: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    ns_text = "\n".join(f"- {s}" for s in neighbour_summaries)
    stylized = agents.run_stylistic_diversifier(assembled, ns_text)
    return stylized, {}


def _safety_stage(denial_letter_text: str, clinical_context: str) -> dict[str, Any]:
    hits = scan_banned(denial_letter_text + "\n" + clinical_context)
    if hits:
        return {
            "dimension": "safety_redactor",
            "reasoning": "Deterministic regex matched banned topic(s): "
            + ", ".join(f"{h.topic_id}:{h.matched_text}" for h in hits),
            "score": "FAIL",
            "confidence": 1.0,
            "evidence_quotes": [h.matched_text for h in hits],
            "improvement": "Re-roll scenario; do not include banned content.",
        }
    return agents.critic_safety_redactor(
        banned_topic_briefs(), denial_letter_text, clinical_context
    )


def _phi_stage(denial_letter_text: str, clinical_context: str) -> dict[str, Any]:
    hits = scan_phi(denial_letter_text + "\n" + clinical_context)
    if hits:
        return {
            "dimension": "phi_pii",
            "reasoning": "Deterministic PHI patterns detected: "
            + ", ".join(f"{h.label}:{h.matched_text}" for h in hits),
            "score": "FAIL",
            "confidence": 1.0,
            "evidence_quotes": [h.matched_text for h in hits],
            "improvement": "Strip PHI patterns from generated text.",
        }
    return {
        "dimension": "phi_pii",
        "reasoning": "No deterministic PHI patterns detected.",
        "score": "PASS",
        "confidence": 1.0,
        "evidence_quotes": [],
        "improvement": None,
    }


def _final_panel(
    patient_profile: dict[str, Any],
    diagnosis: str,
    treatment_requested: str,
    insurer: str,
    denial_type: str,
    denial_letter_text: str,
    clinical_context: str,
) -> dict[str, Any]:
    """Independent final-assembly mini-panel. Each critic is an independent call."""
    return {
        "contradiction_hunter": agents.critic_contradiction_hunter(
            patient_profile,
            diagnosis,
            treatment_requested,
            denial_letter_text,
            clinical_context,
        ),
        "llm_tell_detector": agents.critic_llm_tell_detector(
            denial_letter_text, clinical_context
        ),
        "overall_tone": agents.critic_overall_tone(
            denial_letter_text, clinical_context
        ),
        "financial_auditor": agents.critic_financial_auditor(
            denial_letter_text, clinical_context
        ),
        "legal_auditor": agents.critic_legal_auditor(
            denial_letter_text, clinical_context
        ),
        "demographic_validator": agents.critic_demographic_validator(
            patient_profile, denial_letter_text, clinical_context
        ),
        "scope_guard": agents.critic_scope_guard(
            patient_profile, insurer, denial_type, denial_letter_text, clinical_context
        ),
        "date_sanity": agents.critic_date_sanity(denial_letter_text, clinical_context),
        "citation_traceability": agents.critic_citation_traceability(
            denial_letter_text
        ),
        "appeal_difficulty": agents.critic_appeal_difficulty(
            denial_letter_text, clinical_context
        ),
    }


VALUE_WEIGHTS = {
    "clinical_realism": 1.5,
    "denial_logic": 1.5,
    "scenario_realism": 1.2,
}

def _verdicts_summary(critics: dict[str, dict[str, Any]]) -> tuple[bool, list[str]]:
    """Return (panel_pass, fail_reasons)."""
    failures: list[str] = []
    total_weight = 0.0
    weighted_sum = 0.0

    for dim, v in critics.items():
        if dim == "appeal_difficulty":
            continue  # Informational only, does not gate generation

        weight = VALUE_WEIGHTS.get(dim, 1.0)
        
        if dim in HARD_GATE_DIMS:
            if _is_fail(v):
                failures.append(
                    f"{dim}: HARD-GATE FAIL — {v.get('reasoning', '')[:120]}"
                )
        else:
            score = v.get("score")
            if isinstance(score, int):
                total_weight += weight
                weighted_sum += score * weight
                if score == 1:
                    failures.append(f"{dim}: weighted=1 — {v.get('reasoning', '')[:120]}")
    
    if total_weight > 0:
        logger.info("Case weighted score: %.2f", weighted_sum / total_weight)

    return (len(failures) == 0, failures)


def _case_id_for(insurer: str, denial_type: str, index: int) -> str:
    short = "mednec" if denial_type == "Medical Necessity" else "priorauth"
    return f"case_{index:02d}_{insurer.lower()}_{short}"


def generate_one_case(
    *,
    index: int,
    rng: random.Random,
    accepted_cells: set[tuple[str, ...]],
    neighbour_summaries: list[str],
    run_id: str,
) -> dict[str, Any] | None:
    """Run the full swarm for a single case. Returns the case dict or None on discard."""
    for retry in range(MAX_SCENARIO_RETRIES):
        cell = config.sample_matrix_cell(rng, forbid_cells=accepted_cells)
        patterns = config.sample_denial_patterns(rng, cell["insurer"], cell["specialty"])
        logger.info("[case %d retry %d] matrix cell %s", index, retry, cell)
        try:
            brief, planner_critics = _scenario_planner_stage(cell, patterns)
        except ScenarioDiscarded as exc:
            logger.warning("scenario discarded: %s", exc)
            continue

        letter, drafter_critics = _denial_drafter_stage(brief)
        ctx, writer_critics = _clinical_writer_stage(brief, letter)

        assembled = {
            "matrix_cell": cell,
            "diagnosis": brief["diagnosis"],
            "treatment_requested": brief["treatment_requested"],
            "denial_letter_text": letter,
            "clinical_context": ctx,
        }
        perturbed, div_critics = _flaw_injector_stage(assembled, brief.get("intended_flaw_types", []), patterns)
        assembled_for_p5 = {**assembled, **perturbed}
        stylized, style_critics = _stylistic_diversifier_stage(assembled_for_p5, neighbour_summaries)

        safety_v = _safety_stage(
            stylized["denial_letter_text"], stylized["clinical_context"]
        )
        phi_v = _phi_stage(
            stylized["denial_letter_text"], stylized["clinical_context"]
        )

        if _is_fail(safety_v) or _is_fail(phi_v):
            logger.warning(
                "safety/phi HARD-GATE FAIL on case %d retry %d — re-rolling",
                index,
                retry,
            )
            continue

        patient_profile = {
            "age": brief["patient_age"],
            "gender": brief["patient_gender"],
            "diagnosis": stylized["diagnosis"],
            "treatment_requested": stylized["treatment_requested"],
            "plan_funding_type": brief.get("plan_funding_type", "self_funded"),
        }
        final_critics = _final_panel(
            patient_profile=patient_profile,
            diagnosis=stylized["diagnosis"],
            treatment_requested=stylized["treatment_requested"],
            insurer=cell["insurer"],
            denial_type=cell["denial_type"],
            denial_letter_text=stylized["denial_letter_text"],
            clinical_context=stylized["clinical_context"],
        )

        all_critics: dict[str, dict[str, Any]] = {
            **planner_critics,
            **drafter_critics,
            **writer_critics,
            **div_critics,
            "safety_redactor": safety_v,
            "phi_pii": phi_v,
            **final_critics,
        }
        ok, failures = _verdicts_summary(all_critics)
        if not ok:
            logger.warning(
                "case %d retry %d failed verdicts: %s",
                index,
                retry,
                "; ".join(failures),
            )
            continue

        case_id = _case_id_for(cell["insurer"], cell["denial_type"], index)
        provenance = {
            "generator_model": config.DEFAULT_MODEL,
            "run_id": run_id,
            "generated_at": _now_iso(),
            "matrix_cell": cell,
            "prompt_versions": PROMPT_VERSIONS,
            "banned_topic_filter_version": config.banned_filter_version(),
            "schema_version": config.schema_version(),
            "diversity_matrix_version": config.matrix_version(),
            "critic_verdicts": all_critics,
            "human_summary": (
                f"Synthetic case for {cell['insurer']} {cell['denial_type']} / "
                f"{cell['specialty']} / sub_tactic={cell['sub_tactic']}. "
                "Generated by Aegis case_generator swarm with per-stage AlphaEval critics."
            ),
            "appeal_difficulty": {
                "score": final_critics["appeal_difficulty"].get("score", 3),
                "reasoning": final_critics["appeal_difficulty"].get("reasoning", ""),
                "exploitable_weaknesses": final_critics["appeal_difficulty"].get("exploitable_weaknesses", []),
                "strong_defenses": final_critics["appeal_difficulty"].get("strong_defenses", []),
            },
        }
        case_obj = {
            "case_id": case_id,
            "insurer": cell["insurer"],
            "denial_type": cell["denial_type"],
            "patient_profile": patient_profile,
            "denial_pattern_sources": stylized.get("denial_pattern_sources", []),
            "denial_letter_text": stylized["denial_letter_text"],
            "clinical_context": stylized["clinical_context"],
            "submission_timestamp": stylized.get("submission_timestamp"),
            "denial_timestamp": stylized.get("denial_timestamp"),
            "synthetic_provenance": provenance,
        }
        result = validate_case(case_obj)
        if not result.ok:
            logger.warning("schema validation failed: %s", result.errors)
            continue

        accepted_cells.add(
            (
                cell["insurer"],
                cell["denial_type"],
                cell["specialty"],
                cell["sub_tactic"],
            )
        )
        neighbour_summaries.append(
            _summary_for_neighbours({**cell, **perturbed, **{"matrix_cell": cell}})
        )
        return case_obj

    logger.error("case %d exhausted retries — skipping", index)
    return None


def new_run_id() -> str:
    return f"gen-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:5]}"
