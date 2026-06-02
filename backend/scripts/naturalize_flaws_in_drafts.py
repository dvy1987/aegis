#!/usr/bin/env python3
"""Rewrite existing draft cases so flaws read natural but detectable.

This updates denial letters in-place under `eval/cases/drafts/` by:
- enforcing omission-flaws (`missing_iro_notice`, `missing_cost_liability`)
- ensuring presence-flaws are visible with realistic boilerplate anchors
- cleaning known letter artifacts + re-fitting word budget

Usage:
  cd backend && uv run python scripts/naturalize_flaws_in_drafts.py
  cd backend && uv run python scripts/naturalize_flaws_in_drafts.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from app.case_generator.aplus.text_metrics import fit_letter_word_budget, repair_denial_letter_artifacts
from app.case_generator.validator import validate_case


REPO = Path(__file__).resolve().parents[2]
DRAFTS = REPO / "eval" / "cases" / "drafts"


def _pattern_ids(case: dict) -> set[str]:
    ids = set()
    for s in case.get("denial_pattern_sources") or []:
        ids.add(str(s).split(":", 1)[0].strip())
    return {x for x in ids if x}


def _remove_sentences(letter: str, needles: list[str]) -> str:
    chunks = re.split(r"(?<=[\.\n])\s+", letter)
    kept = []
    for c in chunks:
        cl = c.lower()
        if any(n in cl for n in needles):
            continue
        kept.append(c)
    return " ".join(kept).strip()


def _ensure_contains(letter: str, needle: str, *, after: str | None = None) -> str:
    if needle.lower() in letter.lower():
        return letter
    if after and after in letter:
        return letter.replace(after, after + "\n" + needle, 1)
    return letter.rstrip() + "\n\n" + needle


def _clean(letter: str) -> str:
    letter = repair_denial_letter_artifacts(letter)
    letter = re.sub(r"(This determination was made by Dr\.[^\n]+\n)\1+", r"\1", letter)
    letter = re.sub(
        r"(MCG Care Guidelines \(edition not specified\))(?: and \1){2,}",
        r"\1",
        letter,
    )
    return fit_letter_word_budget(letter)


def naturalize_case(case: dict) -> tuple[dict, list[str]]:
    pats = _pattern_ids(case)
    letter = str(case.get("denial_letter_text") or "")
    changes: list[str] = []

    # Omission flaws.
    if "missing_iro_notice" in pats:
        new = _remove_sentences(letter, ["external review", "independent external review", "iro", "independent review organization"])
        if new != letter:
            letter = new
            changes.append("removed external-review/IRO language (missing_iro_notice)")

    if "missing_cost_liability" in pats:
        new = _remove_sentences(letter, ["financially responsible", "financial responsibility", "you may be billed", "balance bill"])
        if new != letter:
            letter = new
            changes.append("removed cost-liability language (missing_cost_liability)")

    # Presence flaws (natural-but-detectable anchors).
    if "circular_medical_necessity" in pats:
        needle = "The requested service is not medically necessary because it does not meet the plan's medical necessity criteria."
        letter2 = _ensure_contains(letter, needle, after="EXPLANATION OF DECISION")
        if letter2 != letter:
            letter = letter2
            changes.append("added circular-medical-necessity anchor")

    if "appeal_closed_as_withdrawn" in pats:
        needle = (
            "If required information is not received within the applicable timeframe, the appeal may be administratively closed as withdrawn."
        )
        letter2 = _ensure_contains(letter, needle, after="APPEAL RIGHTS")
        if letter2 != letter:
            letter = letter2
            changes.append("added appeal-closed-as-withdrawn anchor")

    if "wrong_appeals_contact" in pats:
        needle = "Appeals contact (as listed): Appeals Unit, P.O. Box 14582, Lexington, KY 40512-4582; Fax: (877) 555-0199."
        letter2 = _ensure_contains(letter, needle, after="APPEAL RIGHTS")
        if letter2 != letter:
            letter = letter2
            changes.append("added wrong-appeals-contact anchor")

    if "plan_exclusion_overrides_state_mandate" in pats:
        needle = (
            "This determination is based on a plan exclusion. State coverage mandates do not alter the terms of this plan for this determination."
        )
        letter2 = _ensure_contains(letter, needle, after="EXPLANATION OF DECISION")
        if letter2 != letter:
            letter = letter2
            changes.append("added plan-exclusion/state-mandate anchor")

    if "wrong_benefit_category" in pats:
        needle = "This request has been processed under a benefit category that does not provide coverage for the requested service (benefit category classification)."
        letter2 = _ensure_contains(letter, needle, after="EXPLANATION OF DECISION")
        if letter2 != letter:
            letter = letter2
            changes.append("added wrong-benefit-category anchor")

    if "incorrect_demographic_guideline" in pats:
        needle = "Guideline applied: pediatric imaging criteria (ages 0–17) referenced for this request (incorrect demographic guideline)."
        letter2 = _ensure_contains(letter, needle, after="Clinical policy applied:")
        if letter2 != letter:
            letter = letter2
            changes.append("added incorrect-demographic-guideline anchor")

    if "superseded_guideline" in pats:
        needle = "Clinical criteria applied: InterQual criteria (2018) and/or older MCG modules (superseded guideline reference)."
        letter2 = _ensure_contains(letter, needle, after="Clinical policy applied:")
        if letter2 != letter:
            letter = letter2
            changes.append("added superseded-guideline anchor")

    if "mhpaea_step_therapy_asymmetry" in pats:
        needle = "For behavioral health benefits, step-therapy and documentation requirements may be applied more restrictively than comparable medical/surgical benefits for services of similar intensity."
        letter2 = _ensure_contains(letter, needle, after="EXPLANATION OF DECISION")
        if letter2 != letter:
            letter = letter2
            changes.append("added MHPAEA step-therapy asymmetry anchor")

    # algo_boilerplate_fingerprint: ensure letter contains minimal specifics.
    if "algo_boilerplate_fingerprint" in pats:
        before = letter
        letter = re.sub(
            r"for [A-Za-z0-9\-\s\(\)\/]+ related to [A-Za-z0-9\-\s\(\)\.,]+",
            "for the requested service.",
            letter,
        )
        letter = re.sub(r"Service requested:.*\n", "Service requested: [REDACTED]\n", letter)
        letter = re.sub(r"Diagnosis \(as submitted\):.*\n", "Diagnosis (as submitted): [REDACTED]\n", letter)
        if letter != before:
            changes.append("redacted service/diagnosis in letter (algo_boilerplate_fingerprint)")

    cleaned = _clean(letter)
    if cleaned != letter:
        letter = cleaned
        changes.append("cleaned artifacts + fit word budget")

    out = dict(case)
    out["denial_letter_text"] = letter
    return out, changes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    paths = sorted(DRAFTS.glob("case_*.json"))
    changed_n = 0
    for p in paths:
        case = json.loads(p.read_text(encoding="utf-8"))
        updated, changes = naturalize_case(case)
        if changes:
            changed_n += 1
        vr = validate_case(updated)
        if not vr.ok:
            raise SystemExit(f"{case.get('case_id')}: schema invalid after edits: {vr.errors[:1]}")
        if (not args.dry_run) and updated != case:
            p.write_text(json.dumps(updated, indent=2), encoding="utf-8")

    print(f"done. cases={len(paths)} changed={changed_n} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

