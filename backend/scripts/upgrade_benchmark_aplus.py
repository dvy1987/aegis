#!/usr/bin/env python3
"""Rebuild benchmark-200 cases to A+ (prompt-aligned schema v1.1.0). No Gumloop."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "eval" / "cases" / "drafts"
LEGACY = REPO / "eval" / "cases" / "drafts"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.case_generator import config  # noqa: E402
from app.case_generator.aplus.pipeline import build_aplus_case  # noqa: E402
from app.case_generator.aplus.text_metrics import context_words_ok, letter_words_ok  # noqa: E402
from app.case_generator.manual_assemble import new_run_id  # noqa: E402
from app.case_generator.manual_batches.matrix_planner import planned_cells  # noqa: E402
from app.case_generator.manual_batches.neighbour import neighbour_summary  # noqa: E402
from app.case_generator.validator import validate_case  # noqa: E402
from app.case_generator.safety import scan_banned, scan_phi  # noqa: E402


def _patch_legacy(path: Path) -> bool:
    """Minimal legacy uplift: plan_funding_type + schema fields if missing."""
    if not path.exists():
        return False
    case = json.loads(path.read_text())
    prof = case.setdefault("patient_profile", {})
    if "plan_funding_type" not in prof:
        prof["plan_funding_type"] = "self_funded"
    if not case.get("denial_pattern_sources"):
        case["denial_pattern_sources"] = ["legacy_uplift: pre-schema draft"]
    prov = case.setdefault("synthetic_provenance", {})
    prov.setdefault("schema_version", "1.0.0")
    ad = prov.setdefault(
        "appeal_difficulty",
        {
            "score": 3,
            "reasoning": "Legacy draft uplifted for schema; appeal difficulty not re-derived.",
            "exploitable_weaknesses": ["Not re-evaluated in uplift pass."],
            "strong_defenses": ["Not re-evaluated in uplift pass."],
        },
    )
    path.write_text(json.dumps(case, indent=2), encoding="utf-8")
    return True


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    seed = 20260601
    cells = planned_cells(seed)
    run_id = new_run_id(99).replace("manual-b99", "aplus-v2")
    neighbours: list[str] = []
    failed: list[str] = []

    for offset, cell in enumerate(cells):
        index = 11 + offset
        try:
            case = build_aplus_case(
                index=index,
                cell=cell,
                run_id=run_id,
                neighbour_summaries=neighbours,
                seed=seed,
            )
        except Exception as exc:
            failed.append(f"{index}: build {exc}")
            continue

        letter_ok = letter_words_ok(case["denial_letter_text"])
        ctx_ok = context_words_ok(case["clinical_context"])
        if not letter_ok:
            failed.append(f"{index}: letter words={len(case['denial_letter_text'].split())}")
        if not ctx_ok:
            failed.append(f"{index}: context words={len(case['clinical_context'].split())}")

        vr = validate_case(case)
        text = case["denial_letter_text"] + "\n" + case["clinical_context"]
        if not vr.ok:
            failed.append(f"{index}: schema {vr.errors[0]}")
        if scan_banned(text) or scan_phi(text):
            failed.append(f"{index}: safety")

        out = OUT / f"{case['case_id']}.json"
        out.write_text(json.dumps(case, indent=2), encoding="utf-8")
        neighbours.append(neighbour_summary(case))
        if len(neighbours) > 15:
            neighbours.pop(0)
        print(f"OK {case['case_id']} letter={len(case['denial_letter_text'].split())}w ctx={len(case['clinical_context'].split())}w")

    for p in sorted(LEGACY.glob("case_*.json")):
        if p.name.startswith("case_0") or p.name.startswith("case_1"):
            num = p.stem.split("_")[1]
            if num.isdigit() and int(num) <= 10:
                _patch_legacy(p)
                print(f"patched legacy {p.name}")

    print(f"done. failures={len(failed)}")
    for f in failed[:20]:
        print(" ", f)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
