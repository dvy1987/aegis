"""Deterministic diversity matrix assignments for 200 manual cases (matrix indices 11–210)."""

from __future__ import annotations

import random
from typing import Any

from app.case_generator import config

# 200 cases → 20 batches × 10. Public case numbers 21–210 + 211–220 (see benchmark_public_number).
FIRST_INDEX = 11
CASE_COUNT = 200
BATCH_SIZE = 10
# Matrix indices 11–20 map to case_211–case_220 so case_11–20 stay free for calibration.
BENCHMARK_INDEX_RESERVED_END = 20
BENCHMARK_PUBLIC_NUMBER_OFFSET = 200


def benchmark_public_number(matrix_index: int) -> int:
    """Map matrix index 11–210 to ``case_<NN>`` filename number."""
    if FIRST_INDEX <= matrix_index <= BENCHMARK_INDEX_RESERVED_END:
        return matrix_index + BENCHMARK_PUBLIC_NUMBER_OFFSET
    return matrix_index


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


# Extension corpus: case_221–case_420 (200 additional benchmark cases)
EXTENSION_FIRST_INDEX = 221
EXTENSION_COUNT = 200
EXTENSION_SEED = 20260603


def planned_cells_extension(seed: int = EXTENSION_SEED) -> list[dict[str, str]]:
    """Return 200 matrix cells for the web-research extension batch (distinct seed)."""
    rng = random.Random(seed)
    cells: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()
    attempts = 0
    while len(cells) < EXTENSION_COUNT and attempts < EXTENSION_COUNT * 25:
        attempts += 1
        cell = config.sample_matrix_cell(rng, forbid_cells=seen)
        key = (cell["insurer"], cell["denial_type"], cell["specialty"], cell["sub_tactic"])
        if key in seen:
            continue
        seen.add(key)
        cells.append(cell)
    while len(cells) < EXTENSION_COUNT:
        cells.append(config.sample_matrix_cell(rng))
    return cells


# Second extension: case_421–case_500 (80 cases → 500 total corpus)
EXTENSION2_FIRST_INDEX = 421
EXTENSION2_COUNT = 80
EXTENSION2_SEED = 20260604


def planned_cells_extension2(seed: int = EXTENSION2_SEED) -> list[dict[str, str]]:
    """Return 80 matrix cells for case_421–case_500 (distinct seed from prior batches)."""
    rng = random.Random(seed)
    cells: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()
    attempts = 0
    while len(cells) < EXTENSION2_COUNT and attempts < EXTENSION2_COUNT * 25:
        attempts += 1
        cell = config.sample_matrix_cell(rng, forbid_cells=seen)
        key = (cell["insurer"], cell["denial_type"], cell["specialty"], cell["sub_tactic"])
        if key in seen:
            continue
        seen.add(key)
        cells.append(cell)
    while len(cells) < EXTENSION2_COUNT:
        cells.append(config.sample_matrix_cell(rng))
    return cells
