from pathlib import Path

from app.learning.efficacy_io import (
    CORPUS_BOUND_DIMENSIONS, lift_report, score_split, weakest_promptable_dimension,
)

REPO = Path(__file__).resolve().parents[4]
RUN1 = REPO / "eval" / "efficacy_runs" / "2026-05-31"
HOLDOUT = ["test_case_01_uhc_mednec", "test_case_02_aetna_priorauth",
           "test_case_03_cigna_mednec", "test_case_04_uhc_priorauth"]


def test_score_split_reproduces_run1_baseline_and_candidate():
    assert score_split(RUN1, "v1", HOLDOUT)["composite"] == 0.71
    assert score_split(RUN1, "v2", HOLDOUT)["composite"] == 0.90


def test_weakest_promptable_excludes_corpus_bound_grounding():
    means = score_split(RUN1, "v1", HOLDOUT)["dimension_means"]
    # grounding is tied-low (3.0) but corpus-bound; the target must be the weakest PROMPTABLE dim
    assert "grounding" in CORPUS_BOUND_DIMENSIONS
    assert weakest_promptable_dimension(means) == "appeal_vector_capture"


def test_lift_report_matches_run1_result_and_gates_clean():
    rep = lift_report(RUN1, holdout_ids=HOLDOUT, baseline_version="v1", candidate_version="v2",
                      diff_added_tokens=131, target_dimension="appeal_vector_capture")
    assert rep["lift_absolute"] == 0.19
    assert rep["lift_relative_pct"] == 26.8
    assert rep["vetoes"] == [] and rep["promotable"] is True


def test_lift_report_vetoes_oversized_diff():
    rep = lift_report(RUN1, holdout_ids=HOLDOUT, baseline_version="v1", candidate_version="v2",
                      diff_added_tokens=500, target_dimension="appeal_vector_capture")
    assert "diff_too_large" in rep["vetoes"] and rep["promotable"] is False
