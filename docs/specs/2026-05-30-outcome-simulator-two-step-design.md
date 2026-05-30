---
status: Approved (design)
slug: outcome-simulator-two-step
created: 2026-05-30
supersedes-implementation-of: PRD FR8 (Demo Simulator — Two-Step Transparent)
related: docs/specs/2026-05-30-learning-coordinator-design.md
---

# Design: Two-Step Transparent Outcome Simulator (Part A)

## Context & problem

The Outcome Simulator answers the demo/UX question **"would the insurer have approved this
appeal?"** (APPROVE/DENY). PRD **FR8** specifies a *two-step transparent* simulator: an LLM
feature-extraction step, then **deterministic scoring per published rules in
`eval/simulator_rules.json`**.

What was actually built is a **single opaque LLM call** (`GeminiSimulatorClient`) that returns a
critique + score(1–10) + verdict, gated by a hard-coded `threshold=10` hack ("require a perfect 10
to APPROVE so weak-v1 reliably DENYs"). And `eval/simulator_rules.json` does **not** hold approval
rules — it holds unused, misnamed safety/quality gates (PII/disclaimer/length) that are already
implemented in `self_check()` and `deterministic_gates.py` (verified: no code reads the file).

This design finishes FR8 honestly: keep the LLM for the **genuinely fuzzy** semantic judgment it is
good at, but move the **scoring and verdict** into a transparent, deterministic, published rule set —
and delete the threshold hack.

## Goals

- The verdict is computed by **deterministic, published rules** over LLM-assessed features — not by
  an opaque model number and not by a magic threshold.
- The LLM does only **fuzzy feature judgment, critique-first** (AlphaEval discipline: reason before
  scoring; forced 1/3/5 anchors with evidence).
- Fully **offline-testable** via the injectable client pattern (`StubSimulatorClient`); the real
  Gemini call is exercised only by a GCP-gated integration test.
- One code path for **production** (`POST /v1/appeal` / `run_appeal_with_outcome`) and **eval**
  (`run_evaluated_case`).

## Non-goals (deferred)

- Per-insurer rule sets (MVP uses one shared rule set; per-insurer overrides are a later extension).
- Any Learning-Coordinator tuning/evolution of the rubric (Plan 2 territory).
- Folding safety gates (PII/disclaimer/length) into the simulator — those remain a separate concern
  in `self_check`/`deterministic_gates.py`.

## Invariants

- **INV-S1 (separation of powers).** The simulator runs in the orchestration/eval layer wrapping the
  Student, never as a Student tool (carried from D11). Unchanged by this design.
- **INV-S2 (transparency).** The verdict is a pure function of (LLM feature anchors, published
  rules). Anyone can read `eval/simulator_rules.json` and reproduce the verdict from the feature
  vector.
- **INV-S3 (critique-first).** The LLM emits its critique and per-feature reasoning **before**
  committing anchors; it never emits the final score or verdict.
- **INV-S4 (insurer-visible inputs only).** The simulator sees only the denial letter, clinical
  context, and appeal letter — never synthetic provenance / answer key. (The quality judges, not the
  simulator, grade against the embedded flaw.) This keeps prod == eval and removes any firewall risk.
- **INV-S5 (no hand-tuning to pass).** Weights/threshold are principled and published, then
  *verified* against the benchmark — never tuned to force a demo outcome. Weak-v1 DENYs because it
  genuinely lacks features.

## The three layers

1. **Pure-deterministic safety gates** — PII / disclaimer / length / schema. *Unchanged*; live in
   `self_check()` and `deterministic_gates.py`. The simulator does **not** include these (an insurer
   does not deny for a missing disclaimer).
2. **Fuzzy LLM feature judgment** — the LLM reads insurer-visible inputs and, critique-first, grades
   each rubric feature on a forced **1/3/5** anchor with a short **evidence quote** from the appeal.
   Emits no score, no verdict.
3. **Deterministic scoring → verdict** — a pure function applies published weights, enforces
   must-haves, computes a normalized 0–1 score, and decides APPROVE/DENY with a gap list.

## Components & interfaces

### `SimulatorClient` protocol (the only fuzzy/LLM surface)

Replaces the current `simulate(...) -> verdict` with a feature-assessment boundary:

```python
class SimulatorClient(Protocol):
    name: str
    def assess(
        self, denial_text: str, clinical_context: str, appeal_letter: str
    ) -> FeatureAssessment:
        ...
```

`FeatureAssessment` (the LLM output, pre-scoring):

```python
class FeatureAssessment(BaseModel):
    critique: str                          # critique-first narrative (INV-S3)
    features: dict[str, FeatureMark]       # keyed by feature name (rules' feature keys)

class FeatureMark(BaseModel):
    anchor: Literal[1, 3, 5]
    evidence: str                          # short quote from the appeal letter ("" if absent)
```

- **`StubSimulatorClient(assessment: FeatureAssessment | None = None)`** — returns a fixed
  `FeatureAssessment` offline (default: a deliberately weak one). Lets the scorer + wiring be tested
  end-to-end without a model.
- **`GeminiSimulatorClient`** — critique-first structured Vertex/Gemini call; cloud imports stay
  inside the method. Returns a `FeatureAssessment`. No verdict, no threshold logic.

### Deterministic scorer (new module `backend/app/aegis_v1/simulator_scoring.py`)

```python
def load_simulator_rules(path: str | None = None) -> SimulatorRules: ...
def score_outcome(assessment: FeatureAssessment, rules: SimulatorRules) -> SimulatorResult: ...
```

- Pure function; no LLM, no I/O beyond loading the published JSON. Trivially unit-testable with
  hand-made feature vectors.
- `SimulatorRules` is the validated shape of `eval/simulator_rules.json`.

### `simulator(...)` tool (composition; same call sites keep working)

`simulator(parsed_case, appeal_draft, self_check_result, client=None)`:
1. `assessment = (client or GeminiSimulatorClient()).assess(denial_text, clinical_context, appeal_letter)`
2. `rules = load_simulator_rules()`
3. `return score_outcome(assessment, rules).model_dump()`

`run_appeal_with_outcome` and `run_evaluated_case` are unchanged in signature; they keep calling
`simulator(...)` and receive the richer `SimulatorResult`.

## Data flow

```
appeal_letter (+ denial_text, clinical_context)
        │
        ▼  SimulatorClient.assess  (LLM, fuzzy, critique-first)
FeatureAssessment { critique, features: {name -> {anchor, evidence}} }
        │
        ▼  score_outcome(assessment, rules)  (pure, deterministic)
SimulatorResult { verdict, score, threshold, feature_scores[], gaps[], critique }
```

## Published rules — `eval/simulator_rules.json` (rewritten)

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
      "description": "Invokes an applicable policy/plan/regulatory basis (e.g. full-and-fair review, medical-necessity criteria) rather than hand-waving."
    },
    "rebuts_specific_flaw": {
      "weight": 0.20, "must_have": true,
      "description": "Actually rebuts the core defect the denial hinges on (the crux), not just restating facts."
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

Weights sum to 1.0.

## Scoring algorithm (`score_outcome`)

Given anchors `a_i ∈ {1,3,5}` and weights `w_i` (Σ w_i = 1):

1. **Normalized score:** `score = ( Σ_i w_i · a_i ) / 5`  →  range `[0.2, 1.0]`.
2. **Must-have veto:** if any feature with `must_have=true` has `anchor < must_have_min_anchor` (3),
   the verdict is **DENY** regardless of score.
3. **Threshold:** otherwise **APPROVE iff `score ≥ approve_threshold` (0.70)**, else **DENY**.
4. **Gaps (the "why"):** on DENY, `gaps` lists, in priority order: (a) any must-have below the min
   (the veto, explicitly labeled), then (b) the highest-weight features scoring `1`, then those
   scoring `3` — each as a short human-readable string with the feature name. On APPROVE, `gaps` is
   empty.

**Robustness:** `score_outcome` iterates the **rules'** feature keys (not the LLM's), so the rule set
is authoritative. A feature the LLM omits is treated as `anchor = 1` (absent) and flagged in `gaps`;
unknown keys the LLM invents are ignored. The scorer accepts a validated `FeatureAssessment` — the
`simulator()` tool validates the client's output into that model before scoring, so a malformed LLM
response surfaces as a validation error rather than a silent mis-score.

Worked examples (for the test suite):
- Strong letter — all anchors 5 → `score = 1.0`, must-haves ≥3 → **APPROVE**, gaps `[]`.
- Weak v1 — `addresses=3, clinical=1, policy=1, rebuts=1, action=3, tone=3`
  → `score = (0.25·3 + 0.20·1 + 0.15·1 + 0.20·1 + 0.10·3 + 0.10·3)/5 = (0.75+0.2+0.15+0.2+0.3+0.3)/5 = 1.90/5 = 0.38`
  → below 0.70 **and** must-have `rebuts_specific_flaw=1 < 3` → **DENY**; gaps lead with the
  must-have veto.
- Must-have veto despite high score — all 5 except `rebuts_specific_flaw=1`
  → `score = (1.0 − 0.20·(5−1)/5) = 0.84` (≥0.70) but must-have <3 → **DENY** (veto).

## Schema change — `SimulatorResult`

Extend the existing model (in `backend/app/aegis_v1/schemas.py`):

```python
class FeatureScore(BaseModel):
    feature: str
    anchor: Literal[1, 3, 5]
    weight: float
    must_have: bool
    evidence: str

class SimulatorResult(BaseModel):
    verdict: Literal["APPROVE", "DENY"]
    score: float                      # CHANGED: normalized 0.0–1.0 (was int 1–10)
    threshold: float                  # CHANGED: e.g. 0.70 (was int 10)
    feature_scores: list[FeatureScore] = Field(default_factory=list)   # NEW
    gaps: list[str] = Field(default_factory=list)                      # NEW — why DENY
    critique: str = ""                # NEW — LLM critique-first narrative
    rationale: list[str] = Field(default_factory=list)                 # kept (derived)
```

The UX and the Phoenix annotation in `run_evaluated_case` get the full transparent breakdown
(`feature_scores`, `gaps`), not just a number. `run_evaluated_case`'s `simulator_score` annotation
becomes the float score.

## Calibration philosophy

Weights and threshold are set from domain reasoning (above), published, and then **verified** against
the benchmark — never tuned to force the demo arc (INV-S5). The improvement story comes from the
appeal genuinely gaining features (the Learning Coordinator's job), not from moving the line. v3 does
not exist yet, so offline we verify with fixtures: a thin/weak `FeatureAssessment` → DENY, a strong
one → APPROVE. Once live Gemini is available, a calibration pass confirms weak-v1 reliably DENYs on
the real benchmark; if it does not, that is a signal v1 is not actually weak — not license to retune.

## Testing (all offline unless noted)

- **`score_outcome` unit tests** (no LLM): the three worked examples above — APPROVE at all-5, DENY
  by threshold, DENY by must-have veto despite high score; plus gap-list content on DENY and empty
  gaps on APPROVE.
- **Rules load/validate test:** `load_simulator_rules()` parses `eval/simulator_rules.json`, weights
  sum to 1.0, all `features` keys present.
- **`simulator()` end-to-end with `StubSimulatorClient`:** fixed weak assessment → DENY with gaps;
  fixed strong assessment → APPROVE. Confirms assess→load→score wiring and the `SimulatorResult`
  shape.
- **Updated existing tests** (score/threshold are now floats; verdict still APPROVE/DENY):
  `test_simulator_client.py`, `test_appeal_orchestrator.py`, `test_appeal_route.py`,
  `test_evaluated_run.py`.
- **GCP-ready live test** (auto-skips without ADC, in `tests/integration/test_live_appeal.py`):
  real `GeminiDrafterClient` + real `assess` → a valid breakdown is produced and the weak v1 lands in
  DENY territory.

## Files touched

- Rewrite `eval/simulator_rules.json` (gates → approval rubric).
- `backend/app/aegis_v1/simulator_client.py` — `assess` protocol; `FeatureAssessment`/`FeatureMark`;
  update `StubSimulatorClient` + `GeminiSimulatorClient` (critique-first structured output).
- New `backend/app/aegis_v1/simulator_scoring.py` — `SimulatorRules`, `load_simulator_rules`,
  `score_outcome`.
- `backend/app/aegis_v1/schemas.py` — extend `SimulatorResult`; add `FeatureScore`.
- `backend/app/aegis_v1/tools.py` — `simulator()` composes assess→load→score; drop the `threshold=10`
  logic.
- Tests as listed above.
- Docs: PRD FR8 stays (now accurate); optionally enrich it to point at the rubric keys.

## Dependencies

- **DEP:** live Gemini/Vertex for the real `assess` call (the GCP machine). All scoring/wiring is
  buildable and testable offline now.
```
