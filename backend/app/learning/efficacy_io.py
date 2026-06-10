"""Reusable I/O + scoring for assistant-orchestrated efficacy runs (the codified
Session-24 Phase-2 logic). Pure functions over a run directory of captured JSON —
no orchestration, no LLM, no cloud. Shared by the eval scripts, round-2+ runs, and
(later) the live efficacy harness."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.learning.models import DIMENSIONS, composite_score, normalize_dimension_scores

# Dimensions with no offline prompt lever (need retrieved corpus/citations) — excluded
# when choosing a reflection target so the loop spends reflection where it can actually climb.
CORPUS_BOUND_DIMENSIONS = frozenset({"grounding"})
DIFF_TOKEN_CAP = 200


def load_judgment(run_dir: Path, version: str, case_id: str) -> dict[str, Any]:
    return json.loads((run_dir / "judgments" / version / f"judge_{case_id}.json").read_text(encoding="utf-8"))


def score_split(run_dir: Path, version: str, case_ids: list[str]) -> dict[str, Any]:
    judgments = {c: load_judgment(run_dir, version, c) for c in case_ids}
    per_case = {c: composite_score(j["dimension_scores"], j["hard_gate_pass"]) for c, j in judgments.items()}
    mean = round(sum(per_case.values()) / len(per_case), 4) if per_case else 0.0
    dim_means = (
        {
            d: round(
                sum(
                    normalize_dimension_scores(judgments[c]["dimension_scores"]).get(d, 1)
                    for c in case_ids
                )
                / len(case_ids),
                3,
            )
            for d in DIMENSIONS
        }
        if case_ids
        else {d: 0.0 for d in DIMENSIONS}
    )
    return {"composite": mean, "per_case": per_case, "dimension_means": dim_means,
            "hard_gate_pass": {c: judgments[c]["hard_gate_pass"] for c in case_ids}}


def weakest_promptable_dimension(dimension_means: dict[str, float]) -> str:
    """The lowest-scoring dimension that a prompt change can actually move (excludes
    corpus-bound dims). Ties broken by DIMENSIONS order for determinism."""
    promptable = [d for d in DIMENSIONS if d not in CORPUS_BOUND_DIMENSIONS]
    return min(promptable, key=lambda d: (dimension_means.get(d, 1.0), DIMENSIONS.index(d)))


def lift_report(run_dir: Path, *, holdout_ids: list[str], baseline_version: str,
                candidate_version: str, diff_added_tokens: int, target_dimension: str,
                diff_token_cap: int = DIFF_TOKEN_CAP) -> dict[str, Any]:
    before = score_split(run_dir, baseline_version, holdout_ids)
    after = score_split(run_dir, candidate_version, holdout_ids)
    lift = round(after["composite"] - before["composite"], 4)
    rel = round(100 * lift / before["composite"], 1) if before["composite"] else None
    deltas = {d: round(after["dimension_means"][d] - before["dimension_means"][d], 3) for d in DIMENSIONS}

    vetoes: list[str] = []
    if after["composite"] < before["composite"]:
        vetoes.append("held_out_regression")
    if not all(after["hard_gate_pass"].values()):
        vetoes.append("safety_or_hard_gate_regression")
    if diff_added_tokens > diff_token_cap:
        vetoes.append("diff_too_large")

    return {
        "dataset_split": "holdout (V2-INV-3 — reflection never saw these)",
        "target_dimension": target_dimension,
        "baseline_composite": before["composite"], "optimized_composite": after["composite"],
        "lift_absolute": lift, "lift_relative_pct": rel,
        "per_dimension_means_baseline": before["dimension_means"],
        "per_dimension_means_candidate": after["dimension_means"],
        "per_dimension_deltas": deltas,
        "per_case": {c: {"baseline": before["per_case"][c], "candidate": after["per_case"][c]} for c in holdout_ids},
        "diff_added_tokens": diff_added_tokens,
        "vetoes": vetoes, "promotable": (not vetoes) and lift > 0,
    }


def build_run_inputs(case_ids: list[str], *, cases_dir: Path, out_dir: Path) -> dict[str, Any]:
    """Emit firewall-clean student packets + teacher packets for a run (reuses the
    production builders, so synthetic_provenance never enters a student packet)."""
    from app.evals.part_a.teacher_packet import (
        build_student_case_packet, build_teacher_grading_packet, load_case,
    )
    inputs = out_dir / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    forbidden = ("exploitable_weaknesses", "expected_appeal_vectors", "appeal_difficulty",
                 "synthetic_provenance", "strong_defenses")
    for cid in case_ids:
        case = load_case(cases_dir / f"{cid}.json")
        student = build_student_case_packet(case)
        blob = student.model_dump_json()
        for f in forbidden:
            if f in blob:
                raise AssertionError(f"firewall breach: {f} in student_{cid}")
        (inputs / f"student_{cid}.json").write_text(student.model_dump_json(indent=2), encoding="utf-8")
        (inputs / f"teacher_{cid}.json").write_text(
            build_teacher_grading_packet(case).model_dump_json(indent=2), encoding="utf-8")
    return {"count": len(case_ids), "inputs_dir": str(inputs)}
