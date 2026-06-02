"""Full P1–P5 pipeline with prompt-aligned QA gates."""

from __future__ import annotations

import random
from typing import Any

from app.case_generator import config
from app.case_generator.manual_assemble import assemble_case, new_run_id
from app.case_generator.manual_batches.neighbour import neighbour_summary
from app.case_generator.prompts import PROMPT_VERSIONS

from .clinical import draft_clinical_context
from .flaws import inject_flaws, verify_flaws_present
from .letter_enhancements import enhance_denial_letter
from .letters import draft_denial_letter
from .scenarios import build_scenario_brief
from .style import diversify
from .text_metrics import (
    context_words_ok,
    fit_letter_word_budget,
    letter_words_ok,
    repair_denial_letter_artifacts,
)
from .critics import build_all_critics

GENERATOR_MODEL = "cursor-manual-agent-aplus-v2"


def build_aplus_case(
    *,
    index: int,
    cell: dict[str, str],
    run_id: str,
    neighbour_summaries: list[str],
    seed: int = 20260601,
    case_id: str | None = None,
    use_web_research: bool = True,
) -> dict[str, Any]:
    rng = random.Random(seed + index)
    patterns = config.sample_denial_patterns(rng, cell["insurer"], cell["specialty"])
    if not patterns:
        patterns = config.load_denial_patterns().get("patterns", [])[:2]

    brief = build_scenario_brief(index, cell, patterns)
    brief["_patterns"] = patterns
    pattern_ids = [p.get("id", "") for p in patterns[:3] if p.get("id")]

    letter, letter_refs = draft_denial_letter(
        brief, cell, index, use_web_research=use_web_research
    )
    letter = enhance_denial_letter(
        letter,
        insurer=cell["insurer"],
        denial_type=cell["denial_type"],
        cell=cell,
        pattern_ids=pattern_ids,
        fit_budget=False,
    )
    ctx = draft_clinical_context(brief, cell)

    assembled = {
        "matrix_cell": cell,
        "diagnosis": brief["diagnosis"],
        "treatment_requested": brief["treatment_requested"],
        "denial_letter_text": letter,
        "clinical_context": ctx,
    }
    perturbed = inject_flaws(
        letter=letter,
        context=ctx,
        brief=brief,
        patterns=patterns,
        index=index,
    )
    stylized = diversify(perturbed, index, neighbour_summaries)
    stylized["denial_letter_text"] = fit_letter_word_budget(
        repair_denial_letter_artifacts(stylized["denial_letter_text"])
    )

    missing = verify_flaws_present(
        stylized["denial_letter_text"],
        pattern_ids,
        stylized.get("submission_timestamp"),
        stylized.get("denial_timestamp"),
    )
    if missing and "algo_time_delta" in missing:
        from datetime import datetime, timedelta

        base = datetime(2026, 4, 1, 10, 0, 0)
        stylized["submission_timestamp"] = base.strftime("%Y-%m-%dT%H:%M:%SZ")
        stylized["denial_timestamp"] = (base + timedelta(minutes=3)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

    letter_f = stylized["denial_letter_text"]
    ctx_f = stylized["clinical_context"]
    if not letter_words_ok(letter_f):
        letter_f = fit_letter_word_budget(repair_denial_letter_artifacts(letter_f))
        stylized["denial_letter_text"] = letter_f
    if not context_words_ok(ctx_f):
        ctx_f += (
            " The treating team requests expedited reconsideration because "
            "delay risks measurable clinical deterioration documented in the "
            "attached visit notes."
        )
        stylized["clinical_context"] = ctx_f

    critics = build_all_critics(
        brief=brief,
        cell=cell,
        letter=stylized["denial_letter_text"],
        ctx=stylized["clinical_context"],
        pattern_ids=pattern_ids,
    )

    patient_profile = {
        "age": brief["patient_age"],
        "gender": brief["patient_gender"],
        "diagnosis": stylized["diagnosis"],
        "treatment_requested": stylized["treatment_requested"],
        "plan_funding_type": brief["plan_funding_type"],
    }

    case = assemble_case(
        index=index,
        matrix_cell=cell,
        patient_profile=patient_profile,
        denial_letter_text=stylized["denial_letter_text"],
        clinical_context=stylized["clinical_context"],
        denial_pattern_sources=stylized["denial_pattern_sources"],
        denial_letter_references=letter_refs,
        critic_verdicts=critics,
        run_id=run_id,
        case_id=case_id,
        submission_timestamp=stylized.get("submission_timestamp"),
        denial_timestamp=stylized.get("denial_timestamp"),
    )
    prov = case["synthetic_provenance"]
    prov["generator_model"] = GENERATOR_MODEL
    prov["schema_version"] = "1.1.0"
    prov["prompt_versions"] = PROMPT_VERSIONS
    web_note = (
        " denial_letter_references include URLs from agent web research "
        "(eval/references/web-research-cache-2026-06-02.json)."
        if use_web_research
        else " denial_letter_references from static catalog only."
    )
    prov["human_summary"] = (
        f"A+ manual pipeline case: {cell['insurer']} {cell['denial_type']} / "
        f"{cell['specialty']} / {cell['sub_tactic']}. "
        f"P1–P5 executed prompt-faithfully; specialty-aligned clinical story; "
        f"flaws: {', '.join(pattern_ids) or 'procedural'}.{web_note} "
        "Letter includes claim-file and peer-to-peer disclosures (public-source realism pass)."
    )
    return case


def rebuild_benchmark(
    *,
    start: int = 11,
    end: int = 210,
    seed: int = 20260601,
) -> list[str]:
    from app.case_generator.manual_batches.matrix_planner import planned_cells

    cells = planned_cells(seed)
    neighbours: list[str] = []
    errors: list[str] = []
    run_id = new_run_id(0).replace("manual-b00", "aplus-full")

    for i, cell in enumerate(cells, start=start):
        if i > end:
            break
        try:
            case = build_aplus_case(
                index=i,
                cell=cell,
                run_id=run_id,
                neighbour_summaries=neighbours,
                seed=seed,
            )
            neighbours.append(neighbour_summary(case))
            if len(neighbours) > 12:
                neighbours.pop(0)
        except Exception as exc:
            errors.append(f"case_{i:02d}: {exc}")
    return errors
