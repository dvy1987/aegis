"""Round-2 efficacy run — input prep (full 10/10 split, firewall enforcement).

Emits firewall-clean student packets + teacher answer-key packets for ALL cases
(train = case_*, held-out = test_case_*) via app.learning.efficacy_io.build_run_inputs.
Run from backend/:
  env UV_CACHE_DIR=/tmp/uv-cache uv run python ../eval/efficacy_runs/2026-06-01-round2/prep.py
"""
from __future__ import annotations

import json
from pathlib import Path

from app.learning.efficacy_io import build_run_inputs

RUN_DIR = Path(__file__).resolve().parent
REPO = RUN_DIR.parents[2]
CASES = REPO / "eval" / "cases" / "drafts"
TRAIN = [p.stem for p in sorted(CASES.glob("case_*.json"))]
HOLDOUT = [p.stem for p in sorted(CASES.glob("test_case_*.json"))]


def main() -> None:
    build_run_inputs(TRAIN + HOLDOUT, cases_dir=CASES, out_dir=RUN_DIR)
    (RUN_DIR / "inputs" / "manifest.json").write_text(
        json.dumps({"train": TRAIN, "holdout": HOLDOUT}, indent=2), encoding="utf-8")
    print(f"train={len(TRAIN)} holdout={len(HOLDOUT)}")


if __name__ == "__main__":
    main()
