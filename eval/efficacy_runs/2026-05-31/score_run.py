"""Phase-2 efficacy run — scoring + gate (held-out lift).

Reads the v1 (baseline) and v2 (candidate) judgments, computes the official
composite via app.learning.models.composite_score (through the reusable
app.learning.efficacy_io helpers), measures held-out lift (test_case_* only —
V2-INV-3), applies the promotion veto gates, and writes result.json. Run from
backend/:
  env UV_CACHE_DIR=/tmp/uv-cache uv run python ../eval/efficacy_runs/2026-05-31/score_run.py
"""
from __future__ import annotations

import json
from pathlib import Path

from app.learning.efficacy_io import score_split
from app.learning.models import DIMENSIONS

RUN = Path(__file__).resolve().parent
HOLDOUT = ["test_case_01_uhc_mednec", "test_case_02_aetna_priorauth",
           "test_case_03_cigna_mednec", "test_case_04_uhc_priorauth"]
DIFF_ADDED_TOKENS = 131  # words added v1->v2 (see reflections/, < 200-token focused-diff cap)


def main() -> None:
    before = score_split(RUN, "v1", HOLDOUT)
    after = score_split(RUN, "v2", HOLDOUT)
    lift = round(after["composite"] - before["composite"], 4)
    rel = round(100 * lift / before["composite"], 1) if before["composite"] else None
    deltas = {d: round(after["dimension_means"][d] - before["dimension_means"][d], 3) for d in DIMENSIONS}

    # promotion veto gates (faithful application; diff measured as the DIFF, not total body)
    vetoes = []
    if after["composite"] < before["composite"]:
        vetoes.append("held_out_regression")
    if not all(after["hard_gate_pass"].values()):
        vetoes.append("safety_or_hard_gate_regression")
    if DIFF_ADDED_TOKENS > 200:
        vetoes.append("diff_too_large")

    result = {
        "slice": "all_holdout(uhc/aetna/cigna x mednec/priorauth)",
        "dataset_split": "holdout (test_case_*) — reflection never saw these (V2-INV-3)",
        "target_dimension": "appeal_vector_capture",
        "baseline_composite": before["composite"],
        "optimized_composite": after["composite"],
        "lift_absolute": lift,
        "lift_relative_pct": rel,
        "per_dimension_means_v1": before["dimension_means"],
        "per_dimension_means_v2": after["dimension_means"],
        "per_dimension_deltas": deltas,
        "per_case": {cid: {"v1": before["per_case"][cid], "v2": after["per_case"][cid]} for cid in HOLDOUT},
        "diff_added_tokens": DIFF_ADDED_TOKENS,
        "vetoes": vetoes,
        "promotable": (not vetoes) and lift > 0,
    }
    (RUN / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
