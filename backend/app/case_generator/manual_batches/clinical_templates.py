"""Clinical scenario templates per sub_tactic — manual P1 seeds (no LLM)."""

from __future__ import annotations

from typing import Any, Callable

TemplateFn = Callable[[dict[str, str], int], dict[str, Any]]


def _age_in_band(band: str, index: int) -> int:
    spans = {
        "18-25": (19, 25),
        "26-40": (27, 40),
        "41-55": (42, 55),
        "56-70": (57, 69),
        "71+": (72, 78),
    }
    lo, hi = spans.get(band, (30, 50))
    return lo + (index % (hi - lo + 1))


def _base(
    cell: dict[str, str],
    index: int,
    *,
    diagnosis: str,
    treatment: str,
    denial_seed: str,
    rebuttal_seed: str,
    flaw_types: list[str],
    difficulty: int = 3,
    plan: str = "self_funded",
) -> dict[str, Any]:
    age = _age_in_band(cell["patient_age_band"], index)
    employer = None
    if cell["patient_age_band"] == "71+":
        employer = "still actively employed as a senior consultant on an employer-sponsored PPO"
        plan = "fully_insured"
    return {
        "matrix_cell": dict(cell),
        "diagnosis": diagnosis,
        "treatment_requested": treatment,
        "denial_rationale_seed": denial_seed,
        "rebuttal_seed": rebuttal_seed,
        "patient_age": age,
        "patient_gender": cell["patient_gender"],
        "plan_funding_type": plan,
        "employer_archetype": employer,
        "intended_appeal_difficulty": difficulty,
        "intended_flaw_types": flaw_types,
        "intended_flaw_categories": ["procedural_disclosure", "clinical_reasoning"],
    }


def _step_therapy(cell: dict[str, str], index: int) -> dict[str, Any]:
    pool = [
        (
            "Paroxysmal atrial fibrillation (I48.0)",
            "Catheter ablation for symptomatic AFib",
            "Insurer requires failure of two class III antiarrhythmics before ablation.",
            "Patient failed dofetilide and sotalol with documented rhythm logs.",
        ),
        (
            "Moderate plaque psoriasis (L40.0)",
            "Adalimumab (Humira) for psoriasis",
            "Step therapy demands methotrexate trial before biologic.",
            "Methotrexate stopped for hepatotoxicity; documentation submitted.",
        ),
        (
            "Rheumatoid arthritis, seropositive (M06.9)",
            "Upadacitinib (Rinvoq) after methotrexate",
            "Requires trial of two DMARDs including methotrexate.",
            "Methotrexate and sulfasalazine failed with DAS28 > 5.1.",
        ),
    ]
    dx, tx, d, r = pool[index % len(pool)]
    return _base(
        cell,
        index,
        diagnosis=dx,
        treatment=tx,
        denial_seed=d,
        rebuttal_seed=r,
        flaw_types=["vague guideline citation", "ignored prior treatment failure"],
    )


def _conservative(cell: dict[str, str], index: int) -> dict[str, Any]:
    pool = [
        (
            "Lumbar radiculopathy with neurogenic claudication (M54.16)",
            "L4-L5 microdiscectomy",
            "Insurer requires 6 months of structured physical therapy first.",
            "Completed 18 PT sessions over 14 weeks with persistent leg pain.",
        ),
        (
            "Rotator cuff tear, partial (M75.101)",
            "Arthroscopic rotator cuff repair",
            "Requires 3 months conservative care including PT.",
            "Sixteen PT visits plus NSAIDs; MRI shows full-thickness tear.",
        ),
    ]
    dx, tx, d, r = pool[index % len(pool)]
    return _base(cell, index, diagnosis=dx, treatment=tx, denial_seed=d, rebuttal_seed=r, flaw_types=["boilerplate ignores prior auth context"])


def _frequency(cell: dict[str, str], index: int) -> dict[str, Any]:
    return _base(
        cell,
        index,
        diagnosis="Generalized anxiety disorder (F41.1)",
        treatment="Weekly psychotherapy beyond 20 visits per plan year",
        denial_seed="Annual behavioral health visit cap of 20 has been reached.",
        rebuttal_seed="MHPAEA parity: medical specialty visits are not capped at 20.",
        flaw_types=["caps behavioral health while medical benefit uncapped"],
        plan="fully_insured",
    )


def _level_of_care(cell: dict[str, str], index: int) -> dict[str, Any]:
    return _base(
        cell,
        index,
        diagnosis="Severe alcohol use disorder (F10.20)",
        treatment="Intensive outpatient program (IOP) for AUD",
        denial_seed="Outpatient counseling is sufficient; IOP level not medically necessary.",
        rebuttal_seed="ASAM criteria met for IOP; outpatient alone failed twice.",
        flaw_types=["uses proprietary criteria more restrictive than ASAM"],
    )


def _not_evidence(cell: dict[str, str], index: int) -> dict[str, Any]:
    pool = [
        (
            "Type 2 diabetes mellitus with labile glucose (E11.65)",
            "Continuous glucose monitor (Dexcom G7)",
            "CGM not evidence-based for Type 2 without intensive insulin per policy.",
            "Patient on basal-bolus with nocturnal hypoglycemia despite fingersticks.",
        ),
        (
            "Chronic migraine without aura (G43.709)",
            "Erenumab (Aimovig) CGRP inhibitor",
            "Lacks RCT evidence for this indication per outdated policy.",
            "Failed topiramate, propranolol, and three triptan trials.",
        ),
    ]
    dx, tx, d, r = pool[index % len(pool)]
    return _base(cell, index, diagnosis=dx, treatment=tx, denial_seed=d, rebuttal_seed=r, flaw_types=["cites outdated InterQual version"])


def _duration(cell: dict[str, str], index: int) -> dict[str, Any]:
    return _base(
        cell,
        index,
        diagnosis="Relapsing-remitting multiple sclerosis (G35)",
        treatment="Ocrelizumab continuation beyond 24-month policy cap",
        denial_seed="Duration exceeds plan maximum without new clinical review.",
        rebuttal_seed="Stable MRI and no relapses; stopping violates standard of care.",
        flaw_types=["no specific clinical thresholds cited"],
    )


def _guideline_mis(cell: dict[str, str], index: int) -> dict[str, Any]:
    return _base(
        cell,
        index,
        diagnosis="HR-positive early breast cancer (C50.911)",
        treatment="Adjuvant abemaciclib with endocrine therapy",
        denial_seed="Insurer cites wrong MCG module for metastatic disease.",
        rebuttal_seed="Patient is stage II; NCCN supports CDK4/6 in high-risk early breast cancer.",
        flaw_types=["references withdrawn MCG module"],
        plan="fully_insured",
    )


def _missing_p2p(cell: dict[str, str], index: int) -> dict[str, Any]:
    return _base(
        cell,
        index,
        diagnosis="Severe OCD, treatment-resistant (F42.2)",
        treatment="Transcranial magnetic stimulation (TMS)",
        denial_seed="Peer-to-peer not completed within 5-business-day window.",
        rebuttal_seed="Scheduling line was down; three documented call attempts.",
        flaw_types=["no mention of IRO process"],
    )


def _formulary(cell: dict[str, str], index: int) -> dict[str, Any]:
    return _base(
        cell,
        index,
        diagnosis="Crohn's disease, moderate (K50.90)",
        treatment="Ustekinumab (Stelara) maintenance",
        denial_seed="Preferred formulary biologic must be tried first.",
        rebuttal_seed="Prior anti-TNF failure documented; step exception requested.",
        flaw_types=["demands step therapy despite documented adverse reaction"],
    )


def _oon(cell: dict[str, str], index: int) -> dict[str, Any]:
    return _base(
        cell,
        index,
        diagnosis="Stage IV endometriosis (N80.4)",
        treatment="Excision of endometriosis with specialist (out-of-network)",
        denial_seed="No gap exception; in-network surgeon available.",
        rebuttal_seed="Only specialist has 200+ excision cases; in-network lacks expertise.",
        flaw_types=["missing financial liability details"],
    )


def _continuation(cell: dict[str, str], index: int) -> dict[str, Any]:
    return _base(
        cell,
        index,
        diagnosis="Psoriatic arthritis (L40.50)",
        treatment="Secukinumab (Cosentyx) refill — continuation of care",
        denial_seed="Prior authorization lapsed; new auth required.",
        rebuttal_seed="Stable 14 months; lapse was insurer portal error.",
        flaw_types=["missing external review right"],
    )


def _emergency_retro(cell: dict[str, str], index: int) -> dict[str, Any]:
    return _base(
        cell,
        index,
        diagnosis="Cervical strain after fall; rule out cord injury (S13.4XXA)",
        treatment="MRI cervical spine without contrast (emergency department)",
        denial_seed="No prior authorization; non-emergent imaging.",
        rebuttal_seed="ED presentation with neuro deficit; prudent layperson standard.",
        flaw_types=["denial dated after regulatory window"],
        plan="fully_insured",
    )


def _modality(cell: dict[str, str], index: int) -> dict[str, Any]:
    pool = [
        (
            "Obstructive sleep apnea, moderate (G47.33)",
            "In-lab polysomnography",
            "Home sleep apnea test required first-line.",
            "BMI 38, CHF, and suspected central apneas.",
        ),
        (
            "Pelvic floor dysfunction postpartum (N81.9)",
            "Pelvic floor physical therapy (12 visits)",
            "Home exercise booklet is sufficient.",
            "Prior vaginal delivery with levator tear on ultrasound.",
        ),
    ]
    dx, tx, d, r = pool[index % len(pool)]
    return _base(cell, index, diagnosis=dx, treatment=tx, denial_seed=d, rebuttal_seed=r, flaw_types=["modality substitution without safety rationale"])


def _visit_limit(cell: dict[str, str], index: int) -> dict[str, Any]:
    return _base(
        cell,
        index,
        diagnosis="Major depressive disorder, recurrent (F33.1)",
        treatment="Additional outpatient psychotherapy visits",
        denial_seed="Annual 20-visit behavioral health cap exceeded.",
        rebuttal_seed="Parity: no analogous cap on cardiology follow-ups.",
        flaw_types=["visit limit not disclosed in plain language"],
        plan="fully_insured",
    )


TEMPLATES: dict[str, TemplateFn] = {
    "step_therapy_missing": _step_therapy,
    "conservative_treatment_required": _conservative,
    "frequency_excessive": _frequency,
    "level_of_care_too_high": _level_of_care,
    "not_evidence_based": _not_evidence,
    "duration_excessive": _duration,
    "guideline_mis_cite": _guideline_mis,
    "missing_peer_to_peer": _missing_p2p,
    "formulary_tier_dispute": _formulary,
    "out_of_network_no_authorization": _oon,
    "continuation_of_care_lapsed": _continuation,
    "emergency_retroactive_auth": _emergency_retro,
    "modality_substitution": _modality,
    "visit_limit_exceeded": _visit_limit,
}


def build_scenario_brief(cell: dict[str, str], index: int) -> dict[str, Any]:
    fn = TEMPLATES.get(cell["sub_tactic"])
    if fn is None:
        return _base(
            cell,
            index,
            diagnosis="Hypertension, uncontrolled (I10)",
            treatment="Renal denervation referral",
            denial_seed="Not medically necessary under plan criteria.",
            rebuttal_seed="Resistant hypertension despite three drug classes.",
            flaw_types=["circular reasoning"],
        )
    return fn(cell, index)
