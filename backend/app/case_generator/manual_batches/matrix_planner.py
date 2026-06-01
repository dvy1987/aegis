"""Deterministic diversity matrix assignments for 200 manual cases (indices 11–210)."""

from __future__ import annotations

import random
from typing import Any

from app.case_generator import config

# 200 cases → 20 batches × 10
FIRST_INDEX = 11
CASE_COUNT = 200
BATCH_SIZE = 10


def planned_cells(seed: int = 20260601) -> list[dict[str, str]]:
    """Return 200 matrix cells with spread across insurers, denials, specialties, tactics."""
    rng = random.Random(seed)
    cells: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()
    attempts = 0
    while len(cells) < CASE_COUNT and attempts < CASE_COUNT * 20:
        attempts += 1
        cell = config.sample_matrix_cell(rng, forbid_cells=seen)
        key = (cell["insurer"], cell["denial_type"], cell["specialty"], cell["sub_tactic"])
        if key in seen:
            continue
        seen.add(key)
        cells.append(cell)
    while len(cells) < CASE_COUNT:
        cell = config.sample_matrix_cell(rng)
        cells.append(cell)
    return cells


def batch_range(batch_num: int) -> tuple[int, int]:
    """1-based batch number → (start_index, end_index) inclusive case indices."""
    if not 1 <= batch_num <= CASE_COUNT // BATCH_SIZE:
        raise ValueError(f"batch_num must be 1..{CASE_COUNT // BATCH_SIZE}")
    offset = (batch_num - 1) * BATCH_SIZE
    start = FIRST_INDEX + offset
    end = start + BATCH_SIZE - 1
    return start, end


def cells_for_batch(batch_num: int, seed: int = 20260601) -> list[tuple[int, dict[str, str]]]:
    start, end = batch_range(batch_num)
    all_cells = planned_cells(seed)
    offset = start - FIRST_INDEX
    return [
        (start + i, all_cells[offset + i])
        for i in range(end - start + 1)
    ]
