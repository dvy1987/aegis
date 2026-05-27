"""CLI entrypoint for the Aegis synthetic case generation swarm.

Examples:
  uv run python -m app.case_generator.cli --count 1 --split train --dry-run
  uv run python -m app.case_generator.cli --count 10 --split test
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from pathlib import Path

from . import pipeline
from .config import REPO_ROOT

DEFAULT_OUT = REPO_ROOT / "eval" / "cases" / "drafts" / "part-a"


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="case_generator", description=__doc__)
    p.add_argument("--count", type=int, default=1, help="Number of cases to generate.")
    p.add_argument(
        "--split",
        choices=["train", "test"],
        default="test",
        help="Target split under eval/cases/drafts/part-a/.",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Override output directory. Defaults to eval/cases/drafts/part-a/<split>/.",
    )
    p.add_argument(
        "--seed", type=int, default=None, help="Optional RNG seed for reproducibility."
    )
    p.add_argument(
        "--start-index",
        type=int,
        default=None,
        help="Index to start case_NN filenames at. Defaults to next free slot in --out-dir.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate but do not write to disk; print case IDs and stage verdicts.",
    )
    p.add_argument("-v", "--verbose", action="count", default=0)
    return p


def _next_free_index(out_dir: Path) -> int:
    if not out_dir.exists():
        return 1
    nums = [
        int(p.name.split("_", 2)[1])
        for p in out_dir.glob("case_*.json")
        if p.name.split("_", 2)[1].isdigit()
    ]
    return (max(nums) + 1) if nums else 1


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose == 0 else logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )
    out_dir = args.out_dir or (DEFAULT_OUT / args.split)
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
    start_index = (
        args.start_index if args.start_index is not None else _next_free_index(out_dir)
    )
    rng = random.Random(args.seed)
    run_id = pipeline.new_run_id()
    print(
        f"run_id={run_id} out_dir={out_dir} start_index={start_index} count={args.count}"
    )

    accepted_cells: set[tuple[str, ...]] = set()
    neighbour_summaries: list[str] = []
    written = 0
    for i in range(args.count):
        idx = start_index + i
        case = pipeline.generate_one_case(
            index=idx,
            rng=rng,
            accepted_cells=accepted_cells,
            neighbour_summaries=neighbour_summaries,
            run_id=run_id,
        )
        if case is None:
            print(f"[{idx}] SKIPPED (retries exhausted)")
            continue
        if args.dry_run:
            print(f"[{idx}] {case['case_id']} OK (dry-run, not written)")
            print(json.dumps(case, indent=2)[:1200] + "...")
        else:
            out_path = out_dir / f"{case['case_id']}.json"
            out_path.write_text(json.dumps(case, indent=2), encoding="utf-8")
            print(f"[{idx}] wrote {out_path.relative_to(REPO_ROOT)}")
            written += 1

    print(f"done. written={written} / requested={args.count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
