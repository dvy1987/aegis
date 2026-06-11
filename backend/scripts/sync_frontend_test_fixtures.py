#!/usr/bin/env python3
"""Sync measured-lift demo fixtures from drafts/showcase-eval (student-visible fields only)."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DRAFTS = REPO / "eval" / "cases" / "drafts" / "showcase-eval"
CASES_TS = REPO / "frontend" / "src" / "lib" / "fixtures" / "cases.ts"
SHOWCASE = REPO / "frontend" / "src" / "lib" / "fixtures" / "showcase"
MEASURED_LIFT_CASES = (
    "case_168_aetna_priorauth",
    "case_180_cigna_mednec",
    "case_193_cigna_priorauth",
)

DENIAL_LABEL = {
    "Medical Necessity": "Medical necessity",
    "Prior Authorization": "Prior authorization",
}


def _case_number(stem: str) -> int | None:
    m = re.match(r"case_(\d+)_", stem)
    return int(m.group(1)) if m else None


def _headline(case: dict) -> str:
    """Treatment line only — insurer and denial type appear in the cycler heading above."""
    return str(case["patient_profile"]["treatment_requested"]).strip()


def _case_summary(case: dict) -> dict:
    profile = case["patient_profile"]
    return {
        "case_id": case["case_id"],
        "insurer": case["insurer"],
        "patient_age": profile["age"],
        "patient_gender": profile["gender"],
        "denial_type": DENIAL_LABEL.get(case["denial_type"], case["denial_type"]),
        "headline": _headline(case),
        "denial_letter_text": case["denial_letter_text"],
        "clinical_context": case["clinical_context"],
    }


def main() -> None:
    summaries: list[dict] = []
    for case_id in MEASURED_LIFT_CASES:
        path = DRAFTS / f"{case_id}.json"
        case = json.loads(path.read_text(encoding="utf-8"))
        summaries.append(_case_summary(case))
        dest = SHOWCASE / f"{case_id}.json"
        existing = json.loads(dest.read_text(encoding="utf-8")) if dest.exists() else {}
        # Preserve illustrative v1/v3 bundle fields when re-syncing case copy.
        dest.write_text(
            json.dumps({**existing, **_case_summary(case)}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {dest.relative_to(REPO)}")

    lines = ['import type { CaseSummary } from "@/lib/types";', "", "export const CASES: CaseSummary[] = ["]
    for row in summaries:
        lines.append("  {")
        for key, value in row.items():
            lines.append(f"    {key}: {json.dumps(value)},")
        lines.append("  },")
    lines.append("];")
    lines.append("")
    CASES_TS.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {CASES_TS.relative_to(REPO)}")


if __name__ == "__main__":
    main()
