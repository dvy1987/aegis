# Two-Step Transparent Outcome Simulator — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish PRD FR8 honestly — the Outcome Simulator's LLM does only critique-first fuzzy feature judgment (1/3/5 anchors + evidence), and a deterministic published rule set scores those features into an APPROVE/DENY verdict (weighted sum + must-have veto + threshold), deleting the `threshold=10` hack.

**Architecture:** Three layers — safety gates stay in `self_check`/`deterministic_gates` (untouched); the LLM surface (`SimulatorClient.assess`) returns a `FeatureAssessment` (no score, no verdict); a pure `score_outcome(assessment, rules)` computes the `SimulatorResult`. The verdict is a pure function of (LLM anchors, published `eval/simulator_rules.json`). Insurer-visible inputs only, so one path serves production (`POST /v1/appeal`) and eval (`run_evaluated_case`). Everything is offline-testable via `StubSimulatorClient`.

**Tech Stack:** Python 3.11, `uv`, Pydantic v2, `pytest`, `google-genai` (Vertex) for the live `assess` only.

**Spec:** `docs/specs/2026-05-30-outcome-simulator-two-step-design.md`. **Invariants:** INV-S1 separation of powers, INV-S2 transparency, INV-S3 critique-first, INV-S4 insurer-visible-only, INV-S5 no hand-tuning.

**Conventions for every task:**
- Run tests from `backend/`: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest <path> -q`.
- No GCP on the dev machine: the real `GeminiSimulatorClient.assess` is unit-tested for construction only; all scoring/wiring is tested offline with `StubSimulatorClient`. Cloud imports stay inside methods.
- Commit per task (short imperative subject).

---

## File Structure

**New files**
- `backend/app/aegis_v1/simulator_scoring.py` — `FeatureRule`, `SimulatorRules`, `load_simulator_rules()`, `score_outcome()` (the deterministic heart).
- `backend/tests/unit/aegis_v1/test_simulator_scoring.py` — model + rules-load + scoring tests.

**Modified files**
- `eval/simulator_rules.json` — rewritten from its unused gate content into the approval rubric.
- `backend/app/aegis_v1/schemas.py` — add `FeatureMark`, `FeatureAssessment`, `FeatureScore`; extend `SimulatorResult` (float `score`/`threshold`; add `feature_scores`/`gaps`/`critique`; drop `features`).
- `backend/app/aegis_v1/simulator_client.py` — `SimulatorClient.assess` protocol; `StubSimulatorClient.assess` + `uniform_assessment()`; `GeminiSimulatorClient.assess`; remove the old `simulate`/threshold path.
- `backend/app/aegis_v1/tools.py` — `simulator()` composes `assess → load_simulator_rules → score_outcome`.
- Tests updated for the new surface: `backend/tests/unit/aegis_v1/test_simulator_client.py`, `test_appeal_orchestrator.py`, `test_appeal_route.py`, `backend/tests/unit/agent/test_aegis_v1_tools.py`, `backend/tests/unit/evals/test_evaluated_run.py`, `backend/tests/integration/test_live_appeal.py`.

**Ownership boundaries:** `simulator_scoring.py` = "deterministic verdict from a feature vector + published rules"; `simulator_client.py` = "fuzzy LLM feature judgment (or a fake)"; `eval/simulator_rules.json` = "the published, auditable rubric"; `tools.simulator()` = "compose the two".

**Feature keys (used throughout — copy exactly):**
`addresses_denial_rationale`, `cites_clinical_evidence`, `cites_binding_policy`, `rebuts_specific_flaw` (must-have), `specific_requested_action`, `credible_tone`.

---

## Task 1: Data models (`FeatureMark`, `FeatureAssessment`, `FeatureScore`, extended `SimulatorResult`)

**Files:**
- Modify: `backend/app/aegis_v1/schemas.py:88-93` (the `SimulatorResult` class)
- Test: `backend/tests/unit/aegis_v1/test_simulator_scoring.py`
- Modify (stale-assertion fixups): `backend/tests/unit/aegis_v1/test_simulator_client.py`, `backend/tests/unit/agent/test_aegis_v1_tools.py`

> **Ripple note:** dropping the old `features: dict[str, bool]` field from `SimulatorResult` breaks two existing assertions that read `["features"]` off a simulator result (they're finalized in Task 5). Step 4 below neutralizes them so this commit stays green. (Pydantic v2 ignores the now-unknown `features=` kwarg the old `simulate()` still passes, and `int`→`float` coercion keeps the old `score`/`threshold` assertions passing, so nothing else breaks.)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/aegis_v1/test_simulator_scoring.py`:

```python
import pytest
from pydantic import ValidationError

from app.aegis_v1.schemas import (
    FeatureAssessment,
    FeatureMark,
    FeatureScore,
    SimulatorResult,
)


def test_feature_mark_rejects_non_anchor_value():
    with pytest.raises(ValidationError):
        FeatureMark(anchor=2)  # only 1/3/5 allowed


def test_feature_assessment_holds_keyed_marks():
    fa = FeatureAssessment(
        critique="c",
        features={"rebuts_specific_flaw": FeatureMark(anchor=5, evidence="q")},
    )
    assert fa.features["rebuts_specific_flaw"].anchor == 5


def test_simulator_result_accepts_float_score_and_breakdown():
    r = SimulatorResult(
        verdict="DENY", score=0.38, threshold=0.70,
        feature_scores=[FeatureScore(
            feature="rebuts_specific_flaw", anchor=1, weight=0.20, must_have=True)],
        gaps=["must-have not met: rebuts_specific_flaw"], critique="weak",
    )
    assert r.score == 0.38
    assert r.verdict == "DENY"
    assert r.feature_scores[0].must_have is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1/test_simulator_scoring.py -q`
Expected: FAIL — `ImportError: cannot import name 'FeatureMark'`.

- [ ] **Step 3: Add the models and replace `SimulatorResult`**

In `backend/app/aegis_v1/schemas.py`, replace the existing `SimulatorResult` class (currently):

```python
class SimulatorResult(BaseModel):
    verdict: Literal["APPROVE", "DENY"]
    score: int
    threshold: int
    features: dict[str, bool]
    rationale: list[str] = Field(default_factory=list)
```

with:

```python
class FeatureMark(BaseModel):
    anchor: Literal[1, 3, 5]
    evidence: str = ""


class FeatureAssessment(BaseModel):
    """LLM output of the simulator's fuzzy step: critique-first, then per-feature
    1/3/5 anchors with evidence. No score, no verdict."""

    critique: str = ""
    features: dict[str, FeatureMark] = Field(default_factory=dict)


class FeatureScore(BaseModel):
    feature: str
    anchor: Literal[1, 3, 5]
    weight: float
    must_have: bool
    evidence: str = ""


class SimulatorResult(BaseModel):
    verdict: Literal["APPROVE", "DENY"]
    score: float                       # normalized 0.0–1.0
    threshold: float                   # e.g. 0.70
    feature_scores: list[FeatureScore] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)   # why DENY (empty on APPROVE)
    critique: str = ""
    rationale: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Neutralize the two stale `features` assertions**

In `backend/tests/unit/aegis_v1/test_simulator_client.py`, in `test_stub_simulator_returns_requested_outcome`, delete the line `assert isinstance(out["features"], dict)` (the other assertions in that test still pass via int→float coercion; the whole test is removed in Task 5).

In `backend/tests/unit/agent/test_aegis_v1_tools.py`, change `assert sim["features"]` to:

```python
    assert sim["verdict"] in {"APPROVE", "DENY"}
```

(Task 5 finalizes this to assert `sim["feature_scores"]`.)

- [ ] **Step 5: Run tests to verify the affected suites pass**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1/test_simulator_scoring.py tests/unit/aegis_v1/test_simulator_client.py tests/unit/agent/test_aegis_v1_tools.py -q`
Expected: PASS (the 3 new model tests + the existing simulator tests with `features` lines removed).

- [ ] **Step 6: Commit**

```bash
git add backend/app/aegis_v1/schemas.py backend/tests/unit/aegis_v1/test_simulator_scoring.py backend/tests/unit/aegis_v1/test_simulator_client.py backend/tests/unit/agent/test_aegis_v1_tools.py
git commit -m "feat(aegis_v1): simulator feature/score models; SimulatorResult gets float score + breakdown"
```

---

## Task 2: Published rules file + loader

**Files:**
- Modify: `eval/simulator_rules.json` (full rewrite)
- Create: `backend/app/aegis_v1/simulator_scoring.py`
- Test: `backend/tests/unit/aegis_v1/test_simulator_scoring.py` (add)

- [ ] **Step 1: Add the failing test**

Append to `backend/tests/unit/aegis_v1/test_simulator_scoring.py`:

```python
from app.aegis_v1.simulator_scoring import load_simulator_rules

FEATURE_KEYS = {
    "addresses_denial_rationale", "cites_clinical_evidence", "cites_binding_policy",
    "rebuts_specific_flaw", "specific_requested_action", "credible_tone",
}


def test_load_simulator_rules_parses_published_file():
    rules = load_simulator_rules()
    assert rules.version
    assert set(rules.features) == FEATURE_KEYS
    assert abs(sum(f.weight for f in rules.features.values()) - 1.0) < 1e-9
    assert rules.approve_threshold == 0.70
    assert rules.must_have_min_anchor == 3
    assert rules.features["rebuts_specific_flaw"].must_have is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1/test_simulator_scoring.py::test_load_simulator_rules_parses_published_file -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.aegis_v1.simulator_scoring'`.

- [ ] **Step 3: Rewrite the published rules file**

Replace the entire contents of `eval/simulator_rules.json` with:

```json
{
  "version": "v1",
  "anchors": [1, 3, 5],
  "approve_threshold": 0.70,
  "must_have_min_anchor": 3,
  "features": {
    "addresses_denial_rationale": {
      "weight": 0.25, "must_have": false,
      "description": "Directly engages the specific reason the denial states, not a generic appeal."
    },
    "cites_clinical_evidence": {
      "weight": 0.20, "must_have": false,
      "description": "Cites concrete clinical facts from the provider context supporting necessity."
    },
    "cites_binding_policy": {
      "weight": 0.15, "must_have": false,
      "description": "Invokes an applicable policy/plan/regulatory basis rather than hand-waving."
    },
    "rebuts_specific_flaw": {
      "weight": 0.20, "must_have": true,
      "description": "Actually rebuts the core defect the denial hinges on, not just restating facts."
    },
    "specific_requested_action": {
      "weight": 0.10, "must_have": false,
      "description": "Makes a clear, specific ask (overturn + reprocess + qualified reviewer), deadline-aware."
    },
    "credible_tone": {
      "weight": 0.10, "must_have": false,
      "description": "Professional, non-hyperbolic, internally consistent tone an adjuster takes seriously."
    }
  }
}
```

- [ ] **Step 4: Create the loader**

Create `backend/app/aegis_v1/simulator_scoring.py`:

```python
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

# backend/app/aegis_v1/simulator_scoring.py -> parents[3] is the repo root; eval/ lives there.
RULES_PATH = Path(__file__).resolve().parents[3] / "eval" / "simulator_rules.json"


class FeatureRule(BaseModel):
    weight: float
    must_have: bool = False
    description: str = ""


class SimulatorRules(BaseModel):
    version: str
    anchors: list[int] = Field(default_factory=lambda: [1, 3, 5])
    approve_threshold: float
    must_have_min_anchor: int
    features: dict[str, FeatureRule]


def load_simulator_rules(path: str | Path | None = None) -> SimulatorRules:
    p = Path(path) if path else RULES_PATH
    return SimulatorRules.model_validate_json(p.read_text(encoding="utf-8"))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1/test_simulator_scoring.py -q`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add eval/simulator_rules.json backend/app/aegis_v1/simulator_scoring.py backend/tests/unit/aegis_v1/test_simulator_scoring.py
git commit -m "feat(evals): rewrite simulator_rules.json into the approval rubric + loader"
```

---

## Task 3: Deterministic `score_outcome()`

**Files:**
- Modify: `backend/app/aegis_v1/simulator_scoring.py`
- Test: `backend/tests/unit/aegis_v1/test_simulator_scoring.py` (add)

- [ ] **Step 1: Add the failing tests**

Append to `backend/tests/unit/aegis_v1/test_simulator_scoring.py`:

```python
from app.aegis_v1.schemas import FeatureAssessment, FeatureMark
from app.aegis_v1.simulator_scoring import score_outcome

ALL_KEYS = [
    "addresses_denial_rationale", "cites_clinical_evidence", "cites_binding_policy",
    "rebuts_specific_flaw", "specific_requested_action", "credible_tone",
]


def _assess(anchors: dict[str, int], critique: str = "c") -> FeatureAssessment:
    return FeatureAssessment(
        critique=critique,
        features={k: FeatureMark(anchor=v) for k, v in anchors.items()},
    )


def test_all_fives_approve_with_no_gaps():
    rules = load_simulator_rules()
    res = score_outcome(_assess({k: 5 for k in ALL_KEYS}), rules)
    assert res.verdict == "APPROVE"
    assert res.score == 1.0
    assert res.gaps == []


def test_weak_v1_denies_below_threshold_and_must_have_veto():
    rules = load_simulator_rules()
    res = score_outcome(_assess({
        "addresses_denial_rationale": 3, "cites_clinical_evidence": 1,
        "cites_binding_policy": 1, "rebuts_specific_flaw": 1,
        "specific_requested_action": 3, "credible_tone": 3}), rules)
    assert res.verdict == "DENY"
    assert res.score == 0.38
    assert any("rebuts_specific_flaw" in g for g in res.gaps)


def test_must_have_veto_denies_even_with_high_score():
    rules = load_simulator_rules()
    anchors = {k: 5 for k in ALL_KEYS}
    anchors["rebuts_specific_flaw"] = 1
    res = score_outcome(_assess(anchors), rules)
    assert res.score == 0.84            # above 0.70
    assert res.verdict == "DENY"        # but must-have vetoes
    assert res.gaps and "rebuts_specific_flaw" in res.gaps[0]


def test_missing_feature_is_treated_as_anchor_1():
    rules = load_simulator_rules()
    anchors = {k: 5 for k in ALL_KEYS if k != "cites_clinical_evidence"}
    res = score_outcome(_assess(anchors), rules)
    cs = {fs.feature: fs.anchor for fs in res.feature_scores}
    assert cs["cites_clinical_evidence"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1/test_simulator_scoring.py -q`
Expected: FAIL — `ImportError: cannot import name 'score_outcome'`.

- [ ] **Step 3: Implement `score_outcome`**

Append to `backend/app/aegis_v1/simulator_scoring.py`:

```python
from app.aegis_v1.schemas import (
    FeatureAssessment,
    FeatureMark,
    FeatureScore,
    SimulatorResult,
)


def score_outcome(assessment: FeatureAssessment, rules: SimulatorRules) -> SimulatorResult:
    """Deterministic verdict from LLM-assessed features + published rules (INV-S2).

    score = Σ(weight·anchor) / max_anchor, in [0.2, 1.0]. APPROVE iff
    score ≥ approve_threshold AND every must-have feature ≥ must_have_min_anchor.
    """
    feature_scores: list[FeatureScore] = []
    must_have_failures: list[FeatureScore] = []
    weighted = 0.0
    for name, rule in rules.features.items():
        mark = assessment.features.get(name) or FeatureMark(anchor=1)
        fs = FeatureScore(
            feature=name, anchor=mark.anchor, weight=rule.weight,
            must_have=rule.must_have, evidence=mark.evidence,
        )
        feature_scores.append(fs)
        weighted += rule.weight * mark.anchor
        if rule.must_have and mark.anchor < rules.must_have_min_anchor:
            must_have_failures.append(fs)

    max_anchor = max(rules.anchors)
    score = round(weighted / max_anchor, 4)
    approve = (not must_have_failures) and score >= rules.approve_threshold
    verdict = "APPROVE" if approve else "DENY"

    gaps: list[str] = []
    if not approve:
        for fs in must_have_failures:
            gaps.append(
                f"must-have not met: {fs.feature} "
                f"(anchor {fs.anchor} < {rules.must_have_min_anchor})"
            )
        failed = {fs.feature for fs in must_have_failures}
        weak = [fs for fs in feature_scores if fs.feature not in failed and fs.anchor < max_anchor]
        for fs in sorted(weak, key=lambda f: (f.anchor, -f.weight)):
            gaps.append(f"weak: {fs.feature} (anchor {fs.anchor})")

    return SimulatorResult(
        verdict=verdict, score=score, threshold=rules.approve_threshold,
        feature_scores=feature_scores, gaps=gaps,
        critique=assessment.critique,
        rationale=[assessment.critique] if assessment.critique else [],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1/test_simulator_scoring.py -q`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/aegis_v1/simulator_scoring.py backend/tests/unit/aegis_v1/test_simulator_scoring.py
git commit -m "feat(aegis_v1): deterministic score_outcome (weighted sum + must-have veto + threshold)"
```

---

## Task 4: Add the `assess` surface (additive — keeps the old path working)

This task is purely additive so the suite stays green: it adds `assess` to the protocol and both clients, plus the `uniform_assessment` test helper, while leaving the old `simulate` path in place (removed in Task 5).

**Files:**
- Modify: `backend/app/aegis_v1/simulator_client.py`
- Test: `backend/tests/unit/aegis_v1/test_simulator_client.py` (add)

- [ ] **Step 1: Add the failing tests**

Append to `backend/tests/unit/aegis_v1/test_simulator_client.py`:

```python
from app.aegis_v1.simulator_client import uniform_assessment
from app.aegis_v1.schemas import FeatureAssessment


def test_uniform_assessment_marks_all_rubric_features():
    fa = uniform_assessment(5)
    assert isinstance(fa, FeatureAssessment)
    assert fa.features["rebuts_specific_flaw"].anchor == 5
    assert len(fa.features) == 6


def test_stub_assess_returns_the_configured_assessment():
    fa = uniform_assessment(3)
    out = StubSimulatorClient(assessment=fa).assess(
        denial_text="d", clinical_context="c", appeal_letter="a")
    assert out.features["credible_tone"].anchor == 3


def test_stub_assess_defaults_to_weak():
    out = StubSimulatorClient().assess(denial_text="d", clinical_context="c", appeal_letter="a")
    assert out.features["rebuts_specific_flaw"].anchor == 1
```

(`StubSimulatorClient` is already imported at the top of this test file.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1/test_simulator_client.py -q`
Expected: FAIL — `ImportError: cannot import name 'uniform_assessment'`.

- [ ] **Step 3: Add `assess` + `uniform_assessment` (keep `simulate` for now)**

In `backend/app/aegis_v1/simulator_client.py`, update the imports at the top:

```python
from app.aegis_v1.schemas import (
    AppealDraft,
    FeatureAssessment,
    FeatureMark,
    ParsedCase,
    SimulatorResult,
)
```

Add `assess` to the `SimulatorClient` Protocol (add the method below the existing `simulate`):

```python
    def assess(
        self, denial_text: str, clinical_context: str, appeal_letter: str
    ) -> FeatureAssessment:
        """Return critique + per-feature 1/3/5 marks (no score, no verdict)."""
```

Add a module-level helper (after the Protocol, before `StubSimulatorClient`):

```python
def uniform_assessment(anchor: int, critique: str = "stub assessment") -> FeatureAssessment:
    """A FeatureAssessment marking every rubric feature at the same anchor (test helper)."""
    from app.aegis_v1.simulator_scoring import load_simulator_rules

    rules = load_simulator_rules()
    return FeatureAssessment(
        critique=critique,
        features={name: FeatureMark(anchor=anchor) for name in rules.features},
    )
```

In `StubSimulatorClient.__init__`, add an `assessment` parameter and store it (keep the existing `verdict`/`score`/`threshold` params for now):

```python
    def __init__(
        self,
        verdict: str = "DENY",
        score: int = 0,
        threshold: int = DEFAULT_SIMULATOR_THRESHOLD,
        assessment: FeatureAssessment | None = None,
    ) -> None:
        self.verdict = verdict
        self.score = score
        self.threshold = threshold
        self._assessment = assessment
```

Add an `assess` method to `StubSimulatorClient`:

```python
    def assess(self, denial_text, clinical_context, appeal_letter) -> FeatureAssessment:
        return self._assessment or uniform_assessment(1)
```

Add an `assess` method to `GeminiSimulatorClient` (cloud imports inside the method; falls back to a weak assessment on failure so the verdict degrades to DENY):

```python
    def assess(self, denial_text, clinical_context, appeal_letter) -> FeatureAssessment:
        from google import genai
        from google.genai import types
        from pydantic import BaseModel, Field
        from typing import Literal

        class _Mark(BaseModel):
            anchor: Literal[1, 3, 5]
            evidence: str = ""

        class _Assessment(BaseModel):
            critique: str = Field(description="Critique the appeal as a strict adjuster BEFORE marking features.")
            addresses_denial_rationale: _Mark
            cites_clinical_evidence: _Mark
            cites_binding_policy: _Mark
            rebuts_specific_flaw: _Mark
            specific_requested_action: _Mark
            credible_tone: _Mark

        keys = [
            "addresses_denial_rationale", "cites_clinical_evidence", "cites_binding_policy",
            "rebuts_specific_flaw", "specific_requested_action", "credible_tone",
        ]
        prompt = _build_assess_prompt(denial_text, clinical_context, appeal_letter)
        try:
            client = genai.Client(vertexai=True, location=self.location)
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_Assessment,
                    temperature=0.2,
                ),
            )
            data = json.loads(response.text)
            return FeatureAssessment(
                critique=data.get("critique", ""),
                features={
                    k: FeatureMark(anchor=data[k]["anchor"], evidence=data[k].get("evidence", ""))
                    for k in keys
                },
            )
        except Exception:
            return uniform_assessment(1, critique="LLM Insurer Simulator unavailable; treated as weak.")
```

Add the prompt builder (module-level, near `_build_simulator_prompt`):

```python
def _build_assess_prompt(denial_text: str, clinical_context: str, appeal_letter: str) -> str:
    return f"""
    You are a strict Insurer Claims Adjuster. You can see ONLY the documents below
    (no answer key). First CRITIQUE the appeal, then mark each feature on a 1/3/5
    scale (1 = absent/poor, 3 = partial, 5 = strong) with a short evidence quote
    taken verbatim from the appeal letter (empty string if absent).

    Features:
    - addresses_denial_rationale: directly engages the specific denial reason.
    - cites_clinical_evidence: cites concrete clinical facts supporting necessity.
    - cites_binding_policy: invokes an applicable policy/plan/regulatory basis.
    - rebuts_specific_flaw: actually rebuts the core defect the denial hinges on.
    - specific_requested_action: makes a clear, specific ask.
    - credible_tone: professional, non-hyperbolic, internally consistent.

    Denial letter you originally sent:
    {denial_text}

    Clinical context provided by the provider:
    {clinical_context}

    Appeal letter drafted by the patient's agent:
    {appeal_letter}

    Critique first, then output the features. Do NOT output a score or verdict.
    """
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1/test_simulator_client.py -q`
Expected: PASS (existing tests + 3 new = all green; old `simulate`-based tests still pass).

- [ ] **Step 5: Commit**

```bash
git add backend/app/aegis_v1/simulator_client.py backend/tests/unit/aegis_v1/test_simulator_client.py
git commit -m "feat(aegis_v1): add SimulatorClient.assess (critique-first feature judgment) + stub/uniform helper"
```

---

## Task 5: Rewire `simulator()` to assess→score; remove the old `simulate` path; update consumers (breaking swap, one commit)

Changing `StubSimulatorClient` to drop the `verdict`/`score` constructor is breaking, so the client cleanup, the `simulator()` rewire, and all consumer-test updates land together to keep the suite green.

**Files:**
- Modify: `backend/app/aegis_v1/tools.py` (the `simulator` function)
- Modify: `backend/app/aegis_v1/simulator_client.py` (remove old path)
- Modify: `backend/tests/unit/aegis_v1/test_simulator_client.py`, `test_appeal_orchestrator.py`, `test_appeal_route.py`, `backend/tests/unit/agent/test_aegis_v1_tools.py`, `backend/tests/unit/evals/test_evaluated_run.py`

- [ ] **Step 1: Write the failing end-to-end test for `simulator()`**

In `backend/tests/unit/aegis_v1/test_simulator_client.py`, replace the existing `test_simulator_tool_uses_injected_client` with:

```python
def test_simulator_tool_denies_on_weak_assessment():
    out = simulator(parsed_case=_parsed(), appeal_draft=_draft(),
                    self_check_result={}, client=StubSimulatorClient(assessment=uniform_assessment(1)))
    assert out["verdict"] == "DENY"
    assert out["score"] == 0.2
    assert out["gaps"]


def test_simulator_tool_approves_on_strong_assessment():
    out = simulator(parsed_case=_parsed(), appeal_draft=_draft(),
                    self_check_result={}, client=StubSimulatorClient(assessment=uniform_assessment(5)))
    assert out["verdict"] == "APPROVE"
    assert out["score"] == 1.0
    assert out["gaps"] == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1/test_simulator_client.py::test_simulator_tool_approves_on_strong_assessment -q`
Expected: FAIL — current `simulator()` returns the stub's verdict/score via `simulate`, so `score`/`gaps` shape is wrong.

- [ ] **Step 3: Rewire `simulator()` in `tools.py`**

Replace the body of `simulator(...)` in `backend/app/aegis_v1/tools.py` with:

```python
def simulator(
    parsed_case: dict[str, Any],
    appeal_draft: dict[str, Any],
    self_check_result: dict[str, Any],
    client: "SimulatorClient | None" = None,
) -> dict[str, Any]:
    """Run the Insurer Persona Outcome Simulator: LLM critique-first feature
    judgment, then deterministic published-rules scoring. Not a Student tool —
    invoked by the orchestration/eval layer (D11). `self_check_result` is accepted
    for interface stability."""
    from app.aegis_v1.simulator_client import GeminiSimulatorClient, SimulatorClient
    from app.aegis_v1.simulator_scoring import load_simulator_rules, score_outcome
    from app.aegis_v1.schemas import FeatureAssessment

    case = ParsedCase.model_validate(parsed_case)
    draft = AppealDraft.model_validate(appeal_draft)
    active: SimulatorClient = client or GeminiSimulatorClient()
    assessment = FeatureAssessment.model_validate(
        active.assess(
            denial_text=case.denial_text,
            clinical_context=case.clinical_context,
            appeal_letter=draft.appeal_letter,
        )
    )
    return score_outcome(assessment, load_simulator_rules()).model_dump()
```

- [ ] **Step 4: Remove the old `simulate` path from `simulator_client.py`**

In `backend/app/aegis_v1/simulator_client.py`:
- Delete the `simulate` method from `SimulatorClient` Protocol, `StubSimulatorClient`, and `GeminiSimulatorClient`.
- Delete `_build_simulator_prompt`.
- Remove `verdict`/`score`/`threshold` params from `StubSimulatorClient.__init__` (keep only `assessment`):

```python
    def __init__(self, assessment: FeatureAssessment | None = None) -> None:
        self._assessment = assessment
```

- Remove the `threshold` attribute/param from `GeminiSimulatorClient.__init__` and delete the `DEFAULT_SIMULATOR_THRESHOLD` constant (no longer used; the threshold lives in the rules file). `GeminiSimulatorClient.__init__` becomes:

```python
    def __init__(self, model: str | None = None, location: str = "global") -> None:
        self.model = model or os.environ.get("AEGIS_SIMULATOR_MODEL", "gemini-3.1-pro")
        self.location = location
```

- [ ] **Step 5: Update the remaining tests in `test_simulator_client.py`**

- Delete `test_stub_simulator_returns_requested_outcome` (the `verdict`/`score` stub is gone).
- In `test_stub_simulator_is_a_simulator_client`, construct with no args: `StubSimulatorClient()`.
- In `test_gemini_simulator_constructs_with_default_model`, delete the `assert client.threshold == 10` line (threshold now lives in the rules file).

- [ ] **Step 6: Update `test_aegis_v1_tools.py`**

In `backend/tests/unit/agent/test_aegis_v1_tools.py`, change the direct simulator call and assertions:

```python
    sim = simulator(parsed_case=parsed, appeal_draft=draft, self_check_result=check,
                    client=StubSimulatorClient(assessment=uniform_assessment(1)))

    assert "Not legal or medical advice. Draft assistance only." in draft["appeal_letter"]
    assert check["hard_gate_pass"] is True
    assert check["citation_check"]["all_citations_traceable"] is True
    assert sim["verdict"] == "DENY"
    assert sim["feature_scores"]
```

And update the import line to add the helper:

```python
from app.aegis_v1.simulator_client import StubSimulatorClient, uniform_assessment
```

- [ ] **Step 7: Update `test_appeal_orchestrator.py`**

In `backend/tests/unit/aegis_v1/test_appeal_orchestrator.py`, change the import and both stub constructions:

```python
from app.aegis_v1.simulator_client import StubSimulatorClient, uniform_assessment
```

- In `test_orchestrator_surfaces_letter_and_outcome_offline`: `simulator_client=StubSimulatorClient(assessment=uniform_assessment(5))` and assert `result.outcome["verdict"] == "APPROVE"` and `result.outcome["score"] == 1.0` (replace the `score == 10` assertion).
- In `test_orchestrator_outcome_reflects_a_deny`: `simulator_client=StubSimulatorClient(assessment=uniform_assessment(1))` and assert `result.outcome["verdict"] == "DENY"`.

- [ ] **Step 8: Update `test_appeal_route.py`**

In `backend/tests/unit/aegis_v1/test_appeal_route.py`, change the import and the dependency override:

```python
from app.aegis_v1.simulator_client import StubSimulatorClient, uniform_assessment
```

Replace the `_client(...)` helper's simulator override and call sites so that the verdict is driven by the assessment anchor:

```python
def _client(anchor: int = 5) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_drafter_client] = lambda: StubDrafterClient()
    app.dependency_overrides[get_simulator_client] = lambda: StubSimulatorClient(
        assessment=uniform_assessment(anchor)
    )
    return TestClient(app)
```

- In `test_post_appeal_returns_letter_and_outcome_offline`: call `_client(anchor=5)` and assert `body["outcome"]["verdict"] == "APPROVE"`.
- In `test_post_appeal_surfaces_a_deny_outcome`: call `_client(anchor=1)` and assert `resp.json()["outcome"]["verdict"] == "DENY"`.

- [ ] **Step 9: Update `test_evaluated_run.py`**

In `backend/tests/unit/evals/test_evaluated_run.py`, change the import and the simulator-annotation test:

```python
from app.aegis_v1.simulator_client import StubSimulatorClient, uniform_assessment
```

In `test_run_evaluated_case_annotates_simulator_outcome_offline`:

```python
        simulator_client=StubSimulatorClient(assessment=uniform_assessment(1)),
    )
    assert result.simulator_result["verdict"] == "DENY"
    ann = rec.get(result.trace_ref)["annotations"]
    assert ann["simulator_verdict"] == "DENY"
    assert ann["simulator_score"] == 0.2
```

- [ ] **Step 10: Run the affected suites**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1 tests/unit/evals tests/unit/agent -q`
Expected: PASS (all). The deterministic verdict now flows from assess→score everywhere.

- [ ] **Step 11: Commit**

```bash
git add backend/app/aegis_v1/tools.py backend/app/aegis_v1/simulator_client.py backend/tests/unit/aegis_v1/test_simulator_client.py backend/tests/unit/aegis_v1/test_appeal_orchestrator.py backend/tests/unit/aegis_v1/test_appeal_route.py backend/tests/unit/agent/test_aegis_v1_tools.py backend/tests/unit/evals/test_evaluated_run.py
git commit -m "feat(aegis_v1): simulator() = assess + deterministic score_outcome; drop simulate + threshold-10 hack"
```

---

## Task 6: Update the live integration test + full acceptance

**Files:**
- Modify: `backend/tests/integration/test_live_appeal.py`

- [ ] **Step 1: Update the live assertions for the new shape**

In `backend/tests/integration/test_live_appeal.py`, in `test_live_appeal_run_produces_letter_and_outcome`, replace the outcome assertions:

```python
    # a real outcome came back, scored deterministically from LLM features
    assert result.outcome["verdict"] in {"APPROVE", "DENY"}
    assert 0.0 <= result.outcome["score"] <= 1.0
    assert result.outcome["threshold"] == 0.70
    assert result.outcome["feature_scores"]            # transparent breakdown present
    # weak-v1 demo arc: the baseline should land in DENY territory
    assert result.outcome["verdict"] == "DENY"
```

(Leave `test_live_evaluated_case_writes_real_phoenix_annotation` as-is; its `verdict in {APPROVE, DENY}` assertion still holds.)

- [ ] **Step 2: Run the integration test offline (must skip cleanly)**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/integration/test_live_appeal.py -q`
Expected: `2 skipped` (no ADC on the dev machine).

- [ ] **Step 3: Full offline acceptance**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1 tests/unit/evals tests/unit/agent -q`
Expected: PASS (all green).

- [ ] **Step 4: Commit**

```bash
git add backend/tests/integration/test_live_appeal.py
git commit -m "test(integration): live appeal asserts deterministic outcome breakdown (float threshold)"
```

---

## Done-When (acceptance)

- The LLM (`SimulatorClient.assess`) emits only critique + per-feature 1/3/5 marks; it never emits a score or verdict.
- `score_outcome()` is a pure function: weighted sum / max-anchor, must-have veto, 0.70 threshold, gap list — fully unit-tested with hand-made vectors (the three worked examples pass).
- `eval/simulator_rules.json` is the published rubric (weights sum to 1.0); the `threshold=10` hack and the old `simulate` path are gone.
- `simulator()`, `run_appeal_with_outcome` (`POST /v1/appeal`), and `run_evaluated_case` all return the transparent `SimulatorResult` (verdict + float score + feature_scores + gaps + critique).
- Offline suite green: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1 tests/unit/evals tests/unit/agent -q`; `tests/integration` skips without ADC.

## Deferred (not this plan)
- Per-insurer rule sets (single shared set now).
- Live-Gemini calibration of weights/threshold against the benchmark (DEP: GCP) — verify, never hand-tune (INV-S5).
- Any Learning-Coordinator evolution of the rubric (Plan 2).
```
