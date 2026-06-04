"""Curated clinical knowledge base (harvested from aplus/scenarios.py).

Loads ``eval/clinical_variants.json`` — 120 hand-curated variants across 10 specialties,
each with real dx (+ICD), tx, specific clinical_facts, rebuttal_core, and a
``sex_constraint`` (M | F | any).

Two jobs in the LLM pipeline:
  1. Ground the P1 planner on real clinical facts (improves J4 case-specificity, clinical
     realism, and prevents hallucinated medicine).
  2. Provide the deterministic SEX GUARD: ``required_sex(diagnosis, treatment)`` so the
     pipeline forces patient_gender to match a sex-specific diagnosis — fixing the
     root-cause demographic bug (gender was previously taken from the random matrix cell).
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from random import Random
from typing import Any

from .config import EVAL_DIR

VARIANTS_PATH = EVAL_DIR / "clinical_variants.json"
RATIONALE_SEEDS_PATH = EVAL_DIR / "denial_rationale_seeds.json"

# Sex inference for diagnoses/treatments not pre-tagged in the KB (defensive guard).
_FEMALE = re.compile(
    r"ovarian|ovary|menorrhagia|adenomyosis|endometri|uterine|uterus|polycystic ovary|PCOS"
    r"|cervix|cervical (?:cancer|dysplasia|intraepithelial)|vagin|fibroid|myoma|menopaus"
    r"|pregnan|gestational|fallopian|vulv|gynecolog|macromastia|breast (?:cancer|hypertrophy|hyperplasia)"
    r"|fibrocystic breast|breast lump|breast pain|uterine prolapse",
    re.I,
)
_MALE = re.compile(
    r"gynecomastia|prostat|testicular|testis|testes|male hypogonadism|erectile|penile"
    r"|scrotal|varicocele|BPH|benign prostatic",
    re.I,
)


@lru_cache(maxsize=1)
def load_variants() -> dict[str, list[dict[str, Any]]]:
    with VARIANTS_PATH.open(encoding="utf-8") as fh:
        return json.load(fh).get("specialties", {})


def variants_for(specialty: str) -> list[dict[str, Any]]:
    return load_variants().get(specialty, [])


def required_sex(diagnosis: str, treatment: str = "") -> str | None:
    """Return 'M' / 'F' if the dx/tx is sex-specific, else None.

    First trusts the KB's pre-computed ``sex_constraint`` for an exact dx match, then
    falls back to regex inference for free-text diagnoses the LLM may invent.
    """
    for variants in load_variants().values():
        for v in variants:
            if v["diagnosis"] == diagnosis:
                sc = v.get("sex_constraint", "any")
                return sc if sc in ("M", "F") else None
    blob = f"{diagnosis} {treatment}"
    if _MALE.search(blob):
        return "M"
    if _FEMALE.search(blob):
        return "F"
    return None


def select_variant(specialty: str, rng: Random) -> dict[str, Any] | None:
    pool = variants_for(specialty)
    return rng.choice(pool) if pool else None


@lru_cache(maxsize=1)
def _load_rationale_seeds() -> dict[str, dict[str, str]]:
    if not RATIONALE_SEEDS_PATH.exists():
        return {}
    with RATIONALE_SEEDS_PATH.open(encoding="utf-8") as fh:
        return json.load(fh).get("seeds", {})


def rationale_seed(sub_tactic: str) -> str:
    """A curated, sub_tactic-aligned denial-rationale exemplar for P1 grounding (harvested
    from aplus _denial_seeds). Adapt, don't copy — keeps denial logic aligned to the tactic."""
    s = _load_rationale_seeds().get(sub_tactic)
    if not s:
        return ""
    return ("Denial-rationale exemplar for this sub_tactic (adapt with the real dx/tx, do "
            f"not copy verbatim): {s['denial_rationale']}")


def grounding_block(specialty: str, *, limit: int = 12) -> str:
    """Render the specialty's variants as a grounding pool for the P1 prompt."""
    rows = variants_for(specialty)[:limit]
    if not rows:
        return "(no curated variants for this specialty; use real-world clinical knowledge)"
    lines = []
    for v in rows:
        sx = v.get("sex_constraint", "any")
        sx_note = f" [sex: {sx}]" if sx in ("M", "F") else ""
        lines.append(
            f"- dx: {v['diagnosis']}{sx_note}\n"
            f"  tx: {v['treatment_requested']}\n"
            f"  facts: {v['clinical_facts']}"
        )
    return "\n".join(lines)
