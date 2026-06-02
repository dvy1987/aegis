"""A+ pipeline integration — letter enhancements and web refs."""

from __future__ import annotations

import random

from app.case_generator.aplus.pipeline import build_aplus_case
from app.case_generator.aplus.text_metrics import letter_words_ok
from app.case_generator.config import sample_matrix_cell
from app.case_generator.manual_assemble import new_run_id


def test_build_aplus_case_includes_letter_enhancements_and_web_refs() -> None:
    cell = sample_matrix_cell(random.Random(42))
    case = build_aplus_case(
        index=8888,
        cell=cell,
        run_id=new_run_id(88),
        neighbour_summaries=[],
        seed=20260688,
    )
    letter = case["denial_letter_text"].lower()
    refs = case["denial_letter_references"]

    assert "claim file" in letter
    assert "peer-to-peer" in letter
    assert letter_words_ok(case["denial_letter_text"])
    assert len(refs) >= 5
    assert any("Web research" in r.get("relevance", "") for r in refs)


def test_build_aplus_case_catalog_only_when_web_disabled() -> None:
    cell = sample_matrix_cell(random.Random(43))
    case = build_aplus_case(
        index=8887,
        cell=cell,
        run_id=new_run_id(87),
        neighbour_summaries=[],
        seed=20260687,
        use_web_research=False,
    )
    refs = case["denial_letter_references"]
    assert refs
    assert not any("Web research" in r.get("relevance", "") for r in refs)
    assert "claim file" in case["denial_letter_text"].lower()
