"""CLI entrypoint for synthetic case generation (LLM Gemini producer→critic swarm).

Examples:
  cd backend && uv run python -m app.case_generator.cli --count 1 --dry-run
  cd backend && uv run python -m app.case_generator.cli --count 10

Requires Vertex/Gemini credentials (AEGIS_CASEGEN_MODEL, ADC). The swarm samples a matrix
cell, grounds on the curated clinical KB, drafts via P1–P5, and gates each case with the
critic panel + flaw-injection verifier before writing.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from pathlib import Path

from .config import REPO_ROOT
from .llm_pipeline import generate_one_case, new_run_id

DEFAULT_OUT = REPO_ROOT / "eval" / "cases" / "drafts"


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="case_generator", description=__doc__)
    p.add_argument("--count", type=int, default=1, help="Number of cases to generate.")
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: eval/cases/drafts/).",
    )
    p.add_argument(
        "--seed", type=int, default=None, help="Optional RNG seed for reproducibility."
    )
    p.add_argument(
        "--start-index",
        type=int,
        default=None,
        help="Index for case_NN filenames. Defaults to next free slot in --out-dir.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate but do not write to disk.",
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
    return max(nums, default=0) + 1


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose == 0 else logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )
    out_dir = args.out_dir or DEFAULT_OUT
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
    start_index = (
        args.start_index if args.start_index is not None else _next_free_index(out_dir)
    )
    rng = random.Random(args.seed)
    run_id = new_run_id()
    print(
        f"run_id={run_id} out_dir={out_dir} start_index={start_index} "
        f"count={args.count} [LLM swarm]"
    )

    accepted_cells: set[tuple[str, ...]] = set()
    neighbour_summaries: list[str] = []
    written = 0

    for i in range(args.count):
        idx = start_index + i
        try:
            # generate_one_case samples the cell, runs the swarm, and updates
            # accepted_cells / neighbour_summaries in place.
            case = generate_one_case(
                index=idx,
                rng=rng,
                accepted_cells=accepted_cells,
                neighbour_summaries=neighbour_summaries,
                run_id=run_id,
            )
        except Exception as exc:
            print(f"[{idx}] FAILED: {exc}")
            continue

        if case is None:
            print(f"[{idx}] discarded (exhausted scenario retries)")
            continue
        if len(neighbour_summaries) > 12:
            neighbour_summaries.pop(0)

        if args.dry_run:
            print(f"[{idx}] {case['case_id']} OK (dry-run)")
        else:
            out_path = out_dir / f"{case['case_id']}.json"
            out_path.write_text(json.dumps(case, indent=2), encoding="utf-8")
            print(f"[{idx}] wrote {out_path.relative_to(REPO_ROOT)}")
            written += 1

    print(f"done. written={written} / requested={args.count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
