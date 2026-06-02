#!/usr/bin/env python3
"""Generate case_421–case_500 (80 cases) via A+ pipeline — 500-case corpus target.

Uses default build_aplus_case: web-research cache refs, claim-file / P2P letter enhancements.

Prerequisite: eval/references/web-research-cache-2026-06-02.json

Usage:
  cd backend && uv run python scripts/generate_cases_421_500.py
  cd backend && uv run python scripts/generate_cases_421_500.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "eval" / "cases" / "drafts"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.case_generator.aplus.pipeline import build_aplus_case  # noqa: E402
from app.case_generator.aplus.text_metrics import context_words_ok, letter_words_ok  # noqa: E402
from app.case_generator.manual_assemble import new_run_id  # noqa: E402
from app.case_generator.manual_batches.matrix_planner import (  # noqa: E402
    EXTENSION2_FIRST_INDEX,
    planned_cells_extension2,
)
from app.case_generator.manual_batches.neighbour import neighbour_summary  # noqa: E402
from app.case_generator.safety import scan_banned, scan_phi  # noqa: E402
from app.case_generator.validator import validate_case  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--seed", type=int, default=20260604)
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    cells = planned_cells_extension2(seed=args.seed)
    run_id = new_run_id(50).replace("manual-b50", "aplus-ext2-500")
    neighbours: list[str] = []
    failed: list[str] = []
    written = 0

    print(
        f"run_id={run_id} generating case_{EXTENSION2_FIRST_INDEX}.."
        f"{EXTENSION2_FIRST_INDEX + len(cells) - 1} "
        f"(A+ pipeline, web_research=True)"
    )

    for offset, cell in enumerate(cells):
        index = EXTENSION2_FIRST_INDEX + offset
        existing = list(OUT.glob(f"case_{index}_*.json"))
        if existing and not args.dry_run:
            print(f"SKIP {index}: already exists {existing[0].name}")
            continue

        try:
            case = build_aplus_case(
                index=index,
                cell=cell,
                run_id=run_id,
                neighbour_summaries=neighbours,
                seed=args.seed,
                use_web_research=True,
            )
        except Exception as exc:
            failed.append(f"{index}: build {exc}")
            print(f"[{index}] FAILED: {exc}")
            continue

        letter = case["denial_letter_text"]
        if not letter_words_ok(letter):
            failed.append(f"{index}: letter words={len(letter.split())}")
        if not context_words_ok(case["clinical_context"]):
            failed.append(f"{index}: context words")

        vr = validate_case(case)
        text = letter + "\n" + case["clinical_context"]
        if not vr.ok:
            failed.append(f"{index}: schema {vr.errors[0]}")
        if scan_banned(text) or scan_phi(text):
            failed.append(f"{index}: safety")

        refs = case.get("denial_letter_references") or []
        web_n = sum(1 for r in refs if "Web research" in r.get("relevance", ""))
        if len(refs) < 5 or web_n < 1:
            failed.append(f"{index}: refs={len(refs)} web={web_n}")

        if "claim file" not in letter.lower():
            failed.append(f"{index}: missing claim-file block")

        neighbours.append(neighbour_summary(case))
        if len(neighbours) > 12:
            neighbours.pop(0)

        if args.dry_run:
            print(
                f"[{index}] {case['case_id']} OK dry-run refs={len(refs)} web={web_n} "
                f"letter={len(letter.split())}w"
            )
            continue

        out = OUT / f"{case['case_id']}.json"
        out.write_text(json.dumps(case, indent=2), encoding="utf-8")
        written += 1
        print(
            f"OK {case['case_id']} refs={len(refs)} web={web_n} "
            f"letter={len(letter.split())}w "
            f"ctx={len(case['clinical_context'].split())}w"
        )

    print(f"done. written={written}/{len(cells)} failures={len(failed)}")
    for f in failed[:15]:
        print(" ", f)
    return 1 if failed and not args.dry_run else 0


if __name__ == "__main__":
    raise SystemExit(main())
