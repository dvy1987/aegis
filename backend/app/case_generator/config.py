from __future__ import annotations

import json
import os
import random
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
EVAL_DIR = REPO_ROOT / "eval"
SCHEMA_PATH = EVAL_DIR / "case_schema.json"
MATRIX_PATH = EVAL_DIR / "diversity_matrix.json"
BANNED_PATH = EVAL_DIR / "banned_topics.json"
PATTERNS_PATH = EVAL_DIR / "denial_patterns.json"


DEFAULT_MODEL = os.environ.get("AEGIS_CASEGEN_MODEL", "gemini-3.1-pro")
CRITIC_MODEL = os.environ.get("AEGIS_CASEGEN_CRITIC_MODEL", "gemini-3.1-pro") # Ideally should be non-Gemini to prevent self-enhancement bias


@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    with SCHEMA_PATH.open() as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def load_matrix() -> dict[str, Any]:
    with MATRIX_PATH.open() as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def load_banned() -> dict[str, Any]:
    with BANNED_PATH.open() as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def load_denial_patterns() -> dict[str, Any]:
    with PATTERNS_PATH.open() as fh:
        return json.load(fh)


def _weighted_choice(items: list[dict[str, Any]], rng: random.Random) -> dict[str, Any]:
    weights = [it["weight"] for it in items]
    return rng.choices(items, weights=weights, k=1)[0]


def sample_matrix_cell(
    rng: random.Random,
    forbid_cells: set[tuple[str, ...]] | None = None,
    max_retries: int = 64,
) -> dict[str, str]:
    """Weighted sample one cell of the diversity matrix.

    forbid_cells is a set of insurer/denial/specialty/sub_tactic tuples already
    drawn this run; we retry to maximise dataset spread.
    """
    matrix = load_matrix()
    axes = matrix["axes"]
    forbid_cells = forbid_cells or set()

    for _ in range(max_retries):
        insurer = _weighted_choice(axes["insurer"], rng)["value"]
        denial = _weighted_choice(axes["denial_type"], rng)["value"]
        specialty = _weighted_choice(axes["specialty"], rng)["value"]
        age_band = _weighted_choice(axes["patient_age_band"], rng)["value"]
        gender = _weighted_choice(axes["patient_gender"], rng)["value"]
        sub_axis = (
            "sub_tactic_medical_necessity"
            if denial == "Medical Necessity"
            else "sub_tactic_prior_authorization"
        )
        sub_tactic = _weighted_choice(axes[sub_axis], rng)["value"]
        key = (insurer, denial, specialty, sub_tactic)
        if key in forbid_cells:
            continue
        return {
            "insurer": insurer,
            "denial_type": denial,
            "patient_age_band": age_band,
            "patient_gender": gender,
            "specialty": specialty,
            "sub_tactic": sub_tactic,
        }
    return {
        "insurer": insurer,
        "denial_type": denial,
        "patient_age_band": age_band,
        "patient_gender": gender,
        "specialty": specialty,
        "sub_tactic": sub_tactic,
    }


def sample_denial_patterns(
    rng: random.Random,
    insurer: str,
    specialty: str,
    max_patterns: int = 2
) -> list[dict[str, Any]]:
    """Sample denial patterns from denial_patterns.json, ensuring diversity."""
    patterns = load_denial_patterns().get("patterns", [])
    valid_patterns = []
    for p in patterns:
        if insurer not in p.get("insurer_affinity", []):
            continue
        if p.get("category") == "mhpaea_parity" and specialty != "behavioral_health":
            continue
        valid_patterns.append(p)
    
    if not valid_patterns:
        return []
    
    # Try to pick patterns from different categories
    chosen = []
    seen_categories = set()
    rng.shuffle(valid_patterns)
    for p in valid_patterns:
        cat = p.get("category", "")
        if cat not in seen_categories:
            chosen.append(p)
            seen_categories.add(cat)
            if len(chosen) >= max_patterns:
                break
    
    # If we still need more, just pick any valid
    if len(chosen) < max_patterns:
        for p in valid_patterns:
            if p not in chosen:
                chosen.append(p)
                if len(chosen) >= max_patterns:
                    break
    
    return chosen


def specialty_examples(specialty: str) -> list[str]:
    for entry in load_matrix()["axes"]["specialty"]:
        if entry["value"] == specialty:
            return entry.get("examples", [])
    return []


def sub_tactic_definition(denial_type: str, sub_tactic: str) -> str:
    matrix = load_matrix()
    key = (
        "sub_tactic_medical_necessity"
        if denial_type == "Medical Necessity"
        else "sub_tactic_prior_authorization"
    )
    for entry in matrix["axes"][key]:
        if entry["value"] == sub_tactic:
            return entry.get("definition", "")
    return ""


def matrix_version() -> str:
    return load_matrix().get("version", "0.0.0")


def banned_filter_version() -> str:
    return load_banned().get("version", "0.0.0")


def schema_version() -> str:
    schema = load_schema()
    return schema.get("x-aegis-schema-version", "0.0.0")


def joint_constraints_text() -> str:
    return "\n".join(f"- {c}" for c in load_matrix().get("joint_constraints", []))
