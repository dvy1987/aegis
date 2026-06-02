#!/usr/bin/env python3
"""Sync frontend demo fixtures from drafts case_11–case_20 (student-visible fields only)."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DRAFTS = REPO / "eval" / "cases" / "drafts"
SHOWCASE = REPO / "frontend" / "src" / "lib" / "fixtures" / "showcase"

DENIAL_LABEL = {
    "Medical Necessity": "Medical necessity",
    "Prior Authorization": "Prior authorization",
}


def _case_number(stem: str) -> int | None:
    m = re.match(r"case_(\d+)_", stem)
    return int(m.group(1)) if m else None


def _headline(case: dict) -> str:
    ins = case["insurer"]
    tx = case["patient_profile"]["treatment_requested"].split("(")[0].strip()[:35]
    dt = DENIAL_LABEL.get(case["denial_type"], case["denial_type"])
    return f"{tx} — {dt.lower()} ({ins})"


def main() -> None:
    for path in sorted(DRAFTS.glob("case_*.json")):
        n = _case_number(path.stem)
        if n is None or not 11 <= n <= 20:
            continue
        case = json.loads(path.read_text(encoding="utf-8"))
        out = {
            "case_id": case["case_id"],
            "insurer": case["insurer"],
            "denial_type": DENIAL_LABEL.get(case["denial_type"], case["denial_type"]),
            "headline": _headline(case),
            "denial_letter_text": case["denial_letter_text"],
            "clinical_context": case["clinical_context"],
        }
        dest = SHOWCASE / f"{case['case_id']}.json"
        dest.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {dest.relative_to(REPO)}")


if __name__ == "__main__":
    main()
