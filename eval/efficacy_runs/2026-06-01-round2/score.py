"""Round-2 efficacy run — train-signal scoring + honest-ceiling gate.

Round 2 baseline is the currently-promoted drafter_v2. We score v2 on the FULL
11-case train split (case_*), pick the weakest *promptable* dimension via
efficacy_io.weakest_promptable_dimension, and apply the pre-registered honest gate:
if that dimension is already at the offline ceiling (mean anchor >= 4.8), there is
no promptable offline headroom — we record the finding and do NOT manufacture a v3.
(Only `grounding` is sub-ceiling, and it is corpus-bound — no prompt edit moves it.)

Run from backend/:
  env UV_CACHE_DIR=/tmp/uv-cache uv run python ../eval/efficacy_runs/2026-06-01-round2/score.py
"""
from __future__ import annotations

import json
from pathlib import Path

from app.learning.efficacy_io import (
    CORPUS_BOUND_DIMENSIONS, score_split, weakest_promptable_dimension,
)

RUN = Path(__file__).resolve().parent
CEILING_ANCHOR = 4.8  # pre-registered: a promptable dim at/above this has no offline headroom


def main() -> None:
    manifest = json.loads((RUN / "inputs" / "manifest.json").read_text())
    train = manifest["train"]
    v2 = score_split(RUN, "v2", train)
    means = v2["dimension_means"]
    target = weakest_promptable_dimension(means)
    at_ceiling = means[target] >= CEILING_ANCHOR

    result = {
        "round": 2,
        "baseline_version": "v2",
        "split_scored": "train (full 11-case case_* split — 2.75x Run #1's 4 train cases)",
        "train_composite": v2["composite"],
        "per_dimension_means": means,
        "hard_gate_pass": v2["hard_gate_pass"],
        "weakest_promptable_dimension": target,
        "weakest_promptable_mean": means[target],
        "ceiling_anchor": CEILING_ANCHOR,
        "corpus_bound_dimensions": sorted(CORPUS_BOUND_DIMENSIONS),
        "offline_ceiling_reached": at_ceiling,
        "decision": "no_promotion" if at_ceiling else "optimize",
        "reason": (
            "No promptable offline headroom: every prompt-movable dimension is at the "
            "offline ceiling on the full 11-case train signal (weakest promptable = "
            f"{target} @ {means[target]} >= {CEILING_ANCHOR}). The only sub-ceiling "
            f"dimension is grounding @ {means['grounding']}, which is corpus-bound "
            "(no retrieved citations in offline runs) and cannot be moved by a prompt "
            "edit. Remaining gains require live corpus retrieval (Tier 1) or harder "
            "cases. drafter_v2 stays active; no v3 manufactured (honest-result clause)."
            if at_ceiling else
            f"Promptable headroom found on {target} @ {means[target]}; proceed to reflect -> v3."
        ),
    }
    (RUN / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
