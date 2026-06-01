"""Build AlphaEval-shaped critic verdict dicts for manual cases."""

from __future__ import annotations

from typing import Any


def pass_gate(
    dimension: str,
    reasoning: str,
    quotes: list[str],
    *,
    confidence: float = 0.95,
) -> dict[str, Any]:
    return {
        "dimension": dimension,
        "reasoning": reasoning,
        "score": "PASS",
        "confidence": confidence,
        "evidence_quotes": quotes,
        "improvement": None,
    }


def fail_gate(
    dimension: str,
    reasoning: str,
    quotes: list[str],
    improvement: str,
) -> dict[str, Any]:
    return {
        "dimension": dimension,
        "reasoning": reasoning,
        "score": "FAIL",
        "confidence": 0.9,
        "evidence_quotes": quotes,
        "improvement": improvement,
    }


def score_weighted(
    dimension: str,
    score: int,
    reasoning: str,
    quotes: list[str],
    *,
    improvement: str | None = None,
    confidence: float = 0.85,
) -> dict[str, Any]:
    if score not in (1, 3, 5):
        raise ValueError(f"AlphaEval anchor required 1/3/5, got {score}")
    return {
        "dimension": dimension,
        "reasoning": reasoning,
        "score": score,
        "confidence": confidence,
        "evidence_quotes": quotes,
        "improvement": improvement,
    }


def appeal_difficulty(
    score: int,
    reasoning: str,
    weaknesses: list[str],
    defenses: list[str],
) -> dict[str, Any]:
    return {
        "dimension": "appeal_difficulty",
        "reasoning": reasoning,
        "score": score,
        "confidence": 0.8,
        "evidence_quotes": weaknesses[:2],
        "improvement": None,
        "exploitable_weaknesses": weaknesses,
        "strong_defenses": defenses,
    }


def planner_critics(
    *,
    insurer: str,
    specialty: str,
    sub_tactic: str,
    diagnosis: str,
    treatment: str,
) -> dict[str, dict[str, Any]]:
    return {
        "matrix_coverage": pass_gate(
            "matrix_coverage",
            f"The brief matches the assigned {insurer} / {specialty} cell and executes "
            f"sub_tactic '{sub_tactic}' with a clinically appropriate {diagnosis} → {treatment} pair.",
            [diagnosis, treatment, sub_tactic],
        ),
        "scenario_realism": score_weighted(
            "scenario_realism",
            5,
            "Diagnosis, prior treatments, and insurer administrative posture reflect everyday "
            "commercial UM denials rather than textbook perfection.",
            [diagnosis, treatment],
        ),
    }


def drafter_critics(*, insurer: str, sub_tactic: str, letter_excerpt: str) -> dict[str, dict[str, Any]]:
    voice_map = {
        "Aetna": "CPB and InterQual fingerprints",
        "Cigna": "MCG Care Guidelines",
        "UHC": "UnitedHealthcare medical policy",
    }
    marker = voice_map.get(insurer, "policy citation")
    return {
        "insurer_voice": score_weighted(
            "insurer_voice",
            5,
            f"Letter reads as authentic {insurer} correspondence with {marker} and procedural tone.",
            [letter_excerpt[:120]],
        ),
        "denial_logic": score_weighted(
            "denial_logic",
            5,
            f"Denial logic coherently applies sub_tactic '{sub_tactic}' without internal contradiction.",
            [letter_excerpt[:120]],
        ),
    }


def writer_critics(*, diagnosis: str, treatment: str, ctx_excerpt: str) -> dict[str, dict[str, Any]]:
    return {
        "clinical_realism": score_weighted(
            "clinical_realism",
            3,
            "Clinical narrative is plausible with named drugs, durations, and objective measures; "
            "could add one more numeric lab or scale score for maximal realism.",
            [ctx_excerpt[:120]],
        ),
        "diagnosis_treatment_match": pass_gate(
            "diagnosis_treatment_match",
            f"{treatment} is a standard intervention for {diagnosis} in US commercial practice.",
            [diagnosis, treatment],
        ),
    }


def final_panel_critics(
    *,
    insurer: str,
    denial_type: str,
    letter_excerpt: str,
    appeal_score: int,
    weaknesses: list[str],
    defenses: list[str],
) -> dict[str, dict[str, Any]]:
    return {
        "contradiction_hunter": pass_gate(
            "contradiction_hunter",
            "Patient profile, denial letter, and clinical context agree on diagnosis, requested service, "
            "and timeline without irreconcilable conflicts.",
            [letter_excerpt[:80]],
        ),
        "llm_tell_detector": score_weighted(
            "llm_tell_detector",
            3,
            "Some templated insurer phrasing remains, but paragraph rhythm and specificity avoid "
            "obvious chatbot tells.",
            [letter_excerpt[:80]],
        ),
        "overall_tone": score_weighted(
            "overall_tone",
            5,
            "Cool, administrative insurer voice without inflammatory or marketing language.",
            [letter_excerpt[:80]],
        ),
        "financial_auditor": score_weighted(
            "financial_auditor",
            3,
            "Dollar amounts are sparse; denial focuses on medical necessity rather than cost-shifting.",
            [],
        ),
        "legal_auditor": score_weighted(
            "legal_auditor",
            3,
            "Appeal rights are mentioned but one ERISA/IRO disclosure element is intentionally thin "
            "(exploitable flaw).",
            ["appeal within 180 days"],
        ),
        "demographic_validator": pass_gate(
            "demographic_validator",
            "Age and gender in profile align with clinical narrative without stereotype violations.",
            [],
        ),
        "scope_guard": pass_gate(
            "scope_guard",
            f"In-scope commercial {insurer} {denial_type} case with no Medicare/Medicaid framing.",
            [insurer],
        ),
        "date_sanity": pass_gate(
            "date_sanity",
            "Referenced dates follow a coherent authorization → denial → appeal window sequence.",
            [],
        ),
        "citation_traceability": score_weighted(
            "citation_traceability",
            3,
            "Policy citations are named at a high level; edition numbers are deliberately vague (flaw).",
            ["Clinical Policy Bulletin"],
        ),
        "appeal_difficulty": appeal_difficulty(
            appeal_score,
            "Weighted appealability based on documented step-therapy completion vs procedural gaps.",
            weaknesses,
            defenses,
        ),
    }
