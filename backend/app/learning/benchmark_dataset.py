"""Benchmark case loader with deterministic 60/40 train/holdout split (FR-4)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

SplitName = Literal["benchmark_train", "benchmark_holdout"]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DRAFTS_DIR = _REPO_ROOT / "eval" / "cases" / "drafts"
_TRAIN_RATIO = 0.6


def _sorted_case_paths(limit: int | None = None) -> list[Path]:
    paths = sorted(_DRAFTS_DIR.glob("case_*.json"))
    if limit is not None:
        paths = paths[:limit]
    return paths


def load_benchmark_cases(
    split: SplitName,
    *,
    limit: int | None = 100,
) -> list[dict[str, Any]]:
    """Load cases assigned to train (first 60%) or holdout (last 40%) by sorted id."""
    paths = _sorted_case_paths(limit=limit)
    if not paths:
        return []
    cut = int(len(paths) * _TRAIN_RATIO)
    if split == "benchmark_train":
        chosen = paths[:cut]
    else:
        chosen = paths[cut:]
    cases: list[dict[str, Any]] = []
    for path in chosen:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["dataset_split"] = split
        cases.append(data)
    return cases


def micro_benchmark_fixture() -> list[dict[str, Any]]:
    """Four-case offline fixture for unit tests (no filesystem dependency)."""
    base = {
        "insurer": "Cigna",
        "denial_type": "medical_necessity",
        "denial_letter_text": "Denied as not medically necessary.",
        "clinical_context": "Failed two prior treatments.",
        "patient_profile": {"plan_funding_type": "fully_insured"},
        "denial_pattern_sources": [],
    }
    return [
        {
            **base,
            "case_id": "micro_h1",
            "dataset_split": "benchmark_holdout",
            "base": {"appeal_vector_capture": 1, "grounding": 3, "case_specific_clinical_rebuttal": 3},
        },
        {
            **base,
            "case_id": "micro_h2",
            "dataset_split": "benchmark_holdout",
            "base": {"appeal_vector_capture": 1, "grounding": 3, "case_specific_clinical_rebuttal": 3},
        },
        {
            **base,
            "case_id": "micro_t1",
            "dataset_split": "benchmark_train",
            "base": {"appeal_vector_capture": 1, "grounding": 3},
        },
        {
            **base,
            "case_id": "micro_t2",
            "dataset_split": "benchmark_train",
            "base": {"appeal_vector_capture": 1, "grounding": 3},
        },
    ]
