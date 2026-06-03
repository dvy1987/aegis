#!/usr/bin/env python3
"""Derive retrieval spot-check queries from eval/cases/drafts for post-index QA.

  cd backend && uv run python scripts/generate_library_spot_checks.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DRAFTS = REPO / "eval" / "cases" / "drafts"
OUT = REPO / "eval" / "library" / "spot_check_queries.json"

# Planner-style query templates per slice
TEMPLATES = [
    "{insurer} {denial_type} medical necessity appeal rights ERISA",
    "{insurer} prior authorization denial appeal documentation",
    "MHPAEA parity {denial_type} behavioral health step therapy",
    "external review IRO adverse benefit determination ACA 2719",
    "{treatment} {diagnosis} clinical evidence medical necessity",
]


def main() -> None:
    combo_counts: Counter = Counter()
    treatment_counts: Counter = Counter()
    pattern_counts: Counter = Counter()

    for p in sorted(DRAFTS.glob("case_*.json")):
        d = json.loads(p.read_text())
        ins = d.get("insurer", "")
        den = d.get("denial_type", "")
        combo_counts[(ins, den)] += 1
        prof = d.get("patient_profile") or {}
        treatment_counts[prof.get("treatment_requested", "")[:80]] += 1
        for pat in d.get("denial_pattern_sources") or []:
            pattern_counts[str(pat).split(":")[0]] += 1

    queries: list[dict] = []

    # One query set per insurer × denial (benchmark grid)
    for (insurer, denial_type), count in combo_counts.most_common():
        sample_case = f"case_*_{insurer.lower().replace(' ', '')}_{'mednec' if 'Medical' in denial_type else 'priorauth'}"
        for tmpl in TEMPLATES[:4]:
            q = tmpl.format(
                insurer=insurer,
                denial_type=denial_type,
                treatment="",
                diagnosis="",
            ).strip()
            queries.append(
                {
                    "query": q,
                    "insurer": insurer,
                    "denial_type": denial_type,
                    "case_slice_count": count,
                    "sample_case_glob": sample_case,
                    "expected_domains": ["legal", "insurer", "clinical", "precedent"],
                    "min_hits": 1,
                }
            )

    # Top treatments across corpus (clinical depth)
    for treatment, n in treatment_counts.most_common(12):
        if not treatment or n < 5:
            continue
        queries.append(
            {
                "query": f"{treatment} medical necessity clinical evidence guideline",
                "insurer": "",
                "denial_type": "Medical Necessity",
                "case_slice_count": n,
                "expected_domains": ["clinical"],
                "min_hits": 1,
                "topic": "clinical_depth",
            }
        )

    # Denial-pattern anchored queries
    for pat, n in pattern_counts.most_common(8):
        if n < 40:
            continue
        if "mhpaea" in pat.lower():
            q = "MHPAEA non-quantitative treatment limitation step therapy behavioral health"
        elif "iro" in pat.lower() or "missing_iro" in pat.lower():
            q = "independent review organization external review notice adverse benefit determination"
        elif "erisa" in pat.lower() or "documentation" in pat.lower():
            q = "ERISA 29 CFR 2560.503 claims procedure appeal deadline documentation"
        elif "evicore" in pat.lower() or "algo" in pat.lower():
            q = "prior authorization utilization management evicore medical necessity denial"
        else:
            continue
        queries.append(
            {
                "query": q,
                "denial_pattern": pat,
                "case_slice_count": n,
                "expected_domains": ["legal", "precedent", "insurer"],
                "min_hits": 1,
                "topic": "denial_pattern",
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_from": str(DRAFTS),
        "case_count": len(list(DRAFTS.glob("case_*.json"))),
        "query_count": len(queries),
        "queries": queries,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(queries)} spot-check queries to {OUT}")


if __name__ == "__main__":
    main()
