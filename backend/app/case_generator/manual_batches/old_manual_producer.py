"""LEGACY manual swarm (P1–P5) — old Dear Member denial letters.

Do not use for new cases. Default: ``app.case_generator.aplus.build_aplus_case``.
"""

from __future__ import annotations

from typing import Any

from app.case_generator import config
from app.case_generator.manual_assemble import assemble_case

from .clinical_templates import build_scenario_brief
from .critic_helpers import (
    drafter_critics,
    final_panel_critics,
    planner_critics,
    writer_critics,
)


def _policy_name(insurer: str) -> str:
    return {
        "Aetna": "Aetna Clinical Policy Bulletins (CPBs) and InterQual criteria",
        "Cigna": "Cigna Medical Coverage Policies and MCG Care Guidelines",
        "UHC": "UnitedHealthcare Medical Policies and Optum clinical criteria",
    }[insurer]


def _signoff(insurer: str) -> str:
    return {
        "Aetna": "Aetna Medical Management",
        "Cigna": "Cigna Health Care Management",
        "UHC": "UnitedHealthcare Utilization Management",
    }[insurer]


def _dates_for_case(index: int) -> tuple[str, str]:
  # Stable synthetic dates per index
    base_year = 2025 + (index % 2)
    month = 1 + (index % 11)
    day = 5 + (index % 20)
    sub = f"{base_year}-{month:02d}-{day:02d}"
    den = f"{base_year}-{month:02d}-{day + 14:02d}"
    return (
        f"{sub}T14:22:00Z",
        f"{den}T09:15:00Z",
    )


def run_p2_denial_drafter(brief: dict[str, Any], cell: dict[str, str]) -> str:
    """P2 — insurer-voice denial letter."""
    insurer = cell["insurer"]
    policy = _policy_name(insurer)
    sub_def = config.sub_tactic_definition(cell["denial_type"], cell["sub_tactic"])
    appeal_days = 180
    employer_note = ""
    if brief.get("employer_archetype"):
        employer_note = (
            f"\n\nThis determination applies to your employer-sponsored commercial "
            f"benefit while {brief['employer_archetype']}."
        )

    letter = f"""Dear Member,

We have completed our review of the request for {brief['treatment_requested']} related to {brief['diagnosis']}.

After clinical review using {policy}, we are unable to approve coverage at this time.{employer_note}

Determination summary: {brief['denial_rationale_seed']} Our records were reviewed against the applicable utilization-management criteria for {cell['denial_type'].lower()} determinations. Specifically, this review evaluated whether the requested service meets the plan's definition of medical necessity and whether required administrative steps were completed. {sub_def}

Clinical review notes indicate the documentation submitted does not satisfy the criteria required to authorize {brief['treatment_requested']}. If you believe additional information was not considered, you may request a peer-to-peer discussion with a medical director; however, any such discussion must occur within the timeframe stated in your plan materials.

You have the right to appeal this determination. To file a standard appeal, submit a written request with supporting medical records within {appeal_days} days of the date of this letter. Include your member identification, provider information, and any letters of medical necessity.

Sincerely,

{_signoff(insurer)}"""
    return letter


def run_p3_clinical_writer(brief: dict[str, Any], letter: str, cell: dict[str, str]) -> str:
    """P3 — rebuttal-oriented clinical context."""
    age = brief["patient_age"]
    gender = brief["patient_gender"]
    pronoun = "She" if gender == "F" else "He" if gender == "M" else "They"
    employer = ""
    if brief.get("employer_archetype"):
        employer = f" The member is {brief['employer_archetype']}."

    ctx = f"""The {age}-year-old member carries a documented diagnosis of {brief['diagnosis']}.{employer} {pronoun} has been under continuous care with treating specialists who recommended {brief['treatment_requested']} as the next appropriate step.

{brief['rebuttal_seed']} Treating clinicians submitted office notes, medication trials with dates and doses, and objective findings supporting medical necessity. The insurer's letter instead relies on {cell['sub_tactic'].replace('_', ' ')} without engaging the specific evidence already on file.

Contrary to the denial narrative, the chart shows prior therapies were attempted for adequate duration and failed or were contraindicated. The appeal should emphasize documented step-therapy exceptions where applicable, correct application of specialty-appropriate guidelines, and any procedural defects in the notice (for example vague policy edition citations or incomplete appeal rights). The member remains symptomatic and faces delay-related harm if the requested service is further postponed."""
    return ctx


def run_p4_flaw_injector(
    assembled: dict[str, Any],
    brief: dict[str, Any],
    patterns: list[dict[str, Any]],
) -> dict[str, Any]:
    """P4 — inject realistic insurer imperfections."""
    letter = assembled["denial_letter_text"]
    flaw_note = ""
    sources: list[str] = []
    for p in patterns[:2]:
        sources.append(f"{p.get('id', 'pattern')}: {p.get('source', 'published UM research')}")
    if not sources:
        sources.append("KFF 2023 Survey of Consumer Experiences with Health Insurance")

    flaws = brief.get("intended_flaw_types", [])
    if any("vague" in f.lower() or "guideline" in f.lower() for f in flaws):
        letter = letter.replace(
            "utilization-management criteria",
            "utilization-management criteria (MCG guidelines, current edition not specified)",
        )
        flaw_note += "Inserted vague guideline citation. "
    if any("iro" in f.lower() or "external review" in f.lower() for f in flaws):
        letter = letter.replace(
            "You have the right to appeal this determination.",
            "You have the right to appeal this determination through our internal appeals process.",
        )
        flaw_note += "Omitted explicit independent external review (IRO) rights. "
    if any("ignored" in f.lower() or "boilerplate" in f.lower() for f in flaws):
        letter += (
            "\n\nPlease note that standard criteria apply regardless of prior submissions."
        )
        flaw_note += "Added boilerplate ignoring prior evidence. "

    sub_ts, den_ts = _dates_for_case(assembled.get("_index", 0))
    return {
        "denial_letter_text": letter,
        "clinical_context": assembled["clinical_context"],
        "diagnosis": assembled["diagnosis"],
        "treatment_requested": assembled["treatment_requested"],
        "submission_timestamp": sub_ts,
        "denial_timestamp": den_ts,
        "denial_pattern_sources": sources,
        "perturbation_notes": flaw_note or "Applied procedural vagueness and disclosure gaps.",
        "_index": assembled.get("_index"),
    }


def run_p5_stylistic_diversifier(stylized_in: dict[str, Any], index: int) -> dict[str, Any]:
    """P5 — light stylistic variation without changing clinical facts."""
    letter = stylized_in["denial_letter_text"]
    if index % 3 == 0:
        letter = letter.replace("Dear Member,", "Dear Plan Member,")
    elif index % 3 == 1:
        letter = letter.replace(
            "We have completed our review",
            "This letter confirms the outcome of our review",
        )
    return {**stylized_in, "denial_letter_text": letter}


def run_manual_pipeline(
    *,
    index: int,
    cell: dict[str, str],
    patterns: list[dict[str, Any]],
    run_id: str,
    neighbour_summaries: list[str],
) -> dict[str, Any]:
    """Full swarm for one case index."""
    # P1
    brief = build_scenario_brief(cell, index)
    brief["matrix_cell"] = dict(cell)
    planner_c = planner_critics(
        insurer=cell["insurer"],
        specialty=cell["specialty"],
        sub_tactic=cell["sub_tactic"],
        diagnosis=brief["diagnosis"],
        treatment=brief["treatment_requested"],
    )

    # P2
    letter = run_p2_denial_drafter(brief, cell)
    drafter_c = drafter_critics(
        insurer=cell["insurer"],
        sub_tactic=cell["sub_tactic"],
        letter_excerpt=letter[:200],
    )

    # P3
    ctx = run_p3_clinical_writer(brief, letter, cell)
    writer_c = writer_critics(
        diagnosis=brief["diagnosis"],
        treatment=brief["treatment_requested"],
        ctx_excerpt=ctx[:200],
    )

    assembled = {
        "matrix_cell": cell,
        "diagnosis": brief["diagnosis"],
        "treatment_requested": brief["treatment_requested"],
        "denial_letter_text": letter,
        "clinical_context": ctx,
        "_index": index,
    }

    # P4
    perturbed = run_p4_flaw_injector(assembled, brief, patterns)

    # P5
    stylized = run_p5_stylistic_diversifier(perturbed, index)

    weaknesses = list(brief.get("intended_flaw_types", []))[:3]
    defenses = [
        "Insurer cites formal policy language and standard appeal window.",
        f"Denial aligns with declared sub_tactic: {cell['sub_tactic']}.",
    ]
    appeal_score = int(brief.get("intended_appeal_difficulty", 3))
    final_c = final_panel_critics(
        insurer=cell["insurer"],
        denial_type=cell["denial_type"],
        letter_excerpt=stylized["denial_letter_text"][:200],
        appeal_score=appeal_score,
        weaknesses=weaknesses,
        defenses=defenses,
    )

    all_critics = {**planner_c, **drafter_c, **writer_c, **final_c}

    patient_profile = {
        "age": brief["patient_age"],
        "gender": brief["patient_gender"],
        "diagnosis": stylized["diagnosis"],
        "treatment_requested": stylized["treatment_requested"],
        "plan_funding_type": brief["plan_funding_type"],
    }

    return assemble_case(
        index=index,
        matrix_cell=cell,
        patient_profile=patient_profile,
        denial_letter_text=stylized["denial_letter_text"],
        clinical_context=stylized["clinical_context"],
        denial_pattern_sources=stylized["denial_pattern_sources"],
        critic_verdicts=all_critics,
        run_id=run_id,
        submission_timestamp=stylized.get("submission_timestamp"),
        denial_timestamp=stylized.get("denial_timestamp"),
    )


def neighbour_summary(case: dict[str, Any]) -> str:
    mc = case["synthetic_provenance"]["matrix_cell"]
    return (
        f"- [{mc['insurer']} / {mc['denial_type']} / {mc['specialty']} / "
        f"{mc['sub_tactic']}] dx={case['patient_profile']['diagnosis']}; "
        f"tx={case['patient_profile']['treatment_requested']}"
    )
