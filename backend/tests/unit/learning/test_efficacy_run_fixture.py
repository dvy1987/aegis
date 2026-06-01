"""Fixture-replay regression for the Session-24 Phase-2 efficacy run.

Converts the assistant-orchestrated manual GEPA run (drafter/judge/reflection played
by the Claude session over the real synthetic cases) into a deterministic offline
test: it replays the recorded judgments through the real composite_score, asserts the
measured held-out lift reproduces, and re-verifies the INV-2 firewall on the committed
inputs/drafts/reflection. No GCP, no API key — pure replay of captured artifacts.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.learning.models import DIMENSIONS, composite_score
from app.learning.signal import FORBIDDEN_FIELDS

REPO_ROOT = Path(__file__).resolve().parents[4]
RUN = REPO_ROOT / "eval" / "efficacy_runs" / "2026-05-31"
RUN2 = REPO_ROOT / "eval" / "efficacy_runs" / "2026-06-01-round2"
HOLDOUT = ["test_case_01_uhc_mednec", "test_case_02_aetna_priorauth",
           "test_case_03_cigna_mednec", "test_case_04_uhc_priorauth"]


def _composite(version: str, case_id: str) -> float:
    j = json.loads((RUN / "judgments" / version / f"judge_{case_id}.json").read_text())
    return composite_score(j["dimension_scores"], j["hard_gate_pass"])


def _mean(version: str) -> float:
    return round(sum(_composite(version, c) for c in HOLDOUT) / len(HOLDOUT), 4)


def test_recorded_run_reproduces_measured_holdout_lift():
    baseline, optimized = _mean("v1"), _mean("v2")
    assert baseline == 0.73          # v1 weak baseline, held-out mean composite
    assert optimized == 0.88         # v2 (appeal_vector_capture reflection)
    lift = round(optimized - baseline, 4)
    assert lift == 0.15              # +20.5% relative, on cases the reflection never saw
    assert round(100 * lift / baseline, 1) == 20.5


def test_target_dimension_moved_and_grounding_stayed_corpus_bound():
    def dim_mean(version, d):
        return sum(json.loads((RUN / "judgments" / version / f"judge_{c}.json").read_text())
                   ["dimension_scores"].get(d, 1) for c in HOLDOUT) / len(HOLDOUT)
    # the reflected dimension climbed; grounding is corpus-bound and honestly did not move
    assert dim_mean("v2", "appeal_vector_capture") > dim_mean("v1", "appeal_vector_capture")
    assert dim_mean("v2", "grounding") == dim_mean("v1", "grounding") == 3.0


def test_promotable_no_vetoes():
    result = json.loads((RUN / "result.json").read_text())
    assert result["vetoes"] == []
    assert result["promotable"] is True
    assert result["diff_added_tokens"] <= 200   # focused single-dimension reflection


def test_firewall_held_on_drafter_and_reflection_inputs():
    # student packets (drafter input) + v1/v2 drafts + the reflection record must carry
    # NO answer-key field — the firewall (INV-2) the drafter/reflection roles depend on.
    blobs: list[str] = []
    for p in (RUN / "inputs").glob("student_*.json"):
        blobs.append(p.read_text())
    for version in ("v1", "v2"):
        for p in (RUN / "drafts" / version).glob("draft_*.json"):
            blobs.append(p.read_text())
    blobs.append((RUN / "reflections" / "reflect_round1_appeal_vector_capture.md").read_text())
    haystack = "\n".join(blobs)
    for forbidden in FORBIDDEN_FIELDS:
        assert forbidden not in haystack, f"firewall breach: {forbidden} reached a drafter/reflection input"


# --- Round 2 (full 11-case train split, 2026-06-01) — honest "offline ceiling reached" ----------

def _run2_train_means() -> dict[str, float]:
    train = json.loads((RUN2 / "inputs" / "manifest.json").read_text())["train"]
    judg = {c: json.loads((RUN2 / "judgments" / "v2" / f"judge_{c}.json").read_text()) for c in train}
    return {d: round(sum(judg[c]["dimension_scores"].get(d, 1) for c in train) / len(train), 3)
            for d in DIMENSIONS}


def test_round2_reproduces_offline_ceiling_finding():
    # v2 holds at the promptable ceiling across the full 11-case train signal — every
    # prompt-movable dimension >= 4.8; only corpus-bound grounding stays sub-ceiling.
    means = _run2_train_means()
    result = json.loads((RUN2 / "result.json").read_text())
    assert result["round"] == 2 and result["baseline_version"] == "v2"
    assert result["offline_ceiling_reached"] is True
    assert result["decision"] == "no_promotion"
    assert means["grounding"] == 3.0                       # corpus-bound, unaddressable offline
    for promptable in ("appeal_vector_capture", "case_specific_clinical_rebuttal",
                       "evidence_completeness", "persuasive_coherence"):
        assert means[promptable] >= result["ceiling_anchor"], promptable
    assert result["weakest_promptable_dimension"] == "persuasive_coherence"
    assert all(result["hard_gate_pass"].values())          # all 11 hard gates PASS


def test_round2_firewall_held_on_drafter_inputs():
    # round-2 student packets + v2 drafts + the finding record carry NO answer-key field.
    blobs = [p.read_text() for p in (RUN2 / "inputs").glob("student_*.json")]
    blobs += [p.read_text() for p in (RUN2 / "drafts" / "v2").glob("draft_*.json")]
    blobs.append((RUN2 / "reflections" / "round2_no_headroom_finding.md").read_text())
    haystack = "\n".join(blobs)
    for forbidden in FORBIDDEN_FIELDS:
        assert forbidden not in haystack, f"firewall breach: {forbidden} reached a round-2 drafter input"
