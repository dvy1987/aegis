"""Reflection meta-prompt A/B — held-out lift comparison.

Holds the optimizer task fixed (reflect drafter_v1 on appeal_vector_capture, same
laundered signal, same 4-case held-out slice as Run #1) and compares two candidate
prompts produced by two meta-prompt variants:
  - base           = drafter_v2 (the base-meta-prompt reflection, from Run #1)
  - critique_plus  = a minimal single-flaw edit produced by the critique_plus variant

Quality is measured by held-out composite lift vs the v1 baseline (0.73); we also
report the diff size (added body words), since critique_plus is designed for minimal
edits. Run from backend/:
  env UV_CACHE_DIR=/tmp/uv-cache uv run python ../eval/efficacy_runs/2026-06-01-metaprompt-ab/score_ab.py
"""
from __future__ import annotations

import json
from pathlib import Path

from app.learning.models import DIMENSIONS, composite_score

AB = Path(__file__).resolve().parent
RUN1 = AB.parent / "2026-05-31"
HOLDOUT = ["test_case_01_uhc_mednec", "test_case_02_aetna_priorauth",
           "test_case_03_cigna_mednec", "test_case_04_uhc_priorauth"]


def mean_composite(judg_dir: Path, fname=lambda c: f"judge_{c}.json") -> float:
    vals = []
    for c in HOLDOUT:
        j = json.loads((judg_dir / fname(c)).read_text())
        vals.append(composite_score(j["dimension_scores"], j["hard_gate_pass"]))
    return round(sum(vals) / len(vals), 4)


def dim_means(judg_dir: Path, fname=lambda c: f"judge_{c}.json") -> dict[str, float]:
    return {d: round(sum(json.loads((judg_dir / fname(c)).read_text())["dimension_scores"].get(d, 1)
                         for c in HOLDOUT) / len(HOLDOUT), 3) for d in DIMENSIONS}


def main() -> None:
    base_v1 = mean_composite(RUN1 / "judgments" / "v1")
    cand_base = mean_composite(RUN1 / "judgments" / "v2")
    cand_cp = mean_composite(AB / "critique_plus" / "judgments")

    # added body words vs drafter_v1 (the token proxy used in Run #1).
    def body_words(p: Path) -> int:
        return len(" ".join(p.read_text().splitlines()[2:]).split())
    v1_words = body_words(AB.parents[2] / "backend/app/aegis_v1/prompts/drafter_v1.md")
    base_words = body_words(AB / "base" / "candidate_prompt.md") - v1_words
    cp_words = body_words(AB / "critique_plus" / "candidate_prompt.md") - v1_words

    result = {
        "task": "reflect drafter_v1 on appeal_vector_capture (held-out = 4 test_case_*, same as Run #1)",
        "baseline_v1_composite": base_v1,
        "candidates": {
            "base": {"held_out_composite": cand_base, "lift_absolute": round(cand_base - base_v1, 4),
                     "lift_relative_pct": round(100 * (cand_base - base_v1) / base_v1, 1),
                     "added_body_words": base_words, "dimension_means": dim_means(RUN1 / "judgments" / "v2")},
            "critique_plus": {"held_out_composite": cand_cp, "lift_absolute": round(cand_cp - base_v1, 4),
                              "lift_relative_pct": round(100 * (cand_cp - base_v1) / base_v1, 1),
                              "added_body_words": cp_words,
                              "dimension_means": dim_means(AB / "critique_plus" / "judgments")},
        },
        "quality_winner": "base" if cand_base > cand_cp else ("critique_plus" if cand_cp > cand_base else "tie"),
        "quality_delta": round(cand_base - cand_cp, 4),
    }
    (AB / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
