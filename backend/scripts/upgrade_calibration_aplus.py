#!/usr/bin/env python3
"""A+ rebuild of calibration drafts case_01–case_20 (flat eval/cases/drafts/)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DRAFTS = REPO / "eval" / "cases" / "drafts"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.case_generator.aplus.calibration_specs import ALL_CALIBRATION_SPECS  # noqa: E402
from app.case_generator.aplus.pipeline import build_aplus_case  # noqa: E402
from app.case_generator.aplus.text_metrics import context_words_ok, letter_words_ok  # noqa: E402
from app.case_generator.manual_assemble import new_run_id  # noqa: E402
from app.case_generator.manual_batches.neighbour import neighbour_summary  # noqa: E402
from app.case_generator.safety import scan_banned, scan_phi  # noqa: E402
from app.case_generator.validator import validate_case  # noqa: E402

ORPHAN = DRAFTS / "case_01_aetna_priorauth.json"
LEGACY_GLOBS = ("test_case_*.json",)


def main() -> int:
    run_id = new_run_id(0).replace("manual-b00", "aplus-cal")
    neighbours: list[str] = []
    failed: list[str] = []
    seed = 20260602

    for spec in ALL_CALIBRATION_SPECS:
        try:
            case = build_aplus_case(
                index=spec.build_index,
                cell=spec.cell,
                run_id=run_id,
                neighbour_summaries=neighbours,
                seed=seed,
                case_id=spec.case_id,
            )
        except Exception as exc:
            failed.append(f"{spec.case_id}: build {exc}")
            continue

        letter_w = len(case["denial_letter_text"].split())
        ctx_w = len(case["clinical_context"].split())
        if not letter_words_ok(case["denial_letter_text"]):
            failed.append(f"{spec.case_id}: letter words={letter_w}")
        if not context_words_ok(case["clinical_context"]):
            failed.append(f"{spec.case_id}: context words={ctx_w}")

        vr = validate_case(case)
        text = case["denial_letter_text"] + "\n" + case["clinical_context"]
        if not vr.ok:
            failed.append(f"{spec.case_id}: schema {vr.errors[0]}")
        if scan_banned(text) or scan_phi(text):
            failed.append(f"{spec.case_id}: safety")

        out = DRAFTS / f"{spec.case_id}.json"
        out.write_text(json.dumps(case, indent=2), encoding="utf-8")
        neighbours.append(neighbour_summary(case))
        if len(neighbours) > 12:
            neighbours.pop(0)
        print(f"OK {spec.case_id} letter={letter_w}w ctx={ctx_w}w")

    if failed:
        print(f"done with errors. failures={len(failed)}")
        for f in failed[:25]:
            print(" ", f)
        return 1

    for pattern in LEGACY_GLOBS:
        for old in DRAFTS.glob(pattern):
            old.unlink()
            print(f"removed legacy {old.name}")

    if ORPHAN.exists():
        ORPHAN.unlink()
        print("removed orphan case_01_aetna_priorauth.json")

    print(f"done. failures={len(failed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
