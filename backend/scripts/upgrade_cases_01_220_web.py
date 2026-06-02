#!/usr/bin/env python3
"""Add web-researched references + material letter improvements to draft cases.

Preserves case identity (matrix cell, clinical context, flaws). Updates:
  - denial_letter_references (web cache + catalog)
  - denial_letter_text (claim-file block, insurer-specific P2P, policy naming)
  - re-applies flaw patches after enhancements

Usage:
  cd backend && uv run python scripts/upgrade_cases_01_220_web.py
  cd backend && uv run python scripts/upgrade_cases_01_220_web.py --start 221 --end 420
  cd backend && uv run python scripts/upgrade_cases_01_220_web.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DRAFTS = REPO / "eval" / "cases" / "drafts"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.case_generator.aplus.flaws import inject_flaws  # noqa: E402
from app.case_generator.aplus.letter_enhancements import (  # noqa: E402
    enhance_denial_letter,
    parse_pattern_ids,
)
from app.case_generator.aplus.letter_references import select_letter_references  # noqa: E402
from app.case_generator.aplus.text_metrics import (  # noqa: E402
    context_words_ok,
    fit_letter_word_budget,
    letter_words_ok,
    repair_denial_letter_artifacts,
)
from app.case_generator.safety import scan_banned, scan_phi  # noqa: E402
from app.case_generator.validator import validate_case  # noqa: E402

_CASE_NUM = re.compile(r"^case_(\d+)_")


def _case_number(path: Path) -> int | None:
    m = _CASE_NUM.match(path.stem)
    return int(m.group(1)) if m else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=220)
    args = parser.parse_args()

    failed: list[str] = []
    updated = 0

    for path in sorted(DRAFTS.glob("case_*.json")):
        num = _case_number(path)
        if num is None or num < args.start or num > args.end:
            continue

        case = json.loads(path.read_text(encoding="utf-8"))
        cell = case["synthetic_provenance"]["matrix_cell"]
        pattern_ids = parse_pattern_ids(case.get("denial_pattern_sources", []))
        patterns = [{"id": pid} for pid in pattern_ids]

        refs = select_letter_references(
            insurer=case["insurer"],
            denial_type=case["denial_type"],
            pattern_ids=pattern_ids,
            cell=cell,
            use_web_research=True,
        )

        letter = enhance_denial_letter(
            case["denial_letter_text"],
            insurer=case["insurer"],
            denial_type=case["denial_type"],
            cell=cell,
            pattern_ids=pattern_ids,
        )

        prof = case["patient_profile"]
        patched = inject_flaws(
            letter=letter,
            context=case["clinical_context"],
            brief={
                "diagnosis": prof["diagnosis"],
                "treatment_requested": prof["treatment_requested"],
                "intended_flaw_types": pattern_ids,
            },
            patterns=patterns,
            index=num,
        )
        letter = fit_letter_word_budget(
            repair_denial_letter_artifacts(patched["denial_letter_text"])
        )

        case["denial_letter_references"] = refs
        case["denial_letter_text"] = letter
        if case.get("submission_timestamp") is None:
            case["submission_timestamp"] = patched.get("submission_timestamp")
        if case.get("denial_timestamp") is None:
            case["denial_timestamp"] = patched.get("denial_timestamp")

        prov = case.setdefault("synthetic_provenance", {})
        summary = prov.get("human_summary", "")
        _upgrade_note = (
            " Upgraded 2026-06-02: web-sourced denial_letter_references and "
            "claim-file / peer-to-peer letter enhancements from public sources."
        )
        if _upgrade_note.strip() not in summary:
            prov["human_summary"] = summary.rstrip() + _upgrade_note

        if not letter_words_ok(letter):
            failed.append(f"{case['case_id']}: letter word count")
        if not context_words_ok(case["clinical_context"]):
            failed.append(f"{case['case_id']}: context word count")

        vr = validate_case(case)
        text = letter + "\n" + case["clinical_context"]
        if not vr.ok:
            failed.append(f"{case['case_id']}: {vr.errors[0]}")
        if scan_banned(text) or scan_phi(text):
            failed.append(f"{case['case_id']}: safety")

        if len(refs) < 5:
            failed.append(f"{case['case_id']}: refs={len(refs)}")

        if args.dry_run:
            print(
                f"DRY {case['case_id']} refs={len(refs)} "
                f"letter={len(letter.split())}w claim_file={'claim file' in letter.lower()}"
            )
            continue

        path.write_text(json.dumps(case, indent=2), encoding="utf-8")
        updated += 1
        print(f"OK {case['case_id']} refs={len(refs)} letter={len(letter.split())}w")

    print(f"done. updated={updated} failures={len(failed)}")
    for f in failed[:20]:
        print(" ", f)
    return 1 if failed and not args.dry_run else 0


if __name__ == "__main__":
    raise SystemExit(main())
