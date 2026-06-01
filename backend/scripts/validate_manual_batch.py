#!/usr/bin/env python3
"""Validate all cases in a manual generation batch."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "eval" / "cases" / "drafts" / "benchmark-200"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.case_generator.manual_batches.matrix_planner import cells_for_batch  # noqa: E402
from app.case_generator.manual_assemble import _case_id_for  # noqa: E402
from app.case_generator.validator import validate_case  # noqa: E402
from app.case_generator.safety import scan_banned, scan_phi  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--batch", type=int, required=True)
    args = p.parse_args()
    items = cells_for_batch(args.batch)
    failed = 0
    for index, cell in items:
        cid = _case_id_for(cell["insurer"], cell["denial_type"], index) + ".json"
        path = OUT_DIR / cid.replace(".json", ".json")
        path = OUT_DIR / f"{_case_id_for(cell['insurer'], cell['denial_type'], index)}.json"
        if not path.exists():
            print(f"MISSING {path.name}")
            failed += 1
            continue
        case = json.loads(path.read_text())
        vr = validate_case(case)
        text = case["denial_letter_text"] + "\n" + case["clinical_context"]
        banned = scan_banned(text)
        phi = scan_phi(text)
        ok = vr.ok and not banned and not phi
        status = "OK" if ok else "FAIL"
        print(f"{path.name}: {status}")
        if not vr.ok:
            for e in vr.errors:
                print(f"  schema: {e}")
        if banned:
            print(f"  banned: {[h.topic_id for h in banned]}")
        if phi:
            print(f"  phi: {[h.label for h in phi]}")
        if not ok:
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
