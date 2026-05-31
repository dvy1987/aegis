# Tier 2 — Learning Efficacy Continuation (offline) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Some tasks are subagent-orchestrated runbooks** (the LLM roles are played by the Claude session, no API key) — those steps are explicit and still capture committed artifacts + extend the replay test.

**Goal:** Strengthen the measured efficacy of the Learning Coordinator entirely offline — (1) extract the one-off Session-24 Phase-2 scripts into a tested, reusable `efficacy_io` module; (2) run a second optimization round on the **full 10/10 split** targeting the next weakest *promptable* dimension; (3) A/B the reflection **meta-prompt** to make future reflections better — all without GCP or an API key, with the firewall (INV-2) and held-out discipline (V2-INV-3) intact.

**Architecture:** A new `backend/app/learning/efficacy_io.py` codifies the firewall packet prep + composite scoring + lift/veto reporting that Session 24 did with throwaway scripts; it is unit-tested against the **already-committed** `eval/efficacy_runs/2026-05-31/` fixtures (deterministic, no new orchestration). Rounds 2 and the meta-prompt A/B are subagent-driven runbooks that reuse that module, capture every draft/judgment/reflection as JSON, and extend the offline replay regression test. Honest-result clause: if v2 is already at the offline ceiling (everything at anchor 5 except corpus-bound `grounding`), the plan records "no further offline headroom" rather than manufacturing lift.

**Tech Stack:** Python 3.11, `uv`, Pydantic v2, `pytest`. No cloud, no API key. The Claude session is the drafter/judge/reflection intelligence (firewall enforced by hand, exactly as in the Session-24 run).

**Specs / prior art:** [`docs/evals/2026-05-31-coordinator-efficacy-run.md`](../evals/2026-05-31-coordinator-efficacy-run.md) (Run #1, +20.5%), [`docs/memory/session-24-execution-handoff.md`](../memory/session-24-execution-handoff.md) (the manual-GEPA runbook + firewall table), [`eval/efficacy_runs/2026-05-31/`](../../eval/efficacy_runs/2026-05-31/) (the committed Run #1 artifacts), [`docs/specs/2026-05-31-learning-coordinator-v2-gepa-design.md`](../specs/2026-05-31-learning-coordinator-v2-gepa-design.md) §5.3 (no-key assistant-orchestrated pass).

**Conventions for every task:**
- Run tests from `backend/`: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest <path> -q`.
- `git commit` from repo root `/bv3/aimbot/divya/buildmind-misc/aegis`; `cd` back to `backend/` before pytest. Commit message ends with the `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>` trailer.
- One commit per task. Nothing pushed to `origin` unless asked.
- **Firewall (INV-2), enforced by hand in the runbook tasks:** drafter & reflection subagents receive ONLY `build_student_case_packet` output (`case_id`+`denial_letter_text`+`clinical_context`); only judge subagents receive the teacher packet. Reflection notes must be laundered (general craft guidance, never the teacher's `expected_appeal_vectors`/`exploitable_weaknesses`/`strong_defenses`).

---

## File Structure

- **Create** `backend/app/learning/efficacy_io.py` — reusable efficacy run I/O + scoring (the codified Phase-2 logic).
- **Create** `backend/tests/unit/learning/test_efficacy_io.py` — unit tests pinned to the committed Run #1 fixtures.
- **Modify** `eval/efficacy_runs/2026-05-31/score_run.py` and `prep_inputs.py` — re-point at `efficacy_io` (DRY; keep the thin CLI wrappers).
- **Create (Task 2 runbook)** `eval/efficacy_runs/2026-06-01-round2/` — full-split round-2 artifacts (inputs/drafts/judgments/reflections/result.json), plus `backend/app/aegis_v1/prompts/drafter_v3.md` if promoted.
- **Modify (Task 2)** `backend/tests/unit/learning/test_efficacy_run_fixture.py` — add a round-2 replay block.
- **Modify (Task 3)** `backend/app/learning/reflection_client.py` — parameterize `build_reflection_prompt` to accept a named meta-variant; add the better variant.
- **Create (Task 3)** `eval/efficacy_runs/2026-06-01-metaprompt-ab/` — the A/B artifacts + a short finding.
- **Modify (Task 4)** `docs/evals/2026-05-31-coordinator-efficacy-run.md` (or a new Run #2 doc) — full-split numbers + round-2 result.

**Ownership boundaries:** `efficacy_io`=pure run I/O + scoring + gating (no orchestration, no LLM); the `eval/efficacy_runs/<date>/` dirs=captured evidence; the prompt files=the optimized "weights"; the replay test=the regression that keeps a manual run reproducible.

---

## Task 1: Extract the reusable `efficacy_io` module (TDD, fully offline)

**Files:** Create `backend/app/learning/efficacy_io.py`; Test `backend/tests/unit/learning/test_efficacy_io.py`.

This codifies what `eval/efficacy_runs/2026-05-31/{prep_inputs,score_run}.py` did inline, so rounds 2+ are cheap and the logic is tested. Tests use the **committed Run #1 artifacts** as fixtures — deterministic, no new subagents.

- [ ] **Step 1: Write the failing test** — `backend/tests/unit/learning/test_efficacy_io.py`:

```python
from pathlib import Path

from app.learning.efficacy_io import (
    CORPUS_BOUND_DIMENSIONS, lift_report, score_split, weakest_promptable_dimension,
)

REPO = Path(__file__).resolve().parents[4]
RUN1 = REPO / "eval" / "efficacy_runs" / "2026-05-31"
HOLDOUT = ["test_case_01_uhc_mednec", "test_case_02_aetna_priorauth",
           "test_case_03_cigna_mednec", "test_case_04_uhc_priorauth"]


def test_score_split_reproduces_run1_baseline_and_candidate():
    assert score_split(RUN1, "v1", HOLDOUT)["composite"] == 0.73
    assert score_split(RUN1, "v2", HOLDOUT)["composite"] == 0.88


def test_weakest_promptable_excludes_corpus_bound_grounding():
    means = score_split(RUN1, "v1", HOLDOUT)["dimension_means"]
    # grounding is tied-low (3.0) but corpus-bound; the target must be the weakest PROMPTABLE dim
    assert "grounding" in CORPUS_BOUND_DIMENSIONS
    assert weakest_promptable_dimension(means) == "appeal_vector_capture"


def test_lift_report_matches_run1_result_and_gates_clean():
    rep = lift_report(RUN1, holdout_ids=HOLDOUT, baseline_version="v1", candidate_version="v2",
                      diff_added_tokens=131, target_dimension="appeal_vector_capture")
    assert rep["lift_absolute"] == 0.15
    assert rep["lift_relative_pct"] == 20.5
    assert rep["vetoes"] == [] and rep["promotable"] is True


def test_lift_report_vetoes_oversized_diff():
    rep = lift_report(RUN1, holdout_ids=HOLDOUT, baseline_version="v1", candidate_version="v2",
                      diff_added_tokens=500, target_dimension="appeal_vector_capture")
    assert "diff_too_large" in rep["vetoes"] and rep["promotable"] is False
```

- [ ] **Step 2: Run to verify it fails** — `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/learning/test_efficacy_io.py -q` → `ModuleNotFoundError: app.learning.efficacy_io`.

- [ ] **Step 3: Implement** — `backend/app/learning/efficacy_io.py`:

```python
"""Reusable I/O + scoring for assistant-orchestrated efficacy runs (the codified
Session-24 Phase-2 logic). Pure functions over a run directory of captured JSON —
no orchestration, no LLM, no cloud. Shared by the eval scripts, round-2+ runs, and
(later) the live efficacy harness."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.learning.models import DIMENSIONS, composite_score

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
    dim_means = {d: round(sum(judgments[c]["dimension_scores"].get(d, 1) for c in case_ids) / len(case_ids), 3)
                 for d in DIMENSIONS} if case_ids else {d: 0.0 for d in DIMENSIONS}
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
```

- [ ] **Step 4: Run to verify pass** — `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/learning/test_efficacy_io.py -q` → 4 passed.

- [ ] **Step 5: DRY the Run #1 scripts** — edit `eval/efficacy_runs/2026-05-31/score_run.py` to import `score_split`/`lift_report` from `app.learning.efficacy_io` and re-emit the same `result.json` (verify it is byte-identical via `git diff --stat` showing only the script changed, not `result.json`). Edit `prep_inputs.py` to call `build_run_inputs`. Re-run both and confirm `result.json` and `inputs/` are unchanged.

Run: `cd backend && env UV_CACHE_DIR=/tmp/uv-cache uv run python ../eval/efficacy_runs/2026-05-31/score_run.py >/dev/null && cd .. && git diff --stat eval/efficacy_runs/2026-05-31/result.json` → no change to `result.json`.

- [ ] **Step 6: Full unit suite** — `cd backend && env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit -q` → all green (90 + 4 new).

- [ ] **Step 7: Commit**

```bash
git add backend/app/learning/efficacy_io.py backend/tests/unit/learning/test_efficacy_io.py \
        eval/efficacy_runs/2026-05-31/score_run.py eval/efficacy_runs/2026-05-31/prep_inputs.py
git commit -m "feat(learning): extract tested efficacy_io module from the Phase-2 scripts

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Round 2 — full 10/10 split, next weakest promptable dimension (subagent-driven runbook)

**Files:** Create `eval/efficacy_runs/2026-06-01-round2/` (inputs/drafts/judgments/reflections/result.json); maybe `backend/app/aegis_v1/prompts/drafter_v3.md`; Modify `backend/tests/unit/learning/test_efficacy_run_fixture.py`.

This is a manual GEPA round with the Claude session as drafter/judge/reflection. **Baseline is the currently-promoted `drafter_v2`** (Run #1 promoted it). Reuse the firewall table and the calibrated judge rubric from Run #1 verbatim (see the efficacy doc + handoff). Full split: train = all 10 `case_*`, held-out = all 10 `test_case_*`.

- [ ] **Step 1: Prep firewall-clean inputs for all 20 cases** — a tiny script using `build_run_inputs`:

```python
# eval/efficacy_runs/2026-06-01-round2/prep.py — run from backend/
from pathlib import Path
from app.learning.efficacy_io import build_run_inputs
REPO = Path(__file__).resolve().parents[3]
CASES = REPO / "eval" / "cases" / "drafts"
OUT = Path(__file__).resolve().parent
TRAIN = [p.stem for p in sorted(CASES.glob("case_*.json"))]
HOLDOUT = [p.stem for p in sorted(CASES.glob("test_case_*.json"))]
build_run_inputs(TRAIN + HOLDOUT, cases_dir=CASES, out_dir=OUT)
print(f"train={len(TRAIN)} holdout={len(HOLDOUT)}")
```
Run: `cd backend && env UV_CACHE_DIR=/tmp/uv-cache uv run python ../eval/efficacy_runs/2026-06-01-round2/prep.py` → `train=10 holdout=10`.

- [ ] **Step 2: Baseline (held-out) with `drafter_v2`** — dispatch DRAFTER subagents (batches of ~5) over the 10 `test_case_*` student packets, using `backend/app/aegis_v1/prompts/drafter_v2.md` + the FIXED SAFETY HARNESS (disclaimer verbatim, no win-claims, draft-only, no government-program framing, no exclamation marks, facts-only, no invented authorities, no corpus/playbook). Write `drafts/v2/draft_<case>.json` (`{case_id,prompt_version:"v2",appeal_letter,missing_evidence_checklist,citations_used:[]}`). **Drafter subagents must NOT receive any teacher packet.**

- [ ] **Step 3: Baseline judging (held-out)** — dispatch JUDGE subagents (batches of ~5) with the **Run-#1 calibrated rubric** (1/3/5 ONLY, never 2/4; anchor 5 reserved; `appeal_vector_capture`/`case_specific_clinical_rebuttal` scored against the teacher's specific vectors; coherence penalizes padding). Judges read draft + teacher packet. Write `judgments/v2/judge_<case>.json` with `{j1_safety,j2_faithfulness,hard_gate_pass,dimension_scores,reasoning,improvement_notes}` and laundered notes. Compute baseline via `score_split(run_dir,"v2",HOLDOUT)`.

- [ ] **Step 4: Train signal** — draft + judge all 10 `case_*` the same way (drafts/judgments under `v2`), then:
  - `means = score_split(run_dir, "v2", TRAIN)["dimension_means"]`
  - `target = weakest_promptable_dimension(means)`  ← the next dimension to optimize.
  - Collect the laundered `improvement_notes[target]` across the 10 train judgments.
  - **Honest-result gate:** if `means[target] >= 4.8` (i.e. v2 is already at the offline ceiling on every promptable dimension), STOP and record the finding "no further offline headroom — remaining gains require live corpus (grounding) or harder cases"; skip to Step 8 writing a no-op result. Do NOT manufacture a target.

- [ ] **Step 5: Reflect → `drafter_v3.md`** — the session writes `backend/app/aegis_v1/prompts/drafter_v3.md`: critique-first (diagnose the `target` weakness from the laundered notes before editing), add a focused section for `target` only, **≤200 added tokens** (verify with the `wc -w` diff method from Run #1), keep every safety rule, do not target the simulator verdict (INV-3). Record the critique + verbatim laundered notes + the diff size in `reflections/reflect_round2_<target>.md` (do NOT enumerate answer-key field names in the record — see Run #1's fixed reflection doc).

- [ ] **Step 6: Score the candidate (held-out)** — draft + judge all 10 `test_case_*` with `drafter_v3.md` (write under `v3`), same harness + same calibrated rubric.

- [ ] **Step 7: Gate + decide** — write `score.py` (mirrors Run #1's `score_run.py` but imports `efficacy_io.lift_report`, full 10-case holdout, `diff_added_tokens` from Step 5) → `result.json`. Run it. If `promotable` and lift>0: promote — set `tools.py` to `load_drafter_prompt("drafter_v3")` and note the lift in the comment. Else leave `drafter_v2` active and record why.

- [ ] **Step 8: Extend the replay regression** — add to `backend/tests/unit/learning/test_efficacy_run_fixture.py` a `test_round2_*` block that replays `2026-06-01-round2/` through `efficacy_io.lift_report` and asserts the recorded result (lift value + `promotable` + firewall over the round-2 inputs/drafts/reflection). Run `tests/unit/learning -q` → green.

- [ ] **Step 9: Commit** the round-2 dir, any `drafter_v3.md`, the `tools.py` promotion (if any), and the extended test:

```bash
git add eval/efficacy_runs/2026-06-01-round2/ backend/app/aegis_v1/prompts/ \
        backend/app/aegis_v1/tools.py backend/tests/unit/learning/test_efficacy_run_fixture.py
git commit -m "feat(learning): efficacy round 2 (full 10/10 split, <target> dimension)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Reflection meta-prompt A/B (make future reflections better)

**Files:** Modify `backend/app/learning/reflection_client.py`; Test `backend/tests/unit/learning/test_reflection_client.py` (extend); Create `eval/efficacy_runs/2026-06-01-metaprompt-ab/`.

`build_reflection_prompt` is the optimizer's own instruction. Improving it is meta-optimization. We compare the current meta-prompt against one refined variant by holding the {component, signal, target} fixed and measuring which produced candidate yields higher held-out lift.

- [ ] **Step 1: Write the failing test** — extend `test_reflection_client.py`:

```python
def test_build_reflection_prompt_supports_named_variant():
    from app.learning.models import Component, DimensionSignal
    from app.learning.reflection_client import build_reflection_prompt
    comp = Component(component_id="drafter_system_prompt", kind="prompt", text="Draft.")
    sig = DimensionSignal(component_id="drafter_system_prompt", weakest_dimension="appeal_vector_capture",
                          failing_cases=[], notes={"appeal_vector_capture": ["missed the specific flaw"]})
    base = build_reflection_prompt(component=comp, signal=sig, minibatch=[])
    v2 = build_reflection_prompt(component=comp, signal=sig, minibatch=[], variant="critique_plus")
    assert "CRITIQUE" in v2.upper()
    assert v2 != base                       # the variant changes the instruction
    assert "exploitable_weaknesses" not in v2  # firewall still holds in the variant
```

- [ ] **Step 2: Run to verify it fails** — `... pytest tests/unit/learning/test_reflection_client.py -q` → fails (`build_reflection_prompt() got an unexpected keyword argument 'variant'`).

- [ ] **Step 3: Implement** — add a `variant` param to `build_reflection_prompt` in `reflection_client.py` (default `"base"` returns today's prompt verbatim; `"critique_plus"` adds an explicit "first write a 2-sentence diagnosis naming the single most important specific flaw, then propose the minimal edit; do not exceed 200 added tokens; keep all safety rules" preamble). Keep `_REFLECTION_CONSTRAINTS` and the firewall intact in both variants. Do not change the `reflect()` signature (the variant is a build-time choice).

- [ ] **Step 4: Run to verify pass** — `... pytest tests/unit/learning/test_reflection_client.py -q` → all green.

- [ ] **Step 5: A/B runbook** — fix the {component=current best drafter prompt, signal=the Step-4 train signal from Task 2, target}. Produce TWO candidate prompts: one reflecting with the `base` meta-prompt, one with `critique_plus` (the session plays reflection for both, same laundered notes). Draft+judge each candidate on the 10 held-out cases (reuse the harness). Compute both lifts with `efficacy_io.lift_report`. Capture both candidates + both result.jsons under `eval/efficacy_runs/2026-06-01-metaprompt-ab/{base,critique_plus}/`.

- [ ] **Step 6: Decide + record** — write `eval/efficacy_runs/2026-06-01-metaprompt-ab/finding.md`: which meta-prompt produced the higher held-out lift and by how much. If `critique_plus` wins, it is the new default for future rounds (note it in the file + the handoff). Honest clause: if they tie, record "no measurable meta-prompt advantage on this slice" — do not promote on noise.

- [ ] **Step 7: Commit**

```bash
git add backend/app/learning/reflection_client.py backend/tests/unit/learning/test_reflection_client.py \
        eval/efficacy_runs/2026-06-01-metaprompt-ab/
git commit -m "feat(learning): reflection meta-prompt variants + A/B finding

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Update the efficacy evidence + headline number

**Files:** Modify `docs/evals/2026-05-31-coordinator-efficacy-run.md` (append a "Run #2 (full split)" section) or create `docs/evals/2026-06-01-coordinator-efficacy-run2.md`.

- [ ] **Step 1** — record the full-10/10 baseline + round-2 result (per-dimension means + deltas, lift, promotion decision), the meta-prompt A/B finding, and refreshed caveats (note whether the offline ceiling was reached). Cross-link from `docs/memory/current-state.md` and add a `project-index.md` handoff-log row.

- [ ] **Step 2: Commit**

```bash
git add docs/evals/ docs/memory/current-state.md docs/memory/project-index.md
git commit -m "docs(learning): record efficacy Run #2 (full split) + meta-prompt A/B

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Done-When (acceptance)
- `efficacy_io` is a tested module; the Run #1 scripts import it and `result.json` is unchanged (DRY, no regression).
- Round 2 ran on the **full 10/10 split** with the firewall + calibrated rubric, and either promoted `drafter_v3` with a recorded held-out lift OR recorded an honest "offline ceiling reached" finding (no manufactured lift).
- The reflection meta-prompt A/B has a recorded winner (or an honest tie), and the better meta-prompt is the documented default for future rounds.
- The offline replay regression covers the round-2 run; `tests/unit` fully green offline; no test makes a cloud/API call.

## Deferred (to the Tier 1 / GCP companion plan)
- Re-running this same loop with **Gemini** drafting + an **independent** judge + κ≥0.6 calibration (cross-model efficacy; these optimized prompts are its starting point).
- The `grounding` dimension (corpus-bound) — addressable only once live corpus retrieval is wired (Tier 1).
- Live `PhoenixLearningStore`-fed signal (Tier 1) replacing the captured-JSON signal used here.
