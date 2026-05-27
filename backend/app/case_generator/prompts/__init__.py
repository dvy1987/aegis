"""Prompt templates for the synthetic case generator swarm.

Each file is one prompt. ``PROMPT_VERSIONS`` maps prompt id -> semver. Bump
the version on any prompt edit so provenance reflects which template produced
each case.
"""

from __future__ import annotations

from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent

PROMPT_VERSIONS: dict[str, str] = {
    "p1_scenario_planner": "1.0.0",
    "p2_denial_drafter": "1.0.0",
    "p3_clinical_writer": "1.0.0",
    "p4_adversarial_diversifier": "1.0.0",
    "c_matrix_coverage": "1.0.0",
    "c_scenario_realism": "1.0.0",
    "c_insurer_voice": "1.0.0",
    "c_denial_logic": "1.0.0",
    "c_clinical_realism": "1.0.0",
    "c_diagnosis_treatment_match": "1.0.0",
    "c_diversity_delta": "1.0.0",
    "c_safety_redactor": "1.0.0",
    "c_contradiction_hunter": "1.0.0",
    "c_llm_tell_detector": "1.0.0",
    "c_overall_tone": "1.0.0",
    "c_financial_auditor": "1.0.0",
    "c_legal_auditor": "1.0.0",
    "c_demographic_validator": "1.0.0",
    "c_scope_guard": "1.0.0",
    "c_date_sanity": "1.0.0",
    "c_citation_traceability": "1.0.0",
}


def load_prompt(prompt_id: str) -> str:
    return (PROMPT_DIR / f"{prompt_id}.txt").read_text(encoding="utf-8")
