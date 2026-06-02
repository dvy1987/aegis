from __future__ import annotations

import json
from pathlib import Path

from app.evals.gumloop.fixes import apply_safe_fixes
from app.evals.gumloop.runner import run_pass_on_case, run_swarm_once
from app.case_generator.validator import validate_case


def _load_case(case_id: str) -> dict:
    repo = Path(__file__).resolve().parents[5]
    path = repo / "eval" / "cases" / "drafts" / f"{case_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_offline_swarm_runs_on_real_case_and_preserves_schema() -> None:
    case = _load_case("case_500_cigna_priorauth")
    res = run_swarm_once(case)
    assert res.case_id == "case_500_cigna_priorauth"
    assert res.arbiter["verdict"] in {"APPROVE", "REVISE", "DISCARD"}

    fixed, history = run_pass_on_case(case, max_fix_iters=1)
    assert history
    vr = validate_case(fixed)
    assert vr.ok, vr.errors


def test_fix_enforces_missing_iro_notice_by_removing_external_review_language() -> None:
    case = _load_case("case_500_cigna_priorauth")
    case = dict(case)
    case["denial_pattern_sources"] = ["missing_iro_notice: test"]
    case["denial_letter_text"] = case["denial_letter_text"] + "\nYou may request an independent external review (IRO)."
    fixed = apply_safe_fixes(case)
    assert "external review" not in fixed["denial_letter_text"].lower()
    assert "iro" not in fixed["denial_letter_text"].lower()


def test_fix_enforces_missing_cost_liability_by_removing_liability_language() -> None:
    case = _load_case("case_500_cigna_priorauth")
    case = dict(case)
    case["denial_pattern_sources"] = ["missing_cost_liability: test"]
    case["denial_letter_text"] = case["denial_letter_text"] + "\nYou may be billed and financially responsible if you proceed."
    fixed = apply_safe_fixes(case)
    ll = fixed["denial_letter_text"].lower()
    assert "financially responsible" not in ll
    assert "you may be billed" not in ll

