"""CLI entrypoint for synthetic case generation (default: A+ pipeline).

Examples:
  cd backend && uv run python -m app.case_generator.cli --count 1 --dry-run
  cd backend && uv run python -m app.case_generator.cli --count 10

Legacy Vertex/Gemini swarm: ``old_pipeline.py`` + ``old_agents.py`` (not used by default).
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from pathlib import Path

from .aplus.pipeline import build_aplus_case
from .config import REPO_ROOT, sample_matrix_cell

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
    p.add_argument(
        "--no-web-research",
        action="store_true",
        help="Use catalog-only denial_letter_references (skip web-research cache).",
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


def _new_run_id() -> str:
    from datetime import UTC, datetime
    import uuid

    return f"aplus-cli-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:5]}"


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
    run_id = _new_run_id()
    print(
        f"run_id={run_id} out_dir={out_dir} start_index={start_index} "
        f"count={args.count} [A+ default]"
    )

    accepted_cells: set[tuple[str, ...]] = set()
    neighbour_summaries: list[str] = []
    written = 0
    seed = args.seed if args.seed is not None else 20260601

    for i in range(args.count):
        idx = start_index + i
        cell = sample_matrix_cell(rng, forbid_cells=accepted_cells)
        try:
            case = build_aplus_case(
                index=idx,
                cell=cell,
                run_id=run_id,
                neighbour_summaries=neighbour_summaries,
                seed=seed,
                use_web_research=not args.no_web_research,
            )
        except Exception as exc:
            print(f"[{idx}] FAILED: {exc}")
            continue

        accepted_cells.add(
            (
                cell["insurer"],
                cell["denial_type"],
                cell["specialty"],
                cell["sub_tactic"],
            )
        )
        neighbour_summaries.append(
            f"- [{cell['insurer']} / {cell['denial_type']} / {cell['specialty']} / "
            f"{cell['sub_tactic']}] dx={case['patient_profile']['diagnosis']}; "
            f"tx={case['patient_profile']['treatment_requested']}"
        )
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
