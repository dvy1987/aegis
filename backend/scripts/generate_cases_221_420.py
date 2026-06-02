#!/usr/bin/env python3
"""Generate case_221–case_420 (200 cases) via A+ pipeline with web-researched references.

Prerequisite: eval/references/web-research-cache-2026-06-02.json (agent web search catalog).

Usage:
  cd backend && uv run python scripts/generate_cases_221_420.py
  cd backend && uv run python scripts/generate_cases_221_420.py --dry-run
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
    EXTENSION_FIRST_INDEX,
    planned_cells_extension,
)
from app.case_generator.manual_batches.neighbour import neighbour_summary  # noqa: E402
from app.case_generator.safety import scan_banned, scan_phi  # noqa: E402
from app.case_generator.validator import validate_case  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--seed", type=int, default=20260603)
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    cells = planned_cells_extension(seed=args.seed)
    run_id = new_run_id(42).replace("manual-b42", "aplus-web-ext")
    neighbours: list[str] = []
    failed: list[str] = []
    written = 0

    print(
        f"run_id={run_id} generating case_{EXTENSION_FIRST_INDEX}.."
        f"{EXTENSION_FIRST_INDEX + len(cells) - 1} web_research=True"
    )

    for offset, cell in enumerate(cells):
        index = EXTENSION_FIRST_INDEX + offset
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

        if not letter_words_ok(case["denial_letter_text"]):
            failed.append(f"{index}: letter words")
        if not context_words_ok(case["clinical_context"]):
            failed.append(f"{index}: context words")

        vr = validate_case(case)
        text = case["denial_letter_text"] + "\n" + case["clinical_context"]
        if not vr.ok:
            failed.append(f"{index}: schema {vr.errors[0]}")
        if scan_banned(text) or scan_phi(text):
            failed.append(f"{index}: safety")

        refs = case.get("denial_letter_references") or []
        if len(refs) < 5:
            failed.append(f"{index}: expected web+catalog refs, got {len(refs)}")

        neighbours.append(neighbour_summary(case))
        if len(neighbours) > 12:
            neighbours.pop(0)

        if args.dry_run:
            print(
                f"[{index}] {case['case_id']} OK dry-run refs={len(refs)} "
                f"letter={len(case['denial_letter_text'].split())}w"
            )
            continue

        out = OUT / f"{case['case_id']}.json"
        out.write_text(json.dumps(case, indent=2), encoding="utf-8")
        written += 1
        print(
            f"OK {case['case_id']} refs={len(refs)} "
            f"letter={len(case['denial_letter_text'].split())}w "
            f"ctx={len(case['clinical_context'].split())}w"
        )

    print(f"done. written={written}/{len(cells)} failures={len(failed)}")
    for f in failed[:15]:
        print(" ", f)
    return 1 if failed and not args.dry_run else 0


if __name__ == "__main__":
    raise SystemExit(main())
