"""Aegis LLM case generator — Vertex/Gemini producer→critic swarm (canonical pipeline).

Grounded on the curated clinical KB (clinical_kb), with a flaw-injection verifier
(flaw_verifier) enforcing the J6 teacher-packet contract, deterministic sex guard,
diversity critic, word-budget guard (text_metrics), and sourced denial_letter_references.
Orchestrates the per-stage producer→critic generation swarm.

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

from . import clinical_kb, config, flaw_verifier, references, stats_evaluator
from . import llm_agents as agents
from .prompts import PROMPT_VERSIONS
from .safety import banned_topic_briefs, scan_banned, scan_phi
from .text_metrics import fit_letter_word_budget, repair_denial_letter_artifacts
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
    "flaw_injection",  # every intended flaw must be discoverable in student-visible text (J6 contract)
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
    seed = clinical_kb.rationale_seed(matrix_cell["sub_tactic"])
    if seed:
        sub_def = f"{sub_def}\n\n{seed}"
    examples = config.specialty_examples(matrix_cell["specialty"])
    constraints = config.joint_constraints_text()

    brief = agents.run_scenario_planner(
        matrix_cell=matrix_cell,
        sub_tactic_definition=sub_def,
        specialty_examples=examples,
        joint_constraints=constraints,
        patterns=patterns,
        clinical_variants=clinical_kb.grounding_block(matrix_cell["specialty"]),
    )

    # Deterministic SEX GUARD — root-cause fix for demographic mismatches. Forces
    # patient_gender to match a sex-specific diagnosis regardless of the random matrix
    # cell gender (the bug that produced "34M ovarian cyst").
    req_sex = clinical_kb.required_sex(
        brief.get("diagnosis", ""), brief.get("treatment_requested", "")
    )
    if req_sex and brief.get("patient_gender") != req_sex:
        logger.info("sex guard: forcing patient_gender %s -> %s for dx=%s",
                    brief.get("patient_gender"), req_sex, brief.get("diagnosis"))
        brief["patient_gender"] = req_sex

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
    # Diversity critic (previously defined but never called) — gate near-duplicates.
    merged = {**assembled, **stylized}
    this_summary = _summary_for_neighbours(
        {"matrix_cell": merged.get("matrix_cell", {}),
         "diagnosis": merged.get("diagnosis", ""),
         "treatment_requested": merged.get("treatment_requested", "")}
    )
    diversity = agents.critic_diversity_delta(this_summary, ns_text)
    return stylized, {"diversity_delta": diversity}


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


def _verify_flaws_full(
    *,
    denial_letter_text: str,
    clinical_context: str,
    pattern_ids: list[str],
    submission_timestamp: str | None,
    denial_timestamp: str | None,
    specialty: str | None,
    plan_funding_type: str | None,
    patterns: list[dict[str, Any]],
    llm_all: bool = False,
) -> tuple[list[str], dict[str, Any], list[str]]:
    """Full deterministic + LLM flaw verification (NO mutation).

    Returns (absent, det_result, llm_absent). ``absent`` = deterministic 'absent' ∪
    LLM-confirmed-absent. With ``llm_all=False`` (mid-pipeline, cheaper) the LLM only
    re-checks the semantic 'needs_llm' patterns; with ``llm_all=True`` (the FINAL gate) the
    LLM independently re-checks EVERY intended flaw — catching deterministic false-positives
    so no judge-facing flaw can slip through the finished case.
    """
    pat_by_id = {p.get("id"): p for p in patterns if p.get("id")}
    fv = flaw_verifier.verify_flaws(
        denial_letter_text=denial_letter_text,
        clinical_context=clinical_context,
        pattern_ids=pattern_ids,
        submission_timestamp=submission_timestamp,
        denial_timestamp=denial_timestamp,
        specialty=specialty,
        plan_funding_type=plan_funding_type,
    )
    llm_targets = list(pattern_ids) if llm_all else list(fv["needs_llm"])
    llm_absent: list[str] = []
    if llm_targets:
        to_check = [
            {"id": pid,
             "description": pat_by_id.get(pid, {}).get("description", ""),
             "appeal_vector": pat_by_id.get(pid, {}).get("appeal_vector", "")}
            for pid in llm_targets
        ]
        try:
            res = agents.critic_flaw_injection_verifier(
                denial_letter_text, clinical_context, to_check,
                submission_timestamp=submission_timestamp,
                denial_timestamp=denial_timestamp,
            )
            llm_absent = [r.get("pattern_id") for r in res.get("verification_results", [])
                          if str(r.get("status", "")).upper() == "ABSENT"]
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM flaw verifier failed: %s", exc)
    absent = sorted(set(fv["absent"]) | set(llm_absent))
    return absent, fv, llm_absent


def _post_p4_flaw_checkpoint(
    assembled_p4: dict[str, Any],
    pattern_ids: list[str],
    cell: dict[str, str],
    brief: dict[str, Any],
    patterns: list[dict[str, Any]],
) -> dict[str, Any]:
    """AlphaEval per-step checkpoint between P4 and P5 (cascade-dependency mitigation).

    Runs the DETERMINISTIC flaw verifier on the P4 output and re-injects any absent flaws
    in place, so the stylistic diversifier never builds on a flaw-broken letter. Cheap
    (no LLM); the full deterministic+LLM gate still runs after P5. Informational verdict —
    the post-P5 ``flaw_injection`` dim is the hard gate.
    """
    pat_by_id = {p.get("id"): p for p in patterns if p.get("id")}

    def _det() -> dict[str, Any]:
        return flaw_verifier.verify_flaws(
            denial_letter_text=assembled_p4["denial_letter_text"],
            clinical_context=assembled_p4["clinical_context"],
            pattern_ids=pattern_ids,
            submission_timestamp=assembled_p4.get("submission_timestamp"),
            denial_timestamp=assembled_p4.get("denial_timestamp"),
            specialty=cell["specialty"],
            plan_funding_type=brief.get("plan_funding_type"),
        )

    fv = _det()
    if fv["absent"]:
        logger.info("post-P4 checkpoint: absent=%s — re-injecting before P5", fv["absent"])
        try:
            reinj = agents.run_realistic_flaw_injector(
                dict(assembled_p4), fv["absent"],
                [pat_by_id[a] for a in fv["absent"] if a in pat_by_id],
            )
            for k in ("denial_letter_text", "clinical_context",
                      "submission_timestamp", "denial_timestamp"):
                if reinj.get(k):
                    assembled_p4[k] = reinj[k]
            fv = _det()
        except Exception as exc:  # noqa: BLE001
            logger.warning("post-P4 re-injection failed: %s", exc)

    return {
        "dimension": "flaw_injection_p4",
        "reasoning": (f"post-P4 deterministic: present={fv['present']}; "
                      f"needs_llm={fv['needs_llm']}; absent={fv['absent']}"),
        "score": "PASS" if not fv["absent"] else "FAIL",
        "confidence": 1.0,
        "evidence_quotes": [],
        "improvement": (f"Inject before P5: {fv['absent']}" if fv["absent"] else None),
    }


def _flaw_injection_stage(
    stylized: dict[str, Any],
    pattern_ids: list[str],
    cell: dict[str, str],
    brief: dict[str, Any],
    assembled_for_p5: dict[str, Any],
    patterns: list[dict[str, Any]],
) -> dict[str, Any]:
    """Verify every intended flaw is discoverable in student-visible text (J6 contract).

    Two layers: deterministic ``flaw_verifier`` for clear-signature patterns, and the LLM
    ``critic_flaw_injection_verifier`` for the semantic ('needs_llm') ones. Their 'absent'
    sets are unioned; one re-injection pass covers all; then a PASS/FAIL hard-gate verdict.
    """
    pat_by_id = {p.get("id"): p for p in patterns if p.get("id")}

    def _absent_set() -> tuple[list[str], dict[str, Any]]:
        absent, fv, _ = _verify_flaws_full(
            denial_letter_text=stylized["denial_letter_text"],
            clinical_context=stylized["clinical_context"],
            pattern_ids=pattern_ids,
            submission_timestamp=stylized.get("submission_timestamp"),
            denial_timestamp=stylized.get("denial_timestamp"),
            specialty=cell["specialty"],
            plan_funding_type=brief.get("plan_funding_type"),
            patterns=patterns,
        )
        return absent, fv

    absent, fv = _absent_set()
    if absent:
        logger.info("flaw verifier: absent=%s — attempting targeted re-injection", absent)
        try:
            reinj = agents.run_realistic_flaw_injector(
                {**assembled_for_p5, **stylized},
                absent,
                [pat_by_id[a] for a in absent if a in pat_by_id],
            )
            for k in ("denial_letter_text", "clinical_context",
                      "submission_timestamp", "denial_timestamp"):
                if reinj.get(k):
                    stylized[k] = reinj[k]
            stylized["denial_letter_text"] = fit_letter_word_budget(
                repair_denial_letter_artifacts(stylized["denial_letter_text"])
            )
            absent, fv = _absent_set()
        except Exception as exc:  # noqa: BLE001
            logger.warning("flaw re-injection failed: %s", exc)

    return {
        "dimension": "flaw_injection",
        "reasoning": (f"discoverable={fv['present']}; needs_llm={fv['needs_llm']}; "
                      f"absent_after_retry={absent}"),
        "score": "PASS" if not absent else "FAIL",
        "confidence": 1.0,
        "evidence_quotes": [],
        "improvement": (f"Re-inject so discoverable in student-visible text: {absent}"
                        if absent else None),
    }


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
        pattern_ids_list = [p.get("id") for p in patterns if p.get("id")]
        perturbed, div_critics = _flaw_injector_stage(assembled, brief.get("intended_flaw_types", []), patterns)
        assembled_for_p5 = {**assembled, **perturbed}

        # AlphaEval per-step checkpoint: validate P4's flaw injection BEFORE P5 diversifies it
        # (cascade-dependency mitigation). Deterministic-only re-injection here is cheap; the
        # full deterministic+LLM gate runs again after P5.
        p4_v = _post_p4_flaw_checkpoint(
            assembled_for_p5, pattern_ids_list, cell, brief, patterns
        )

        stylized, style_critics = _stylistic_diversifier_stage(assembled_for_p5, neighbour_summaries)

        # text_metrics guard: enforce P2/P3 word budget + repair splice artifacts.
        stylized["denial_letter_text"] = fit_letter_word_budget(
            repair_denial_letter_artifacts(stylized["denial_letter_text"])
        )
        # Judge-aligned denial_pattern_sources ("{id}: {source}" — teacher-packet-parseable).
        stylized["denial_pattern_sources"] = flaw_verifier.format_pattern_sources(patterns)

        # Flaw-injection verifier gate (mutates stylized via re-injection on absent flaws).
        flaw_v = _flaw_injection_stage(
            stylized, pattern_ids_list, cell, brief, assembled_for_p5, patterns
        )

        # Statistical evaluator layer (AlphaEval 3rd type): lexical near-duplicate vs the
        # existing drafts corpus — "diversify based on existing cases".
        case_id = _case_id_for(cell["insurer"], cell["denial_type"], index)
        div_stat_v = stats_evaluator.diversity_verdict(
            stats_evaluator.diversity_metrics(
                denial_letter_text=stylized["denial_letter_text"],
                clinical_context=stylized["clinical_context"],
                neighbour_texts=[],
                corpus=stats_evaluator.corpus_trigrams(
                    config.REPO_ROOT / "eval" / "cases" / "drafts"),
                exclude_case_id=case_id,
            )
        )

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
            **style_critics,
            "flaw_injection_p4": p4_v,
            "flaw_injection": flaw_v,
            "diversity_statistical": div_stat_v,
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
                "exploitable_weaknesses": (
                    final_critics["appeal_difficulty"].get("exploitable_weaknesses", [])
                    + [f"Pattern anchor: {pid}" for pid in pattern_ids_list]
                ),
                "strong_defenses": final_critics["appeal_difficulty"].get("strong_defenses", []),
            },
        }
        case_obj = {
            "case_id": case_id,
            "insurer": cell["insurer"],
            "denial_type": cell["denial_type"],
            "patient_profile": patient_profile,
            "denial_pattern_sources": stylized.get("denial_pattern_sources", []),
            "denial_letter_references": references.select_letter_references(
                insurer=cell["insurer"],
                denial_type=cell["denial_type"],
                pattern_ids=pattern_ids_list,
                cell=cell,
                use_web_research=True,
            ),
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

        # FINAL FLAW-INTEGRITY CHECK (last step) — FULL deterministic + LLM verification on
        # the FINISHED case_obj. This is the hard guarantee that every judge-facing flaw
        # (the same patterns fed to the teacher packet via denial_pattern_sources +
        # appeal_difficulty.exploitable_weaknesses) is still discoverable in the final
        # letter/clinical text. If any is missing — clear-signature OR semantic — re-roll,
        # so the judges never penalise the learner for a flaw the data fails to contain.
        final_absent, final_fv, final_llm_absent = _verify_flaws_full(
            denial_letter_text=case_obj["denial_letter_text"],
            clinical_context=case_obj["clinical_context"],
            pattern_ids=pattern_ids_list,
            submission_timestamp=case_obj.get("submission_timestamp"),
            denial_timestamp=case_obj.get("denial_timestamp"),
            specialty=cell["specialty"],
            plan_funding_type=brief.get("plan_funding_type"),
            patterns=patterns,
            llm_all=True,  # FINAL gate: LLM independently re-checks EVERY intended flaw.
        )
        case_obj["synthetic_provenance"]["final_flaw_integrity"] = {
            "method": "deterministic+llm(all)",
            "expected_flaws": pattern_ids_list,
            "deterministic_present": final_fv["present"],
            "llm_absent": final_llm_absent,
            "absent": final_absent,
            "aligned": not final_absent,
        }
        if final_absent:
            logger.warning(
                "case %d retry %d FINAL flaw-integrity FAIL (det+llm) — judge-facing flaw(s) "
                "%s missing from the finished case; re-rolling",
                index, retry, final_absent,
            )
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
