#!/usr/bin/env python3
"""Manual Gumloop-style fix pass for a 10-case sample (case_01..case_10).

Goal: ensure each listed denial_pattern_sources flaw is clearly present in the
denial letter / timestamps, and clean obvious LLM/artifact issues.

This is NOT the full Gumloop LLM swarm. It's a human-directed edit pass encoded
as deterministic transformations so changes are reviewable and repeatable.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.case_generator.aplus.text_metrics import fit_letter_word_budget, repair_denial_letter_artifacts
from app.case_generator.validator import validate_case


REPO = Path(__file__).resolve().parents[2]
DRAFTS = REPO / "eval" / "cases" / "drafts"


def _load(case_id: str) -> dict:
    p = DRAFTS / f"{case_id}.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _write(case: dict) -> None:
    p = DRAFTS / f"{case['case_id']}.json"
    p.write_text(json.dumps(case, indent=2), encoding="utf-8")


def _pattern_ids(case: dict) -> list[str]:
    out = []
    for s in case.get("denial_pattern_sources") or []:
        out.append(str(s).split(":", 1)[0].strip())
    return [x for x in out if x]


def _remove_external_review(letter: str) -> str:
    # Remove sentences that mention external review / IRO.
    chunks = re.split(r"(?<=[\.\n])\s+", letter)
    kept = []
    for c in chunks:
        cl = c.lower()
        if any(x in cl for x in ["external review", "independent external review", "independent review organization", "iro"]):
            continue
        kept.append(c)
    return " ".join(kept).strip()


def _remove_cost_liability(letter: str) -> str:
    chunks = re.split(r"(?<=[\.\n])\s+", letter)
    kept = []
    for c in chunks:
        cl = c.lower()
        if any(x in cl for x in ["financially responsible", "you may be billed", "balance bill", "financial responsibility"]):
            continue
        kept.append(c)
    return " ".join(kept).strip()


def _ensure_contains(letter: str, needle: str, *, after: str | None = None) -> str:
    if needle.lower() in letter.lower():
        return letter
    if after and after in letter:
        return letter.replace(after, after + "\n\n" + needle, 1)
    return letter.rstrip() + "\n\n" + needle


def _fix_common_artifacts(letter: str) -> str:
    letter = repair_denial_letter_artifacts(letter)
    # Remove duplicated "This determination was made..." lines if repeated.
    letter = re.sub(r"(This determination was made by Dr\.[^\n]+\n)\1+", r"\1", letter)
    # Collapse triple repeated "MCG Care Guidelines (edition not specified)" spam.
    letter = re.sub(
        r"(MCG Care Guidelines \(edition not specified\))(?: and \1){2,}",
        r"\1",
        letter,
    )
    return fit_letter_word_budget(letter)


def _apply(case: dict) -> tuple[dict, list[str]]:
    cid = case["case_id"]
    patterns = set(_pattern_ids(case))
    changed: list[str] = []

    letter = case.get("denial_letter_text") or ""
    ctx = case.get("clinical_context") or ""

    # Flaws that require OMISSION.
    if "missing_iro_notice" in patterns:
        new = _remove_external_review(letter)
        if new != letter:
            letter = new
            changed.append("removed external-review/IRO language (to satisfy missing_iro_notice)")
    if "missing_cost_liability" in patterns:
        new = _remove_cost_liability(letter)
        if new != letter:
            letter = new
            changed.append("removed cost-liability language (to satisfy missing_cost_liability)")

    # Flaws that require PRESENCE.
    if "circular_medical_necessity" in patterns:
        letter2 = _ensure_contains(
            letter,
            "The requested service is not medically necessary because it does not meet the plan's medical necessity criteria.",
            after="EXPLANATION OF DECISION",
        )
        if letter2 != letter:
            letter = letter2
            changed.append("added explicit circular medical-necessity sentence")

    if "mhpaea_step_therapy_asymmetry" in patterns:
        letter2 = _ensure_contains(
            letter,
            "For behavioral health benefits, step-therapy and documentation requirements may be applied more restrictively than comparable medical/surgical benefits for services of similar intensity.",
            after="EXPLANATION OF DECISION",
        )
        if letter2 != letter:
            letter = letter2
            changed.append("added MHPAEA step-therapy asymmetry signal sentence")

    if "wrong_benefit_category" in patterns:
        letter2 = _ensure_contains(
            letter,
            "This request has been processed under a benefit category that does not provide coverage for the requested service (benefit category classification).",
            after="EXPLANATION OF DECISION",
        )
        if letter2 != letter:
            letter = letter2
            changed.append("added wrong benefit category statement")

    if "appeal_closed_as_withdrawn" in patterns:
        letter2 = _ensure_contains(
            letter,
            "If required information is not received within the applicable timeframe, the appeal may be administratively closed as withdrawn.",
            after="APPEAL RIGHTS",
        )
        if letter2 != letter:
            letter = letter2
            changed.append("added appeal-closed-as-withdrawn language")

    if "superseded_guideline" in patterns:
        letter2 = _ensure_contains(
            letter,
            "Clinical criteria applied: InterQual criteria (2018) and/or older MCG modules (superseded guideline reference).",
            after="Clinical policy applied:",
        )
        if letter2 != letter:
            letter = letter2
            changed.append("added superseded guideline signal sentence")

    if "plan_exclusion_overrides_state_mandate" in patterns:
        letter2 = _ensure_contains(
            letter,
            "This determination is based on a plan exclusion. State coverage mandates do not alter the terms of this plan for this determination.",
            after="EXPLANATION OF DECISION",
        )
        if letter2 != letter:
            letter = letter2
            changed.append("added plan-exclusion-overrides-state-mandate language")

    if "wrong_appeals_contact" in patterns:
        letter2 = _ensure_contains(
            letter,
            "Appeals contact (as listed): Appeals Unit, P.O. Box 14582, Lexington, KY 40512-4582; Fax: (877) 555-0199.",
            after="APPEAL RIGHTS",
        )
        if letter2 != letter:
            letter = letter2
            changed.append("added implausible/wrong appeals contact block")

    if "incorrect_demographic_guideline" in patterns:
        letter2 = _ensure_contains(
            letter,
            "Guideline applied: pediatric imaging criteria (ages 0\u201317) referenced for this request (incorrect demographic guideline).",
            after="Clinical policy applied:",
        )
        if letter2 != letter:
            letter = letter2
            changed.append("added incorrect demographic guideline reference")

    if "algo_boilerplate_fingerprint" in patterns:
        # Remove explicit diagnosis/treatment mentions from the denial letter (keep IDs/claim info).
        # This is intentionally harsh: the flaw is "no patient-specific details".
        before = letter
        letter = re.sub(r"for [A-Za-z0-9\-\s\(\)\/]+ related to [A-Za-z0-9\-\s\(\)\.,]+", "for the requested service.", letter)
        letter = re.sub(r"Service requested:.*\n", "Service requested: [REDACTED]\n", letter)
        letter = re.sub(r"Diagnosis \(as submitted\):.*\n", "Diagnosis (as submitted): [REDACTED]\n", letter)
        if letter != before:
            changed.append("removed patient-specific service/diagnosis mentions (to satisfy algo_boilerplate_fingerprint)")

    # Clean obvious artifacts (broken splices, duplicated lines, spam).
    fixed = _fix_common_artifacts(letter)
    if fixed != letter:
        letter = fixed
        changed.append("cleaned letter artifacts + fit word budget")

    # Update case
    out = dict(case)
    out["denial_letter_text"] = letter
    out["clinical_context"] = ctx
    return out, changed


def main() -> int:
    case_ids = [
        "case_01_cigna_mednec",
        "case_02_cigna_priorauth",
        "case_03_aetna_mednec",
        "case_04_aetna_priorauth",
        "case_05_uhc_mednec",
        "case_06_uhc_priorauth",
        "case_07_cigna_mednec",
        "case_08_cigna_priorauth",
        "case_09_aetna_mednec",
        "case_10_uhc_priorauth",
    ]

    report: list[dict] = []
    for cid in case_ids:
        case = _load(cid)
        updated, changes = _apply(case)
        vr = validate_case(updated)
        if not vr.ok:
            raise SystemExit(f"{cid}: schema invalid after edits: {vr.errors[:1]}")
        _write(updated)
        report.append({"case_id": cid, "changes": changes})

    out = REPO / "eval" / "gumloop_runs" / "manual-llm-sample" / "01-10-naturalized-changes.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

