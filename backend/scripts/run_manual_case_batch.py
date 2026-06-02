#!/usr/bin/env python3
"""Generate synthetic cases (default: A+ pipeline, ERISA-style denial letters).

Usage:
  cd backend && uv run python scripts/run_manual_case_batch.py --batch 1
  cd backend && uv run python scripts/run_manual_case_batch.py --batch 1 --dry-run

Legacy (old letter format): ``old_run_manual_case_batch.py``
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "eval" / "cases" / "drafts"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.case_generator.aplus.pipeline import build_aplus_case  # noqa: E402
from app.case_generator.aplus.text_metrics import context_words_ok, letter_words_ok  # noqa: E402
from app.case_generator.manual_assemble import new_run_id  # noqa: E402
from app.case_generator.manual_batches.matrix_planner import (  # noqa: E402
    BATCH_SIZE,
    CASE_COUNT,
    cells_for_batch,
)
from app.case_generator.manual_batches.neighbour import neighbour_summary  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=int, required=True, help="Batch 1–20")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--seed", type=int, default=20260601)
    args = parser.parse_args()
    max_batch = CASE_COUNT // BATCH_SIZE
    if not 1 <= args.batch <= max_batch:
        print(f"--batch must be 1..{max_batch}", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = new_run_id(args.batch).replace("manual-b", "aplus-b")
    items = cells_for_batch(args.batch, seed=args.seed)
    neighbours: list[str] = []
    written = 0
    failed: list[str] = []
    print(f"run_id={run_id} batch={args.batch} cases={len(items)} [A+ default]")

    for index, cell in items:
        try:
            case = build_aplus_case(
                index=index,
                cell=cell,
                run_id=run_id,
                neighbour_summaries=neighbours,
                seed=args.seed,
            )
        except Exception as exc:
            failed.append(f"{index}: {exc}")
            print(f"[{index}] FAILED: {exc}")
            continue

        if not letter_words_ok(case["denial_letter_text"]):
            failed.append(f"{index}: letter word count")
        if not context_words_ok(case["clinical_context"]):
            failed.append(f"{index}: context word count")

        neighbours.append(neighbour_summary(case))
        if len(neighbours) > 12:
            neighbours.pop(0)

        out_path = OUT_DIR / f"{case['case_id']}.json"
        if args.dry_run:
            print(f"[{index}] {case['case_id']} OK dry-run")
        else:
            out_path.write_text(json.dumps(case, indent=2), encoding="utf-8")
            print(f"[{index}] wrote {out_path.relative_to(REPO)}")
            written += 1

    print(f"done batch={args.batch} written={written}/{len(items)}")
    if failed:
        print("failures:", *failed[:5], sep="\n  ")
    return 0 if written == len(items) or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
