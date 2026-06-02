"""Round-2 efficacy run — input prep (interim 10/10 ID split, firewall enforcement).

**Note:** Production workflow keeps all cases in flat ``drafts/`` until Gumloop →
``approved/``; train/holdout folders come later. This script uses ``case_01``–``10``
vs ``case_11``–``20`` only for the frozen 2026-06-01 efficacy experiment.

Run from backend/:
  env UV_CACHE_DIR=/tmp/uv-cache uv run python ../eval/efficacy_runs/2026-06-01-round2/prep.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from app.learning.efficacy_io import build_run_inputs

RUN_DIR = Path(__file__).resolve().parent
REPO = RUN_DIR.parents[2]
CASES = REPO / "eval" / "cases" / "drafts"


def _num(stem: str) -> int:
    m = re.match(r"case_(\d+)_", stem)
    return int(m.group(1)) if m else -1


_stems = sorted((p.stem for p in CASES.glob("case_*.json")), key=_num)
TRAIN = [s for s in _stems if 1 <= _num(s) <= 10]
HOLDOUT = [s for s in _stems if 11 <= _num(s) <= 20]


def main() -> None:
    build_run_inputs(TRAIN + HOLDOUT, cases_dir=CASES, out_dir=RUN_DIR)
    (RUN_DIR / "inputs" / "manifest.json").write_text(
        json.dumps({"train": TRAIN, "holdout": HOLDOUT}, indent=2), encoding="utf-8")
    print(f"train={len(TRAIN)} holdout={len(HOLDOUT)}")


if __name__ == "__main__":
    main()
