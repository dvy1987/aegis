#!/usr/bin/env python3
"""Generate one batch (10 cases) of manual synthetic cases — no Vertex Gemini.

Usage:
  cd backend && uv run python scripts/run_manual_case_batch.py --batch 1
  cd backend && uv run python scripts/run_manual_case_batch.py --batch 1 --dry-run
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "eval" / "cases" / "drafts" / "benchmark-200"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.case_generator import config  # noqa: E402
from app.case_generator.manual_assemble import new_run_id  # noqa: E402
from app.case_generator.manual_batches.manual_producer import (  # noqa: E402
    neighbour_summary,
    run_manual_pipeline,
)
from app.case_generator.manual_batches.matrix_planner import (  # noqa: E402
    BATCH_SIZE,
    CASE_COUNT,
    cells_for_batch,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, required=True, help="Batch 1–20")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--seed", type=int, default=20260601)
    args = parser.parse_args()
    max_batch = CASE_COUNT // BATCH_SIZE
    if not 1 <= args.batch <= max_batch:
        print(f"--batch must be 1..{max_batch}", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = new_run_id(args.batch)
    items = cells_for_batch(args.batch, seed=args.seed)
    rng = random.Random(args.seed + args.batch)
    neighbours: list[str] = []
    written = 0
    print(f"run_id={run_id} batch={args.batch} cases={len(items)}")

    for index, cell in items:
        patterns = config.sample_denial_patterns(rng, cell["insurer"], cell["specialty"])
        try:
            case = run_manual_pipeline(
                index=index,
                cell=cell,
                patterns=patterns,
                run_id=run_id,
                neighbour_summaries=neighbours,
            )
        except ValueError as exc:
            print(f"[{index}] FAILED: {exc}")
            continue
        neighbours.append(neighbour_summary(case))
        out_path = OUT_DIR / f"{case['case_id']}.json"
        if args.dry_run:
            print(f"[{index}] {case['case_id']} OK dry-run")
        else:
            out_path.write_text(json.dumps(case, indent=2), encoding="utf-8")
            print(f"[{index}] wrote {out_path.relative_to(REPO)}")
            written += 1

    print(f"done batch={args.batch} written={written}/{len(items)}")
    return 0 if written == len(items) or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
