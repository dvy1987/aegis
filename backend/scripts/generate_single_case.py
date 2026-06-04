#!/usr/bin/env python3
"""CLI command to faithfully generate a single synthetic case using the complete pipeline.

Usage:
  cd backend && uv run python scripts/generate_single_case.py --index 102
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRATCH_DIR = REPO / "scratch"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.case_generator import llm_pipeline

def main() -> int:
    parser = argparse.ArgumentParser(description="Faithfully execute the llm_pipeline.py case generation.")
    parser.add_argument("--index", type=int, required=True, help="The case index (e.g., 102)")
    parser.add_argument("--seed", type=int, default=20260604)
    args = parser.parse_args()

    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    run_id = llm_pipeline.new_run_id()
    rng = random.Random(args.seed + args.index)
    
    print(f"Executing generation pipeline for case {args.index}...", file=sys.stderr)
    print("This runs the strict llm_pipeline.py code, including all P-stages and C-stages, the true 10-critic Final Panel, and the determinisic+LLM Final Flaw Integrity Check.", file=sys.stderr)
    
    accepted_cells: set[tuple[str, ...]] = set()
    neighbour_summaries: list[str] = []
    
    case = llm_pipeline.generate_one_case(
        index=args.index,
        rng=rng,
        accepted_cells=accepted_cells,
        neighbour_summaries=neighbour_summaries,
        run_id=run_id
    )
    
    if not case:
        print(f"Failed to generate case {args.index} after exhausting retries.", file=sys.stderr)
        return 1
        
    out_path = SCRATCH_DIR / f"case_{args.index}_auto.json"
    out_path.write_text(json.dumps(case, indent=2), encoding="utf-8")
    
    print(f"\nSUCCESS: Case {args.index} generated fully by code.", file=sys.stderr)
    print(f"Saved to: {out_path.relative_to(REPO)}", file=sys.stderr)
    
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
