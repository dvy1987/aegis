# Learning Coordinator (offline build) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

> **✅ COMPLETE (Session 24, 2026-05-31).** All 12 tasks executed subagent-driven; commits `9f048f7..53f1eaf` on `main`. Learning suite **35 passed**, full `tests/unit` **86 passed** offline; no module-top cloud imports. One genuine plan bug was caught during Task 3 and fixed: the firewall must also launder `improvement_notes` on the `failing_cases` runs that feed the reflection minibatch (corrected in this doc + commit `dab6dc0`). Next: Phase 2 (assistant-orchestrated prompt optimization) — see [`docs/memory/session-24-execution-handoff.md`](../memory/session-24-execution-handoff.md).

**Goal:** Build the full Learning Coordinator machinery — GEPA-faithful reflective prompt evolution that reads its eval signal from a `PhoenixLearningStore`, mutates one component at a time via dimension-targeted reflection, selects on an instance-wise Pareto frontier, merges lineages, gates promotion behind vetoes + a human, and is measurable for real *efficacy* via a pluggable-intelligence harness — all offline-testable with stubs/fakes, no GCP and no API key.

**Architecture:** New package `backend/app/learning/`. Pure deterministic core (models, scoring, Pareto selection, merge, veto gates) + injected Protocol seams for the three LLM roles (drafter/judge already exist; **reflection** is new) and for Phoenix I/O (`PhoenixLearningStore`) and experiment execution (`ExperimentRunner`). Offline implementations are deterministic fakes; Gemini/Anthropic backends are written but unit-tested for construction only. The loop reads back the substrate's own recorded signal (`InMemoryPhoenixRecorder`/`InMemoryPhoenixLearningStore`), so it closes without Phoenix. INV-1 (Phoenix-off → learning halts) and INV-2 (firewall) get build-breaking tests.

**Tech Stack:** Python 3.11, `uv`, Pydantic v2, `pytest`. Optional `anthropic` SDK (efficacy backend, method-local import). No DSPy.

**Spec:** [`docs/specs/2026-05-31-learning-coordinator-v2-gepa-design.md`](../specs/2026-05-31-learning-coordinator-v2-gepa-design.md) (v2) + [`docs/specs/2026-05-30-learning-coordinator-design.md`](../specs/2026-05-30-learning-coordinator-design.md) (v1 invariants).

**Conventions for every task:**
- Run tests from `backend/`: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest <path> -q`.
- `git commit` from the repo root `/bv3/aimbot/divya/buildmind-misc/aegis`; `cd` back to `backend/` before pytest. Commit message ends with the `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>` trailer.
- No live cloud/API calls in any test. Cloud/SDK imports stay **inside methods**.
- One commit per task (rollback safety).

---

## File Structure

**New package `backend/app/learning/`**
- `models.py` — Pydantic models + scoring helpers (`Component`, `Candidate`, `ScoredRun`, `DimensionSignal`, `ComponentVersion`, `CaseScore`, `ExperimentResult`, `PromotionAudit`, `PromotionProposal`, `DIMENSIONS`, `DIMENSION_WEIGHTS`, `composite_score`).
- `store.py` — `PhoenixLearningStore` Protocol + `InMemoryPhoenixLearningStore` fake.
- `signal.py` — `acquire_signal()` + firewall (`FORBIDDEN_FIELDS`).
- `reflection_client.py` — `ReflectionClient` Protocol + `StubReflectionClient` + `GeminiReflectionClient` + `AnthropicReflectionClient` + `build_reflection_prompt()`.
- `selection.py` — `pareto_frontier()`, `pareto_select()`, `select_component()` (pure).
- `mutation.py` — `reflective_mutate()`.
- `merge.py` — `system_aware_merge()` (pure).
- `gates.py` — `evaluate_vetoes()` (pure).
- `experiment.py` — `ExperimentRunner` Protocol + `StubExperimentRunner` + `LiveExperimentRunner`.
- `coordinator.py` — `LearningCoordinator` (the loop + proposal + promotion).
- `efficacy_harness.py` — `run_efficacy()` + CLI.

**New tests `backend/tests/unit/learning/`** — one test module per source module + `test_coordinator_integration.py`.

**Ownership boundaries:** `models`=data+scoring; `store`=Phoenix persistence contract; `signal`=firewalled gradient; `reflection_client`=the LLM mutation step; `selection`/`merge`/`gates`=pure GEPA mechanics; `experiment`=scoring a candidate over a split; `coordinator`=orchestration; `efficacy_harness`=real-intelligence effectiveness measurement.

**Rubric dimensions & weights (copy exactly):** `grounding` 0.30, `appeal_vector_capture` 0.25, `case_specific_clinical_rebuttal` 0.20, `evidence_completeness` 0.15, `persuasive_coherence` 0.10.

---

## Task 1: Core models + scoring

**Files:** Create `backend/app/learning/__init__.py` (empty), `backend/app/learning/models.py`; Test `backend/tests/unit/learning/__init__.py` (empty), `backend/tests/unit/learning/test_models.py`.

- [x] **Step 1: Write the failing test** — `backend/tests/unit/learning/test_models.py`:

```python
from app.learning.models import (
    Candidate, CaseScore, Component, DIMENSIONS, DIMENSION_WEIGHTS,
    ExperimentResult, composite_score,
)


def test_dimension_weights_sum_to_one():
    assert set(DIMENSION_WEIGHTS) == set(DIMENSIONS)
    assert abs(sum(DIMENSION_WEIGHTS.values()) - 1.0) < 1e-9


def test_composite_all_fives_is_one_all_ones_is_point_two():
    assert composite_score({d: 5 for d in DIMENSIONS}, hard_gate_pass=True) == 1.0
    assert composite_score({d: 1 for d in DIMENSIONS}, hard_gate_pass=True) == 0.2


def test_composite_hard_gate_fail_is_zero():
    assert composite_score({d: 5 for d in DIMENSIONS}, hard_gate_pass=False) == 0.0


def test_missing_dimension_defaults_to_anchor_one():
    assert composite_score({"grounding": 5}, hard_gate_pass=True) == round(
        0.30 * 1.0 + (0.25 + 0.20 + 0.15 + 0.10) * 0.2, 4)


def test_experiment_result_mean_and_dimension_means():
    r = ExperimentResult(
        candidate_id="c1", dataset_split="holdout",
        per_case=[
            CaseScore(case_id="a", composite=0.4, dimension_scores={d: 1 for d in DIMENSIONS}, hard_gate_pass=True),
            CaseScore(case_id="b", composite=0.8, dimension_scores={d: 5 for d in DIMENSIONS}, hard_gate_pass=True),
        ],
        composite=0.6,
    )
    assert r.composite == 0.6
    assert r.dimension_means()["grounding"] == 3.0


def test_candidate_carries_components_and_lineage():
    c = Candidate(candidate_id="x", components={
        "drafter_system_prompt": Component(component_id="drafter_system_prompt", kind="prompt", text="draft well")},
        origin="seed")
    assert c.components["drafter_system_prompt"].kind == "prompt"
    assert c.parent_id is None
```

- [x] **Step 2: Run to verify it fails** — `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/learning/test_models.py -q` → `ModuleNotFoundError: app.learning.models`.

- [x] **Step 3: Implement** — create `backend/app/learning/__init__.py` (empty) and `backend/app/learning/models.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DIMENSIONS = [
    "grounding", "appeal_vector_capture", "case_specific_clinical_rebuttal",
    "evidence_completeness", "persuasive_coherence",
]
DIMENSION_WEIGHTS = {
    "grounding": 0.30, "appeal_vector_capture": 0.25,
    "case_specific_clinical_rebuttal": 0.20, "evidence_completeness": 0.15,
    "persuasive_coherence": 0.10,
}


def composite_score(dimension_scores: dict[str, int], hard_gate_pass: bool) -> float:
    """Weighted, hard-gated quality composite in [0.0, 1.0]. Hard-gate FAIL → 0.0;
    missing dimensions default to anchor 1; all-5 → 1.0, all-1 → 0.2."""
    if not hard_gate_pass:
        return 0.0
    total = sum(
        DIMENSION_WEIGHTS[d] * (dimension_scores.get(d, 1) / 5.0) for d in DIMENSIONS
    )
    return round(total, 4)


class Component(BaseModel):
    component_id: str                       # "drafter_system_prompt" | "playbook:Cigna:medical_necessity"
    kind: Literal["prompt", "playbook"]
    version: str = "v1"
    text: str | None = None                 # kind == "prompt"
    playbook: dict | None = None            # kind == "playbook"


class Candidate(BaseModel):
    candidate_id: str
    parent_id: str | None = None
    components: dict[str, Component]
    origin: Literal["seed", "reflect", "merge", "restart"] = "seed"
    dimension_targets: list[str] = Field(default_factory=list)
    diff_summary: str = ""


class ScoredRun(BaseModel):
    """A past run read back from Phoenix, joined with its judge annotations.
    Carries ONLY laundered fields — never answer-key provenance (INV-2)."""
    case_id: str
    slice: str                              # f"{insurer}:{denial_type}"
    dimension_scores: dict[str, int]
    hard_gate_pass: bool
    weighted_quality: float
    improvement_notes: dict[str, str] = Field(default_factory=dict)  # laundered, per dimension
    simulator_verdict: Literal["APPROVE", "DENY"] | None = None
    prompt_version: str = ""
    playbook_version: str = ""


class DimensionSignal(BaseModel):
    component_id: str
    weakest_dimension: str
    failing_cases: list[ScoredRun] = Field(default_factory=list)
    notes: dict[str, list[str]] = Field(default_factory=dict)  # dimension -> laundered notes


class ComponentVersion(BaseModel):
    component_id: str
    version: str
    text: str | None = None
    playbook: dict | None = None


class CaseScore(BaseModel):
    case_id: str
    composite: float
    dimension_scores: dict[str, int]
    hard_gate_pass: bool
    simulator_verdict: Literal["APPROVE", "DENY"] | None = None


class ExperimentResult(BaseModel):
    candidate_id: str
    dataset_split: str
    per_case: list[CaseScore] = Field(default_factory=list)
    composite: float = 0.0
    experiment_id: str = ""

    def dimension_means(self) -> dict[str, float]:
        if not self.per_case:
            return {d: 0.0 for d in DIMENSIONS}
        return {
            d: round(sum(c.dimension_scores.get(d, 1) for c in self.per_case) / len(self.per_case), 4)
            for d in DIMENSIONS
        }


class PromotionAudit(BaseModel):
    candidate_id: str
    experiment_id: str
    before_composite: float
    after_composite: float
    per_dimension_deltas: dict[str, float]
    diff_summary: str
    approver: str
    vetoes: list[str] = Field(default_factory=list)


class PromotionProposal(BaseModel):
    candidate: Candidate
    before: ExperimentResult
    after: ExperimentResult
    per_dimension_deltas: dict[str, float]
    vetoes: list[str] = Field(default_factory=list)

    @property
    def is_promotable(self) -> bool:
        return not self.vetoes and self.after.composite > self.before.composite
```

- [x] **Step 4: Run to verify pass** — `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/learning/test_models.py -q` → 6 passed.

- [x] **Step 5: Commit**

```bash
git add backend/app/learning/__init__.py backend/app/learning/models.py backend/tests/unit/learning/__init__.py backend/tests/unit/learning/test_models.py
git commit -m "feat(learning): coordinator core models + composite scoring

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `PhoenixLearningStore` Protocol + in-memory fake

**Files:** Create `backend/app/learning/store.py`; Test `backend/tests/unit/learning/test_store.py`.

- [x] **Step 1: Write the failing test** — `backend/tests/unit/learning/test_store.py`:

```python
from app.learning.models import Component, ScoredRun
from app.learning.store import InMemoryPhoenixLearningStore


def _run(case_id, slice_, scores, gate=True, notes=None):
    from app.learning.models import composite_score
    return ScoredRun(case_id=case_id, slice=slice_, dimension_scores=scores,
                     hard_gate_pass=gate, weighted_quality=composite_score(scores, gate),
                     improvement_notes=notes or {})


def test_store_reads_runs_filtered_by_split():
    store = InMemoryPhoenixLearningStore()
    store.add_run("benchmark_train", _run("a", "Cigna:medical_necessity", {"grounding": 1}))
    store.add_run("benchmark_holdout", _run("b", "Cigna:medical_necessity", {"grounding": 5}))
    train = store.read_scored_runs(dataset_split="benchmark_train")
    assert [r.case_id for r in train] == ["a"]


def test_store_round_trips_component_versions():
    store = InMemoryPhoenixLearningStore()
    store.seed_component(Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="weak"))
    cv = store.read_prompt_version("drafter_system_prompt")
    assert cv.version == "v1" and cv.text == "weak"
    assert store.list_prompt_versions("drafter_system_prompt")[0].version == "v1"


def test_register_promotion_bumps_version_and_records_audit():
    from app.learning.models import Candidate, PromotionAudit
    store = InMemoryPhoenixLearningStore()
    store.seed_component(Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="weak"))
    cand = Candidate(candidate_id="c2", components={
        "drafter_system_prompt": Component(component_id="drafter_system_prompt", kind="prompt", version="v2", text="better")})
    audit = PromotionAudit(candidate_id="c2", experiment_id="exp1", before_composite=0.4,
                           after_composite=0.7, per_dimension_deltas={}, diff_summary="d", approver="pm")
    store.register_promotion(cand, audit)
    assert store.read_prompt_version("drafter_system_prompt").text == "better"
    assert len(store.list_prompt_versions("drafter_system_prompt")) == 2
    assert store.audits[-1].approver == "pm"
```

- [x] **Step 2: Run to verify it fails** — `... pytest tests/unit/learning/test_store.py -q` → ImportError.

- [x] **Step 3: Implement** — `backend/app/learning/store.py`:

```python
from __future__ import annotations

from typing import Protocol

from app.learning.models import (
    Candidate, Component, ComponentVersion, ExperimentResult, PromotionAudit, ScoredRun,
)


class PhoenixLearningStore(Protocol):
    """The ONLY contract the Coordinator has to Phoenix (INV-1). Real impl talks to
    Phoenix MCP/SDK; the fake mirrors the same shapes in memory."""

    def read_scored_runs(self, *, dataset_split: str, prompt_version: str | None = None,
                         playbook_version: str | None = None) -> list[ScoredRun]: ...

    def read_prompt_version(self, component_id: str, version: str | None = None) -> ComponentVersion: ...

    def list_prompt_versions(self, component_id: str) -> list[ComponentVersion]: ...

    def register_promotion(self, candidate: Candidate, audit: PromotionAudit) -> None: ...


class InMemoryPhoenixLearningStore:
    """Deterministic offline fake. Reads back recorded runs (the substrate's
    InMemoryPhoenixRecorder feeds these) and versions components in memory."""

    name = "in_memory_learning_store"

    def __init__(self) -> None:
        self._runs: dict[str, list[ScoredRun]] = {}
        self._versions: dict[str, list[ComponentVersion]] = {}
        self.audits: list[PromotionAudit] = []

    # --- test/seed helpers ---
    def add_run(self, dataset_split: str, run: ScoredRun) -> None:
        self._runs.setdefault(dataset_split, []).append(run)

    def seed_component(self, component: Component) -> None:
        self._versions.setdefault(component.component_id, []).append(
            ComponentVersion(component_id=component.component_id, version=component.version,
                             text=component.text, playbook=component.playbook))

    # --- read ---
    def read_scored_runs(self, *, dataset_split: str, prompt_version: str | None = None,
                         playbook_version: str | None = None) -> list[ScoredRun]:
        runs = self._runs.get(dataset_split, [])
        if prompt_version is not None:
            runs = [r for r in runs if r.prompt_version == prompt_version]
        if playbook_version is not None:
            runs = [r for r in runs if r.playbook_version == playbook_version]
        return list(runs)

    def read_prompt_version(self, component_id: str, version: str | None = None) -> ComponentVersion:
        versions = self._versions[component_id]
        if version is None:
            return versions[-1]
        return next(v for v in versions if v.version == version)

    def list_prompt_versions(self, component_id: str) -> list[ComponentVersion]:
        return list(self._versions.get(component_id, []))

    # --- write ---
    def register_promotion(self, candidate: Candidate, audit: PromotionAudit) -> None:
        for comp in candidate.components.values():
            existing = self._versions.setdefault(comp.component_id, [])
            if not existing or existing[-1].version != comp.version:   # only register real changes
                existing.append(ComponentVersion(component_id=comp.component_id, version=comp.version,
                                                 text=comp.text, playbook=comp.playbook))
        self.audits.append(audit)
```

> The real `PhoenixLearningStore` (MCP/SDK-backed) is built in the companion GCP plan; it implements the same Protocol so the Coordinator is unchanged. `run_experiment` lives on the `ExperimentRunner` seam (Task 9), keeping persistence (store) separate from execution (runner) — a refinement of v2 spec §2.2 for testability.

- [x] **Step 4: Run to verify pass** — `... pytest tests/unit/learning/test_store.py -q` → 3 passed.

- [x] **Step 5: Commit**

```bash
git add backend/app/learning/store.py backend/tests/unit/learning/test_store.py
git commit -m "feat(learning): PhoenixLearningStore protocol + in-memory fake

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Signal acquisition + anti-cheating firewall (INV-1, INV-2)

**Files:** Create `backend/app/learning/signal.py`; Test `backend/tests/unit/learning/test_signal.py`.

- [x] **Step 1: Write the failing test** — `backend/tests/unit/learning/test_signal.py`:

```python
import pytest

from app.learning.models import ScoredRun, composite_score
from app.learning.signal import FORBIDDEN_FIELDS, acquire_signal
from app.learning.store import InMemoryPhoenixLearningStore


def _run(case_id, scores, notes):
    return ScoredRun(case_id=case_id, slice="Cigna:medical_necessity", dimension_scores=scores,
                     hard_gate_pass=True, weighted_quality=composite_score(scores, True),
                     improvement_notes=notes)


def _store_with_runs():
    store = InMemoryPhoenixLearningStore()
    store.add_run("benchmark_train", _run("a", {"grounding": 5, "appeal_vector_capture": 1},
                  {"appeal_vector_capture": "did not hunt the denial's specific defect"}))
    store.add_run("benchmark_train", _run("b", {"grounding": 5, "appeal_vector_capture": 1},
                  {"appeal_vector_capture": "generic appeal, missed the flaw"}))
    return store


def test_signal_picks_weakest_dimension_and_collects_notes():
    sig = acquire_signal(_store_with_runs(), component_id="playbook:Cigna:medical_necessity",
                         dataset_split="benchmark_train", slice_filter="Cigna:medical_necessity")
    assert sig is not None
    assert sig.weakest_dimension == "appeal_vector_capture"
    assert len(sig.notes["appeal_vector_capture"]) == 2


def test_signal_is_none_when_phoenix_has_no_runs():
    empty = InMemoryPhoenixLearningStore()
    sig = acquire_signal(empty, component_id="drafter_system_prompt",
                         dataset_split="benchmark_train", slice_filter=None)
    assert sig is None   # INV-1: no Phoenix signal -> no gradient


def test_signal_never_exposes_answer_key_fields():
    # Even if a malformed run smuggled answer-key keys into notes, the firewall strips them.
    store = InMemoryPhoenixLearningStore()
    store.add_run("benchmark_train", _run("a", {"appeal_vector_capture": 1},
                  {"appeal_vector_capture": "fine", "exploitable_weaknesses": "LEAK", "appeal_difficulty": "hard"}))
    sig = acquire_signal(store, component_id="playbook:Cigna:medical_necessity",
                         dataset_split="benchmark_train", slice_filter="Cigna:medical_necessity")
    blob = sig.model_dump_json()
    for forbidden in FORBIDDEN_FIELDS:
        assert forbidden not in blob
```

- [x] **Step 2: Run to verify it fails** — `... pytest tests/unit/learning/test_signal.py -q` → ImportError.

- [x] **Step 3: Implement** — `backend/app/learning/signal.py`:

```python
from __future__ import annotations

from app.learning.models import DIMENSIONS, DimensionSignal, ScoredRun
from app.learning.store import PhoenixLearningStore

# Answer-key / teacher-only fields that must NEVER reach the Student or Optimizer (INV-2).
FORBIDDEN_FIELDS = frozenset({
    "expected_appeal_vectors", "exploitable_weaknesses", "appeal_difficulty",
    "synthetic_provenance", "evaluator_disagreements",
})


def _launder(notes: dict[str, str]) -> dict[str, str]:
    """Keep only rubric-dimension keys; drop any answer-key field (defence in depth)."""
    return {k: v for k, v in notes.items() if k in DIMENSIONS and k not in FORBIDDEN_FIELDS}


def acquire_signal(store: PhoenixLearningStore, *, component_id: str, dataset_split: str,
                   slice_filter: str | None) -> DimensionSignal | None:
    """Read the eval signal FROM Phoenix (INV-1) and reduce it to a firewalled
    DimensionSignal for one component: the weakest rubric dimension on this slice and
    the laundered per-dimension improvement notes. Returns None when there is no
    Phoenix signal (the 'Phoenix-off → learning halts' counterfactual)."""
    runs = store.read_scored_runs(dataset_split=dataset_split)
    if slice_filter is not None:
        runs = [r for r in runs if r.slice == slice_filter]
    if not runs:
        return None

    dim_means = {
        d: sum(r.dimension_scores.get(d, 1) for r in runs) / len(runs) for d in DIMENSIONS
    }
    weakest = min(DIMENSIONS, key=lambda d: dim_means[d])

    notes: dict[str, list[str]] = {d: [] for d in DIMENSIONS}
    for r in runs:
        for dim, note in _launder(r.improvement_notes).items():
            if note:
                notes[dim].append(note)

    # Launder improvement_notes on the runs we carry forward too (defence in depth):
    # failing_cases are serialized into the reflection minibatch, so forbidden keys must
    # be stripped here as well, not only in the aggregated `notes` (INV-2).
    failing = [
        r.model_copy(update={"improvement_notes": _launder(r.improvement_notes)})
        for r in runs if not r.hard_gate_pass or r.dimension_scores.get(weakest, 1) < 5
    ]
    return DimensionSignal(component_id=component_id, weakest_dimension=weakest,
                           failing_cases=failing, notes=notes)
```

- [x] **Step 4: Run to verify pass** — `... pytest tests/unit/learning/test_signal.py -q` → 3 passed.

- [x] **Step 5: Commit**

```bash
git add backend/app/learning/signal.py backend/tests/unit/learning/test_signal.py
git commit -m "feat(learning): firewalled signal acquisition from Phoenix (INV-1/INV-2)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: `ReflectionClient` (Stub + Gemini + Anthropic) + prompt builder

**Files:** Create `backend/app/learning/reflection_client.py`; Test `backend/tests/unit/learning/test_reflection_client.py`.

The Stub is deterministic and *constructive*: it returns the same component with a tactic/prompt-line **tagged with the target dimension**, so downstream scoring (Task 9) can reward it and the loop demonstrably climbs. Gemini/Anthropic backends are written (cloud/SDK imports inside the method, fallback to a no-op edit on failure) but unit-tested for **construction only**.

- [x] **Step 1: Write the failing test** — `backend/tests/unit/learning/test_reflection_client.py`:

```python
from app.learning.models import Component, DimensionSignal, ScoredRun
from app.learning.reflection_client import (
    AnthropicReflectionClient, GeminiReflectionClient, StubReflectionClient, build_reflection_prompt,
)


def _signal(dim="appeal_vector_capture"):
    return DimensionSignal(component_id="playbook:Cigna:medical_necessity", weakest_dimension=dim,
                           failing_cases=[], notes={dim: ["missed the specific denial flaw"]})


def test_stub_reflects_playbook_by_tagging_target_dimension():
    comp = Component(component_id="playbook:Cigna:medical_necessity", kind="playbook", version="v1",
                     playbook={"tactics": [], "required_evidence": [], "dimension_targets": []})
    out = StubReflectionClient().reflect(component=comp, signal=_signal(), minibatch=[])
    assert "appeal_vector_capture" in out.playbook["dimension_targets"]
    assert out.playbook["tactics"]            # a tactic was added


def test_stub_reflects_prompt_by_appending_dimension_line():
    comp = Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="Draft an appeal.")
    out = StubReflectionClient().reflect(component=comp, signal=_signal("grounding"), minibatch=[])
    assert "dim:grounding" in out.text


def test_reflection_prompt_is_critique_first_and_firewalled():
    p = build_reflection_prompt(
        component=Component(component_id="drafter_system_prompt", kind="prompt", text="Draft."),
        signal=_signal(), minibatch=[])
    assert "CRITIQUE" in p.upper()
    assert "exploitable_weaknesses" not in p   # firewall holds in the prompt too


def test_cloud_backends_construct_without_calls():
    assert GeminiReflectionClient().name == "gemini_reflection"
    assert AnthropicReflectionClient().name == "anthropic_reflection"
```

- [x] **Step 2: Run to verify it fails** — `... pytest tests/unit/learning/test_reflection_client.py -q` → ImportError.

- [x] **Step 3: Implement** — `backend/app/learning/reflection_client.py`:

```python
from __future__ import annotations

import os
from typing import Protocol

from app.learning.models import Component, DimensionSignal, ScoredRun

# Hard constraints injected into every reflection so safety/firewall survive optimization.
_REFLECTION_CONSTRAINTS = (
    "Keep the exact disclaimer, citation-only rule, and no-exclamation rule intact. "
    "Change at most ~200 tokens. Do NOT optimize toward the insurer APPROVE/DENY verdict; "
    "improve the QUALITY dimension named below. You may see only the documents and the "
    "laundered improvement notes — never an answer key."
)


def build_reflection_prompt(*, component: Component, signal: DimensionSignal,
                            minibatch: list[ScoredRun]) -> str:
    notes = "\n".join(f"- {n}" for n in signal.notes.get(signal.weakest_dimension, []))
    current = component.text if component.kind == "prompt" else str(component.playbook)
    cases = "\n".join(
        f"- case {r.case_id}: {signal.weakest_dimension}={r.dimension_scores.get(signal.weakest_dimension, 1)}"
        for r in minibatch
    )
    return f"""You are improving one component of an appeal-drafting system.

FIRST CRITIQUE, THEN EDIT. Diagnose why the component underperforms on the weakest
quality dimension before proposing a change.

Weakest dimension to improve: {signal.weakest_dimension}
Current component ({component.kind}):
{current}

Minibatch (insurer-visible signal only):
{cases}

Laundered improvement notes for this dimension:
{notes}

Constraints: {_REFLECTION_CONSTRAINTS}

Return the full revised component text/JSON."""


class ReflectionClient(Protocol):
    name: str

    def reflect(self, *, component: Component, signal: DimensionSignal,
                minibatch: list[ScoredRun]) -> Component:
        """Return a revised component improving signal.weakest_dimension. Critique-first."""


def _tag_component(component: Component, dimension: str) -> Component:
    """Deterministic constructive edit: tag the component with the target dimension so
    downstream scoring can attribute and reward the improvement."""
    nxt = _bump_version(component.version)
    if component.kind == "playbook":
        pb = dict(component.playbook or {})
        pb["tactics"] = list(pb.get("tactics", [])) + [f"Address {dimension} explicitly."]
        pb["dimension_targets"] = sorted(set(pb.get("dimension_targets", [])) | {dimension})
        return component.model_copy(update={"version": nxt, "playbook": pb})
    text = (component.text or "") + f"\n- Strengthen dim:{dimension}."
    return component.model_copy(update={"version": nxt, "text": text})


def _bump_version(version: str) -> str:
    if version.startswith("v") and version[1:].isdigit():
        return f"v{int(version[1:]) + 1}"
    return f"{version}+1"


class StubReflectionClient:
    name = "stub_reflection"

    def reflect(self, *, component: Component, signal: DimensionSignal,
                minibatch: list[ScoredRun]) -> Component:
        return _tag_component(component, signal.weakest_dimension)


class GeminiReflectionClient:
    name = "gemini_reflection"

    def __init__(self, model: str | None = None, location: str = "global") -> None:
        self.model = model or os.environ.get("AEGIS_REFLECTION_MODEL", "gemini-3.1-pro")
        self.location = location

    def reflect(self, *, component, signal, minibatch) -> Component:
        from google import genai
        from google.genai import types
        prompt = build_reflection_prompt(component=component, signal=signal, minibatch=minibatch)
        try:
            client = genai.Client(vertexai=True, location=self.location)
            resp = client.models.generate_content(
                model=self.model, contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7))
            return _apply_text_edit(component, resp.text)
        except Exception:
            return component   # no-op edit on failure → loop simply finds no improvement


class AnthropicReflectionClient:
    name = "anthropic_reflection"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.environ.get("AEGIS_ANTHROPIC_REFLECTION_MODEL", "claude-opus-4-8")

    def reflect(self, *, component, signal, minibatch) -> Component:
        import anthropic
        prompt = build_reflection_prompt(component=component, signal=signal, minibatch=minibatch)
        try:
            client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY from env
            msg = client.messages.create(
                model=self.model, max_tokens=2000, temperature=0.7,
                messages=[{"role": "user", "content": prompt}])
            return _apply_text_edit(component, msg.content[0].text)
        except Exception:
            return component


def _apply_text_edit(component: Component, revised: str) -> Component:
    """Wrap an LLM's revised text back into a Component, bumping the version. For
    playbooks the model returns JSON; tolerate non-JSON by keeping the old playbook."""
    nxt = _bump_version(component.version)
    if component.kind == "prompt":
        return component.model_copy(update={"version": nxt, "text": revised.strip()})
    import json
    try:
        return component.model_copy(update={"version": nxt, "playbook": json.loads(revised)})
    except Exception:
        return component.model_copy(update={"version": nxt})
```

- [x] **Step 4: Run to verify pass** — `... pytest tests/unit/learning/test_reflection_client.py -q` → 4 passed.

- [x] **Step 5: Commit**

```bash
git add backend/app/learning/reflection_client.py backend/tests/unit/learning/test_reflection_client.py
git commit -m "feat(learning): ReflectionClient (stub + gemini + anthropic) + critique-first prompt

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Pareto selection + component selection (pure GEPA mechanics)

**Files:** Create `backend/app/learning/selection.py`; Test `backend/tests/unit/learning/test_selection.py`.

Offline selection is **deterministic** (argmax coverage, ties→higher mean→candidate_id) so tests are stable; the docstring notes the live version may sample stochastically.

- [x] **Step 1: Write the failing test** — `backend/tests/unit/learning/test_selection.py`:

```python
from app.learning.models import Candidate, Component
from app.learning.selection import pareto_frontier, pareto_select, select_component


def _cand(cid):
    return Candidate(candidate_id=cid, components={
        "drafter_system_prompt": Component(component_id="drafter_system_prompt", kind="prompt", text="x")})


def test_pareto_frontier_drops_strictly_dominated():
    pool = [_cand("a"), _cand("b"), _cand("c")]
    scores = {"a": {"1": 0.8, "2": 0.2}, "b": {"1": 0.2, "2": 0.8}, "c": {"1": 0.1, "2": 0.1}}
    front = {c.candidate_id for c in pareto_frontier(pool, scores)}
    assert front == {"a", "b"}            # c is dominated on every case


def test_pareto_select_prefers_widest_coverage():
    pool = [_cand("a"), _cand("b")]
    scores = {"a": {"1": 0.9, "2": 0.9}, "b": {"1": 0.9, "2": 0.1}}
    assert pareto_select(pool, scores).candidate_id == "a"   # a wins both cases


def test_select_component_round_robins_for_coverage():
    parent = Candidate(candidate_id="p", components={
        "drafter_system_prompt": Component(component_id="drafter_system_prompt", kind="prompt", text="x"),
        "playbook:Cigna:medical_necessity": Component(
            component_id="playbook:Cigna:medical_necessity", kind="playbook",
            playbook={"tactics": [], "dimension_targets": []})})
    picks = [select_component(parent, i) for i in range(4)]
    assert picks == ["drafter_system_prompt", "playbook:Cigna:medical_necessity",
                     "drafter_system_prompt", "playbook:Cigna:medical_necessity"]
```

- [x] **Step 2: Run to verify it fails** — `... pytest tests/unit/learning/test_selection.py -q` → ImportError.

- [x] **Step 3: Implement** — `backend/app/learning/selection.py`:

```python
from __future__ import annotations

from app.learning.models import Candidate

Scores = dict[str, dict[str, float]]   # candidate_id -> {case_id -> composite}


def pareto_frontier(pool: list[Candidate], scores: Scores) -> list[Candidate]:
    """Instance-wise Pareto frontier: drop candidates strictly dominated on every case
    by another (GEPA Alg. 2). A candidate survives if it is best-or-tied on >=1 case."""
    case_ids = sorted({cid for s in scores.values() for cid in s})
    survivors: list[Candidate] = []
    for cand in pool:
        s = scores.get(cand.candidate_id, {})
        dominated = False
        for other in pool:
            if other.candidate_id == cand.candidate_id:
                continue
            o = scores.get(other.candidate_id, {})
            ge_all = all(o.get(c, 0.0) >= s.get(c, 0.0) for c in case_ids)
            gt_any = any(o.get(c, 0.0) > s.get(c, 0.0) for c in case_ids)
            if ge_all and gt_any:
                dominated = True
                break
        if not dominated:
            survivors.append(cand)
    return survivors


def pareto_select(pool: list[Candidate], scores: Scores) -> Candidate:
    """Pick the parent to mutate from the Pareto frontier. Offline: deterministic argmax
    by case-win coverage (ties -> higher mean -> candidate_id). The live coordinator may
    sample stochastically with probability proportional to coverage (GEPA)."""
    front = pareto_frontier(pool, scores) or pool
    case_ids = sorted({cid for s in scores.values() for cid in s})

    def coverage(c: Candidate) -> int:
        s = scores.get(c.candidate_id, {})
        return sum(1 for cid in case_ids
                   if s.get(cid, 0.0) >= max(scores.get(o.candidate_id, {}).get(cid, 0.0) for o in front))

    def mean(c: Candidate) -> float:
        s = scores.get(c.candidate_id, {})
        return sum(s.values()) / len(s) if s else 0.0

    return max(front, key=lambda c: (coverage(c), mean(c), c.candidate_id))


def select_component(parent: Candidate, round_index: int) -> str:
    """Round-robin across the candidate's components so every lever (global prompt and
    each per-slice playbook) receives updates over the run (GEPA module round-robin,
    v2 spec §4.2). Deterministic: sorted ids indexed by the round."""
    ids = sorted(parent.components)
    return ids[round_index % len(ids)]
```

- [x] **Step 4: Run to verify pass** — `... pytest tests/unit/learning/test_selection.py -q` → 3 passed.

- [x] **Step 5: Commit**

```bash
git add backend/app/learning/selection.py backend/tests/unit/learning/test_selection.py
git commit -m "feat(learning): instance-wise Pareto frontier + component selection (GEPA)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Reflective mutation (one component per child)

**Files:** Create `backend/app/learning/mutation.py`; Test `backend/tests/unit/learning/test_mutation.py`.

- [x] **Step 1: Write the failing test** — `backend/tests/unit/learning/test_mutation.py`:

```python
from app.learning.models import Candidate, Component, DimensionSignal
from app.learning.mutation import reflective_mutate
from app.learning.reflection_client import StubReflectionClient


def _parent():
    return Candidate(candidate_id="p", components={
        "drafter_system_prompt": Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="x"),
        "playbook:Cigna:medical_necessity": Component(
            component_id="playbook:Cigna:medical_necessity", kind="playbook", version="v1",
            playbook={"tactics": [], "dimension_targets": []})})


def test_mutation_edits_exactly_one_component_and_records_lineage():
    sig = DimensionSignal(component_id="playbook:Cigna:medical_necessity",
                          weakest_dimension="appeal_vector_capture", failing_cases=[], notes={})
    child = reflective_mutate(_parent(), sig, StubReflectionClient(), minibatch=[], next_id="c1")
    assert child.parent_id == "p"
    assert child.origin == "reflect"
    assert child.dimension_targets == ["appeal_vector_capture"]
    # exactly one component changed (the targeted playbook); the prompt is untouched
    assert child.components["drafter_system_prompt"] == _parent().components["drafter_system_prompt"]
    assert child.components["playbook:Cigna:medical_necessity"].version == "v2"
    assert "appeal_vector_capture" in child.components["playbook:Cigna:medical_necessity"].playbook["dimension_targets"]
```

- [x] **Step 2: Run to verify it fails** — `... pytest tests/unit/learning/test_mutation.py -q` → ImportError.

- [x] **Step 3: Implement** — `backend/app/learning/mutation.py`:

```python
from __future__ import annotations

from app.learning.models import Candidate, DimensionSignal, ScoredRun
from app.learning.reflection_client import ReflectionClient


def reflective_mutate(parent: Candidate, signal: DimensionSignal,
                      reflection_client: ReflectionClient, *, minibatch: list[ScoredRun],
                      next_id: str) -> Candidate:
    """GEPA reflective mutation: revise EXACTLY the targeted component, copy the rest,
    record lineage + dimension credit. Small, attributable diffs (V2-INV-2)."""
    target = signal.component_id
    revised = reflection_client.reflect(
        component=parent.components[target], signal=signal, minibatch=minibatch)
    components = dict(parent.components)
    components[target] = revised
    return Candidate(
        candidate_id=next_id, parent_id=parent.candidate_id, components=components,
        origin="reflect", dimension_targets=[signal.weakest_dimension],
        diff_summary=f"reflect {target} for {signal.weakest_dimension}: {parent.components[target].version}->{revised.version}",
    )
```

- [x] **Step 4: Run to verify pass** — `... pytest tests/unit/learning/test_mutation.py -q` → 1 passed.

- [x] **Step 5: Commit**

```bash
git add backend/app/learning/mutation.py backend/tests/unit/learning/test_mutation.py
git commit -m "feat(learning): single-component reflective mutation with lineage + credit

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: System-aware merge

**Files:** Create `backend/app/learning/merge.py`; Test `backend/tests/unit/learning/test_merge.py`.

- [x] **Step 1: Write the failing test** — `backend/tests/unit/learning/test_merge.py`:

```python
from app.learning.models import Candidate, Component
from app.learning.merge import system_aware_merge


def _c(cid, prompt_v, pb_v):
    return Candidate(candidate_id=cid, components={
        "drafter_system_prompt": Component(component_id="drafter_system_prompt", kind="prompt", version=prompt_v, text=prompt_v),
        "playbook:Cigna:medical_necessity": Component(
            component_id="playbook:Cigna:medical_necessity", kind="playbook", version=pb_v,
            playbook={"v": pb_v})})


def test_merge_takes_each_lineages_improved_component():
    a = _c("a", "v2", "v1")   # a improved the prompt
    b = _c("b", "v1", "v2")   # b improved the playbook
    base = _c("seed", "v1", "v1")
    merged = system_aware_merge(a, b, base=base, next_id="m1")
    assert merged is not None
    assert merged.components["drafter_system_prompt"].version == "v2"      # from a
    assert merged.components["playbook:Cigna:medical_necessity"].version == "v2"  # from b
    assert merged.origin == "merge"


def test_merge_returns_none_on_conflict_same_component():
    a = _c("a", "v2", "v1")
    b = _c("b", "v3", "v1")   # both edited the prompt -> conflict
    base = _c("seed", "v1", "v1")
    assert system_aware_merge(a, b, base=base, next_id="m1") is None
```

- [x] **Step 2: Run to verify it fails** — `... pytest tests/unit/learning/test_merge.py -q` → ImportError.

- [x] **Step 3: Implement** — `backend/app/learning/merge.py`:

```python
from __future__ import annotations

from app.learning.models import Candidate, Component


def _changed(cand: Candidate, base: Candidate) -> set[str]:
    return {cid for cid, comp in cand.components.items()
            if base.components.get(cid) is None or base.components[cid].version != comp.version}


def system_aware_merge(a: Candidate, b: Candidate, *, base: Candidate,
                       next_id: str) -> Candidate | None:
    """Combine two lineages that improved DIFFERENT components (GEPA Appendix F).
    Returns None if they edited the same component (conflict → escalate/skip)."""
    changed_a, changed_b = _changed(a, base), _changed(b, base)
    if changed_a & changed_b:
        return None
    components: dict[str, Component] = dict(base.components)
    for cid in changed_a:
        components[cid] = a.components[cid]
    for cid in changed_b:
        components[cid] = b.components[cid]
    return Candidate(
        candidate_id=next_id, parent_id=a.candidate_id, components=components, origin="merge",
        dimension_targets=sorted(set(a.dimension_targets) | set(b.dimension_targets)),
        diff_summary=f"merge {a.candidate_id}+{b.candidate_id}: {sorted(changed_a)}|{sorted(changed_b)}",
    )
```

- [x] **Step 4: Run to verify pass** — `... pytest tests/unit/learning/test_merge.py -q` → 2 passed.

- [x] **Step 5: Commit**

```bash
git add backend/app/learning/merge.py backend/tests/unit/learning/test_merge.py
git commit -m "feat(learning): system-aware merge of complementary lineages (GEPA)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Promotion veto gates

**Files:** Create `backend/app/learning/gates.py`; Test `backend/tests/unit/learning/test_gates.py`.

- [x] **Step 1: Write the failing test** — `backend/tests/unit/learning/test_gates.py`:

```python
from app.learning.models import Candidate, CaseScore, Component, ExperimentResult
from app.learning.gates import evaluate_vetoes


def _exp(cid, comp, cases):
    return ExperimentResult(candidate_id=cid, dataset_split="benchmark_holdout", per_case=cases, composite=comp)


def _cand(diff_tokens=10):
    return Candidate(candidate_id="c", components={
        "drafter_system_prompt": Component(component_id="drafter_system_prompt", kind="prompt", text="w " * diff_tokens)},
        diff_summary="d")


def test_no_vetoes_on_clean_improvement():
    before = _exp("seed", 0.5, [CaseScore(case_id="a", composite=0.5, dimension_scores={"grounding": 3}, hard_gate_pass=True)])
    after = _exp("c", 0.7, [CaseScore(case_id="a", composite=0.7, dimension_scores={"grounding": 5}, hard_gate_pass=True)])
    assert evaluate_vetoes(before, after, _cand()) == []


def test_veto_on_held_out_regression():
    before = _exp("seed", 0.7, [])
    after = _exp("c", 0.5, [])
    assert "held_out_regression" in evaluate_vetoes(before, after, _cand())


def test_veto_on_hard_gate_regression():
    before = _exp("seed", 0.5, [CaseScore(case_id="a", composite=0.5, dimension_scores={}, hard_gate_pass=True)])
    after = _exp("c", 0.6, [CaseScore(case_id="a", composite=0.0, dimension_scores={}, hard_gate_pass=False)])
    assert "safety_or_hard_gate_regression" in evaluate_vetoes(before, after, _cand())


def test_veto_on_simulator_approve_but_judges_fail():
    before = _exp("seed", 0.5, [])
    after = _exp("c", 0.6, [CaseScore(case_id="a", composite=0.0, dimension_scores={}, hard_gate_pass=False, simulator_verdict="APPROVE")])
    vetoes = evaluate_vetoes(before, after, _cand())
    assert "simulator_approve_but_judges_fail" in vetoes


def test_veto_on_oversized_diff():
    before = _exp("seed", 0.5, [])
    after = _exp("c", 0.9, [])
    assert "diff_too_large" in evaluate_vetoes(before, after, _cand(diff_tokens=500))
```

- [x] **Step 2: Run to verify it fails** — `... pytest tests/unit/learning/test_gates.py -q` → ImportError.

- [x] **Step 3: Implement** — `backend/app/learning/gates.py`:

```python
from __future__ import annotations

from app.learning.models import Candidate, ExperimentResult

DIFF_TOKEN_CAP = 200


def _diff_tokens(candidate: Candidate) -> int:
    """Rough token proxy: whitespace tokens across all component bodies."""
    total = 0
    for comp in candidate.components.values():
        if comp.text:
            total += len(comp.text.split())
        if comp.playbook:
            total += len(str(comp.playbook).split())
    return total


def evaluate_vetoes(before: ExperimentResult, after: ExperimentResult,
                    candidate: Candidate, *, diff_token_cap: int = DIFF_TOKEN_CAP) -> list[str]:
    """Non-LLM promotion gates (v1 §8.2). A candidate is promotable only if this is empty
    AND composite improved. Mostly deterministic so judge bias can't drive promotions."""
    vetoes: list[str] = []
    if after.composite < before.composite:
        vetoes.append("held_out_regression")
    if any(not c.hard_gate_pass for c in after.per_case):
        vetoes.append("safety_or_hard_gate_regression")
    if any(c.simulator_verdict == "APPROVE" and not c.hard_gate_pass for c in after.per_case):
        vetoes.append("simulator_approve_but_judges_fail")   # INV-3
    if _diff_tokens(candidate) > diff_token_cap:
        vetoes.append("diff_too_large")
    return vetoes
```

- [x] **Step 4: Run to verify pass** — `... pytest tests/unit/learning/test_gates.py -q` → 5 passed.

- [x] **Step 5: Commit**

```bash
git add backend/app/learning/gates.py backend/tests/unit/learning/test_gates.py
git commit -m "feat(learning): non-LLM promotion veto gates (INV-3 + safety/diff/regression)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: `ExperimentRunner` (stub scorer + live drafter/judge)

**Files:** Create `backend/app/learning/experiment.py`; Test `backend/tests/unit/learning/test_experiment.py`.

The `StubExperimentRunner` scores a candidate **deterministically** from its components — each tactic/prompt-line tagged with a dimension bumps that dimension's anchor — so a reflected (tagged) candidate scores measurably higher than the seed. `LiveExperimentRunner` runs the real drafter+judge over a dataset (used by the efficacy harness / GCP plan).

- [x] **Step 1: Write the failing test** — `backend/tests/unit/learning/test_experiment.py`:

```python
from app.learning.models import Candidate, Component
from app.learning.experiment import StubExperimentRunner


DATASET = [
    {"case_id": "a", "slice": "Cigna:medical_necessity", "base": {"appeal_vector_capture": 1, "grounding": 3}},
    {"case_id": "b", "slice": "Cigna:medical_necessity", "base": {"appeal_vector_capture": 1, "grounding": 3}},
]


def _seed():
    return Candidate(candidate_id="seed", components={
        "drafter_system_prompt": Component(component_id="drafter_system_prompt", kind="prompt", text="draft"),
        "playbook:Cigna:medical_necessity": Component(
            component_id="playbook:Cigna:medical_necessity", kind="playbook",
            playbook={"tactics": [], "dimension_targets": []})})


def _improved():
    c = _seed()
    c.components["playbook:Cigna:medical_necessity"].playbook["dimension_targets"] = ["appeal_vector_capture"]
    return c.model_copy(update={"candidate_id": "improved"})


def test_stub_runner_scores_per_case_and_mean():
    res = StubExperimentRunner(DATASET).run(_seed(), dataset_split="benchmark_holdout")
    assert len(res.per_case) == 2
    assert res.composite == res.per_case[0].composite   # identical cases


def test_targeting_the_weak_dimension_raises_the_composite():
    seed_score = StubExperimentRunner(DATASET).run(_seed(), dataset_split="benchmark_holdout").composite
    improved_score = StubExperimentRunner(DATASET).run(_improved(), dataset_split="benchmark_holdout").composite
    assert improved_score > seed_score   # the loop has real signal to climb
```

- [x] **Step 2: Run to verify it fails** — `... pytest tests/unit/learning/test_experiment.py -q` → ImportError.

- [x] **Step 3: Implement** — `backend/app/learning/experiment.py`:

```python
from __future__ import annotations

from typing import Any, Protocol

from app.learning.models import (
    Candidate, CaseScore, DIMENSIONS, ExperimentResult, composite_score,
)


class ExperimentRunner(Protocol):
    def run(self, candidate: Candidate, *, dataset_split: str) -> ExperimentResult: ...


def _targeted_dimensions(candidate: Candidate, slice_: str) -> list[str]:
    """Which dimensions this candidate explicitly aims to improve, from playbook
    dimension_targets and `dim:<name>` lines in the drafter prompt."""
    targets: set[str] = set()
    pb = candidate.components.get(f"playbook:{slice_}")
    if pb and pb.playbook:
        targets |= set(pb.playbook.get("dimension_targets", []))
    prompt = candidate.components.get("drafter_system_prompt")
    if prompt and prompt.text:
        for line in prompt.text.splitlines():
            if "dim:" in line:
                targets.add(line.split("dim:")[1].strip().rstrip("."))
    return [d for d in targets if d in DIMENSIONS]


class StubExperimentRunner:
    """Deterministic offline scorer: each targeted dimension is bumped two anchor steps
    (1->3->5). Gives the Coordinator a real, monotone gradient to climb in tests."""

    name = "stub_experiment_runner"

    def __init__(self, dataset: list[dict[str, Any]]) -> None:
        self.dataset = dataset

    def run(self, candidate: Candidate, *, dataset_split: str) -> ExperimentResult:
        per_case: list[CaseScore] = []
        for case in self.dataset:
            dims = dict(case["base"])
            for d in _targeted_dimensions(candidate, case["slice"]):
                dims[d] = min(5, dims.get(d, 1) + 2)
            comp = composite_score(dims, hard_gate_pass=True)
            per_case.append(CaseScore(case_id=case["case_id"], composite=comp,
                                      dimension_scores=dims, hard_gate_pass=True))
        mean = round(sum(c.composite for c in per_case) / len(per_case), 4) if per_case else 0.0
        return ExperimentResult(candidate_id=candidate.candidate_id, dataset_split=dataset_split,
                                per_case=per_case, composite=mean,
                                experiment_id=f"exp_{candidate.candidate_id}_{dataset_split}")


class LiveExperimentRunner:
    """Real scorer: draft each case with the candidate's components, judge it, compute the
    composite. Used by the efficacy harness (Claude/Gemini) and the GCP plan. Construction
    is offline-safe; `run` makes model calls and is exercised only with a live backend."""

    name = "live_experiment_runner"

    def __init__(self, dataset: list[dict[str, Any]], drafter_client: Any, judge_client: Any) -> None:
        self.dataset = dataset
        self.drafter_client = drafter_client
        self.judge_client = judge_client

    def run(self, candidate: Candidate, *, dataset_split: str) -> ExperimentResult:
        per_case: list[CaseScore] = []
        for case in self.dataset:
            letter = self.drafter_client.draft(
                prompt=candidate.components["drafter_system_prompt"].text or "",
                parsed_case=case["parsed_case"], citations=case.get("citations", []),
                playbook=(candidate.components.get(f"playbook:{case['slice']}").playbook
                          if candidate.components.get(f"playbook:{case['slice']}") else {}),
                phoenix_summary=case.get("phoenix_summary", {}))
            verdict = self.judge_client.score(case=case, appeal_letter=letter)  # -> dict-like
            dims = verdict["dimension_scores"]
            gate = verdict["hard_gate_pass"]
            per_case.append(CaseScore(case_id=case["case_id"], composite=composite_score(dims, gate),
                                      dimension_scores=dims, hard_gate_pass=gate,
                                      simulator_verdict=verdict.get("simulator_verdict")))
        mean = round(sum(c.composite for c in per_case) / len(per_case), 4) if per_case else 0.0
        return ExperimentResult(candidate_id=candidate.candidate_id, dataset_split=dataset_split,
                                per_case=per_case, composite=mean,
                                experiment_id=f"exp_{candidate.candidate_id}_{dataset_split}")
```

> The `judge_client.score(case, appeal_letter) -> {dimension_scores, hard_gate_pass, simulator_verdict?}` adapter is thin glue over the existing Part-A judge panel; the GCP/efficacy plan supplies the concrete `GeminiJudgeClient`/`AnthropicJudgeClient` adapters. Offline tests use only `StubExperimentRunner`.

- [x] **Step 4: Run to verify pass** — `... pytest tests/unit/learning/test_experiment.py -q` → 2 passed.

- [x] **Step 5: Commit**

```bash
git add backend/app/learning/experiment.py backend/tests/unit/learning/test_experiment.py
git commit -m "feat(learning): experiment runner (deterministic stub scorer + live drafter/judge)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: `LearningCoordinator` — the optimize loop + proposal + promotion

**Files:** Create `backend/app/learning/coordinator.py`; Test `backend/tests/unit/learning/test_coordinator.py`.

- [x] **Step 1: Write the failing test** — `backend/tests/unit/learning/test_coordinator.py`:

```python
from app.learning.coordinator import LearningCoordinator
from app.learning.experiment import StubExperimentRunner
from app.learning.models import Component, ScoredRun, composite_score
from app.learning.reflection_client import StubReflectionClient
from app.learning.store import InMemoryPhoenixLearningStore

SLICE = "Cigna:medical_necessity"
DATASET = [
    {"case_id": "h1", "slice": SLICE, "base": {"appeal_vector_capture": 1, "grounding": 3}},
    {"case_id": "h2", "slice": SLICE, "base": {"appeal_vector_capture": 1, "grounding": 3}},
]


def _seeded_store():
    store = InMemoryPhoenixLearningStore()
    store.seed_component(Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="draft"))
    store.seed_component(Component(component_id=f"playbook:{SLICE}", kind="playbook", version="v1",
                                   playbook={"tactics": [], "dimension_targets": []}))
    for cid in ("t1", "t2"):
        store.add_run("benchmark_train", ScoredRun(
            case_id=cid, slice=SLICE, dimension_scores={"appeal_vector_capture": 1, "grounding": 3},
            hard_gate_pass=True, weighted_quality=composite_score({"appeal_vector_capture": 1, "grounding": 3}, True),
            improvement_notes={"appeal_vector_capture": "missed the specific denial flaw"}))
    return store


def _coordinator(store):
    return LearningCoordinator(
        store=store, runner=StubExperimentRunner(DATASET), reflection_client=StubReflectionClient(),
        slice_filter=SLICE, holdout_split="benchmark_holdout", train_split="benchmark_train",
        max_rounds=6)


def test_coordinator_proposes_a_promotable_lift():
    proposal = _coordinator(_seeded_store()).optimize()
    assert proposal.after.composite > proposal.before.composite
    assert proposal.is_promotable
    assert proposal.per_dimension_deltas["appeal_vector_capture"] > 0
    assert proposal.candidate.dimension_targets   # credit assignment recorded


def test_coordinator_halts_without_phoenix_signal_INV1():
    empty = InMemoryPhoenixLearningStore()
    empty.seed_component(Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="draft"))
    empty.seed_component(Component(component_id=f"playbook:{SLICE}", kind="playbook", version="v1",
                                   playbook={"tactics": [], "dimension_targets": []}))
    proposal = _coordinator(empty).optimize()   # no runs recorded -> no gradient
    assert proposal is None   # INV-1: disable Phoenix signal -> learning halts


def test_promote_writes_new_version_and_audit():
    store = _seeded_store()
    coord = _coordinator(store)
    proposal = coord.optimize()
    coord.promote(proposal, approver="pm")
    # the loop improves the global drafter prompt first; only changed components get a new version
    assert len(store.list_prompt_versions("drafter_system_prompt")) == 2
    assert store.read_prompt_version("drafter_system_prompt").version != "v1"
    assert store.audits[-1].after_composite == proposal.after.composite
```

- [x] **Step 2: Run to verify it fails** — `... pytest tests/unit/learning/test_coordinator.py -q` → ImportError.

- [x] **Step 3: Implement** — `backend/app/learning/coordinator.py`:

```python
from __future__ import annotations

from app.learning.experiment import ExperimentRunner
from app.learning.gates import evaluate_vetoes
from app.learning.merge import system_aware_merge
from app.learning.models import (
    Candidate, Component, DIMENSIONS, ExperimentResult, PromotionAudit, PromotionProposal,
)
from app.learning.mutation import reflective_mutate
from app.learning.reflection_client import ReflectionClient
from app.learning.selection import pareto_select, select_component
from app.learning.signal import acquire_signal
from app.learning.store import PhoenixLearningStore

JUDGE_CONFIG_VERSION = "frozen_v1"


class LearningCoordinator:
    """GEPA-faithful reflective prompt evolution over {drafter prompt} ∪ {per-slice
    playbooks}. Reads its gradient FROM Phoenix (INV-1), reflects one component per
    child (V2-INV-2), selects on an instance-wise Pareto frontier, merges lineages,
    and returns a human-reviewable PromotionProposal. Promotion is explicit (HITL)."""

    def __init__(self, *, store: PhoenixLearningStore, runner: ExperimentRunner,
                 reflection_client: ReflectionClient, slice_filter: str,
                 holdout_split: str = "benchmark_holdout", train_split: str = "benchmark_train",
                 max_rounds: int = 8, max_merges: int = 5,
                 minibatch_size: int = 3) -> None:
        self.store = store
        self.runner = runner
        self.reflection_client = reflection_client
        self.slice_filter = slice_filter
        self.holdout_split = holdout_split
        self.train_split = train_split
        self.max_rounds = max_rounds
        self.max_merges = max_merges
        self.minibatch_size = minibatch_size

    def _seed(self) -> Candidate:
        prompt = self.store.read_prompt_version("drafter_system_prompt")
        pb = self.store.read_prompt_version(f"playbook:{self.slice_filter}")
        return Candidate(candidate_id="seed", components={
            "drafter_system_prompt": Component(component_id="drafter_system_prompt", kind="prompt",
                                               version=prompt.version, text=prompt.text),
            f"playbook:{self.slice_filter}": Component(component_id=f"playbook:{self.slice_filter}",
                                                       kind="playbook", version=pb.version, playbook=pb.playbook)},
            origin="seed")

    def _case_scores(self, result: ExperimentResult) -> dict[str, float]:
        return {c.case_id: c.composite for c in result.per_case}

    def optimize(self) -> PromotionProposal | None:
        # INV-1: no Phoenix signal -> no gradient -> halt before any candidate work.
        probe = acquire_signal(self.store, component_id="drafter_system_prompt",
                               dataset_split=self.train_split, slice_filter=self.slice_filter)
        if probe is None:
            return None

        seed = self._seed()
        results: dict[str, ExperimentResult] = {seed.candidate_id: self.runner.run(seed, dataset_split=self.holdout_split)}
        pool: list[Candidate] = [seed]
        scores = {seed.candidate_id: self._case_scores(results[seed.candidate_id])}
        best = seed
        merges = 0
        counter = 0

        for round_index in range(self.max_rounds):
            parent = pareto_select(pool, scores)
            comp_id = select_component(parent, round_index)   # round-robin coverage (v2 §4.2)
            signal = acquire_signal(self.store, component_id=comp_id,
                                    dataset_split=self.train_split, slice_filter=self.slice_filter)
            if signal is None:
                break
            minibatch = signal.failing_cases[: self.minibatch_size]
            counter += 1
            child = reflective_mutate(parent, signal, self.reflection_client,
                                      minibatch=minibatch, next_id=f"c{counter}")
            res = self.runner.run(child, dataset_split=self.holdout_split)
            pool.append(child)
            results[child.candidate_id] = res
            scores[child.candidate_id] = self._case_scores(res)
            if res.composite > results[best.candidate_id].composite:
                best = child

            # system-aware merge of two complementary lineages (capped)
            if merges < self.max_merges and len(pool) >= 3:
                merged = system_aware_merge(best, child, base=seed, next_id=f"m{counter}")
                if merged is not None:
                    mres = self.runner.run(merged, dataset_split=self.holdout_split)
                    pool.append(merged)
                    results[merged.candidate_id] = mres
                    scores[merged.candidate_id] = self._case_scores(mres)
                    merges += 1
                    if mres.composite > results[best.candidate_id].composite:
                        best = merged

        before, after = results[seed.candidate_id], results[best.candidate_id]
        deltas = {d: round(after.dimension_means()[d] - before.dimension_means()[d], 4) for d in DIMENSIONS}
        vetoes = evaluate_vetoes(before, after, best)
        return PromotionProposal(candidate=best, before=before, after=after,
                                 per_dimension_deltas=deltas, vetoes=vetoes)

    def promote(self, proposal: PromotionProposal, *, approver: str) -> None:
        """HITL promotion: register the new component versions + write the audit. Caller
        is responsible for only calling this on an approved, promotable proposal."""
        audit = PromotionAudit(
            candidate_id=proposal.candidate.candidate_id, experiment_id=proposal.after.experiment_id,
            before_composite=proposal.before.composite, after_composite=proposal.after.composite,
            per_dimension_deltas=proposal.per_dimension_deltas, diff_summary=proposal.candidate.diff_summary,
            approver=approver, vetoes=proposal.vetoes)
        self.store.register_promotion(proposal.candidate, audit)
```

- [x] **Step 4: Run to verify pass** — `... pytest tests/unit/learning/test_coordinator.py -q` → 3 passed.

- [x] **Step 5: Commit**

```bash
git add backend/app/learning/coordinator.py backend/tests/unit/learning/test_coordinator.py
git commit -m "feat(learning): LearningCoordinator optimize loop + HITL promotion (GEPA, INV-1)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: Efficacy harness (+ V2-INV-3 held-out guard) + CLI

**Files:** Create `backend/app/learning/efficacy_harness.py`; Test `backend/tests/unit/learning/test_efficacy_harness.py`.

The harness runs the full loop with **injected** backends and reports the lift; it refuses to report lift measured on the training split (V2-INV-3). The stub-backed test asserts mechanics (a rigged constructive reflection yields measurable lift); the Anthropic/Gemini backends plug in the same way for real efficacy (companion plan / when a key exists).

- [x] **Step 1: Write the failing test** — `backend/tests/unit/learning/test_efficacy_harness.py`:

```python
import pytest

from app.learning.efficacy_harness import EfficacyReport, run_efficacy
from app.learning.experiment import StubExperimentRunner
from app.learning.models import Component, ScoredRun, composite_score
from app.learning.reflection_client import StubReflectionClient
from app.learning.store import InMemoryPhoenixLearningStore

SLICE = "Cigna:medical_necessity"
HOLDOUT = [{"case_id": "h1", "slice": SLICE, "base": {"appeal_vector_capture": 1, "grounding": 3}}]


def _store():
    s = InMemoryPhoenixLearningStore()
    s.seed_component(Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="draft"))
    s.seed_component(Component(component_id=f"playbook:{SLICE}", kind="playbook", version="v1",
                              playbook={"tactics": [], "dimension_targets": []}))
    s.add_run("benchmark_train", ScoredRun(case_id="t1", slice=SLICE,
              dimension_scores={"appeal_vector_capture": 1, "grounding": 3}, hard_gate_pass=True,
              weighted_quality=composite_score({"appeal_vector_capture": 1, "grounding": 3}, True),
              improvement_notes={"appeal_vector_capture": "missed the flaw"}))
    return s


def test_harness_reports_real_held_out_lift():
    report = run_efficacy(store=_store(), runner=StubExperimentRunner(HOLDOUT),
                          reflection_client=StubReflectionClient(), slice_filter=SLICE)
    assert isinstance(report, EfficacyReport)
    assert report.lift > 0
    assert report.optimized_composite > report.baseline_composite
    assert report.dataset_split == "benchmark_holdout"


def test_harness_refuses_to_measure_on_train_split_INV_V2_3():
    with pytest.raises(ValueError):
        run_efficacy(store=_store(), runner=StubExperimentRunner(HOLDOUT),
                     reflection_client=StubReflectionClient(), slice_filter=SLICE,
                     holdout_split="benchmark_train")
```

- [x] **Step 2: Run to verify it fails** — `... pytest tests/unit/learning/test_efficacy_harness.py -q` → ImportError.

- [x] **Step 3: Implement** — `backend/app/learning/efficacy_harness.py`:

```python
from __future__ import annotations

from pydantic import BaseModel, Field

from app.learning.coordinator import LearningCoordinator
from app.learning.experiment import ExperimentRunner
from app.learning.reflection_client import ReflectionClient
from app.learning.store import PhoenixLearningStore


class EfficacyReport(BaseModel):
    slice_filter: str
    dataset_split: str
    baseline_composite: float
    optimized_composite: float
    lift: float
    per_dimension_deltas: dict[str, float] = Field(default_factory=dict)
    promoted_diff: str = ""
    vetoes: list[str] = Field(default_factory=list)


def run_efficacy(*, store: PhoenixLearningStore, runner: ExperimentRunner,
                 reflection_client: ReflectionClient, slice_filter: str,
                 holdout_split: str = "benchmark_holdout", train_split: str = "benchmark_train",
                 max_rounds: int = 8) -> EfficacyReport:
    """Run the full learn-loop with the injected intelligence and report held-out lift.
    Backend-agnostic: Stub (mechanics), Anthropic/Claude or Gemini (real efficacy).
    V2-INV-3: efficacy must be measured on a held-out split the reflection never trained on."""
    if holdout_split == train_split:
        raise ValueError("V2-INV-3: efficacy must be measured on a held-out split, not the train split")

    coordinator = LearningCoordinator(
        store=store, runner=runner, reflection_client=reflection_client, slice_filter=slice_filter,
        holdout_split=holdout_split, train_split=train_split, max_rounds=max_rounds)
    proposal = coordinator.optimize()
    if proposal is None:
        return EfficacyReport(slice_filter=slice_filter, dataset_split=holdout_split,
                              baseline_composite=0.0, optimized_composite=0.0, lift=0.0,
                              vetoes=["no_phoenix_signal"])
    return EfficacyReport(
        slice_filter=slice_filter, dataset_split=holdout_split,
        baseline_composite=proposal.before.composite, optimized_composite=proposal.after.composite,
        lift=round(proposal.after.composite - proposal.before.composite, 4),
        per_dimension_deltas=proposal.per_dimension_deltas, promoted_diff=proposal.candidate.diff_summary,
        vetoes=proposal.vetoes)


def _main() -> None:  # pragma: no cover - thin CLI wrapper
    """CLI entry: `python -m app.learning.efficacy_harness`. The companion GCP/efficacy
    plan wires real backends (Anthropic/Gemini drafter+judge+reflection) here; offline
    this prints a stub-backed mechanics run."""
    import json

    from app.learning.experiment import StubExperimentRunner
    from app.learning.models import Component, ScoredRun, composite_score
    from app.learning.reflection_client import StubReflectionClient
    from app.learning.store import InMemoryPhoenixLearningStore

    slice_ = "Cigna:medical_necessity"
    store = InMemoryPhoenixLearningStore()
    store.seed_component(Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="draft"))
    store.seed_component(Component(component_id=f"playbook:{slice_}", kind="playbook", version="v1",
                                   playbook={"tactics": [], "dimension_targets": []}))
    store.add_run("benchmark_train", ScoredRun(case_id="t1", slice=slice_,
                  dimension_scores={"appeal_vector_capture": 1, "grounding": 3}, hard_gate_pass=True,
                  weighted_quality=composite_score({"appeal_vector_capture": 1, "grounding": 3}, True),
                  improvement_notes={"appeal_vector_capture": "missed the flaw"}))
    holdout = [{"case_id": "h1", "slice": slice_, "base": {"appeal_vector_capture": 1, "grounding": 3}}]
    report = run_efficacy(store=store, runner=StubExperimentRunner(holdout),
                          reflection_client=StubReflectionClient(), slice_filter=slice_)
    print(json.dumps(report.model_dump(), indent=2))


if __name__ == "__main__":  # pragma: no cover
    _main()
```

- [x] **Step 4: Run to verify pass** — `... pytest tests/unit/learning/test_efficacy_harness.py -q` → 2 passed.

- [x] **Step 5: Commit**

```bash
git add backend/app/learning/efficacy_harness.py backend/tests/unit/learning/test_efficacy_harness.py
git commit -m "feat(learning): pluggable-intelligence efficacy harness + held-out guard (V2-INV-3)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: Offline integration test + full acceptance

**Files:** Test `backend/tests/unit/learning/test_integration.py`.

- [x] **Step 1: Write the integration test** — `backend/tests/unit/learning/test_integration.py`:

```python
"""End-to-end offline: seed weak components + recorded signal -> optimize -> promotable
lift -> promote -> the store now serves the improved version. No GCP, no API key."""
from app.learning.coordinator import LearningCoordinator
from app.learning.experiment import StubExperimentRunner
from app.learning.models import Component, ScoredRun, composite_score
from app.learning.reflection_client import StubReflectionClient
from app.learning.store import InMemoryPhoenixLearningStore

SLICE = "Aetna:prior_authorization"
HOLDOUT = [
    {"case_id": "h1", "slice": SLICE, "base": {"appeal_vector_capture": 1, "evidence_completeness": 1, "grounding": 3}},
    {"case_id": "h2", "slice": SLICE, "base": {"appeal_vector_capture": 1, "evidence_completeness": 1, "grounding": 3}},
]


def test_full_offline_learning_loop():
    store = InMemoryPhoenixLearningStore()
    store.seed_component(Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="Draft an appeal."))
    store.seed_component(Component(component_id=f"playbook:{SLICE}", kind="playbook", version="v1",
                                   playbook={"tactics": [], "dimension_targets": []}))
    for cid in ("t1", "t2", "t3"):
        store.add_run("benchmark_train", ScoredRun(
            case_id=cid, slice=SLICE,
            dimension_scores={"appeal_vector_capture": 1, "evidence_completeness": 1, "grounding": 3},
            hard_gate_pass=True,
            weighted_quality=composite_score({"appeal_vector_capture": 1, "evidence_completeness": 1, "grounding": 3}, True),
            improvement_notes={"appeal_vector_capture": "did not rebut the specific defect",
                               "evidence_completeness": "omitted required evidence"}))

    coord = LearningCoordinator(store=store, runner=StubExperimentRunner(HOLDOUT),
                                reflection_client=StubReflectionClient(), slice_filter=SLICE, max_rounds=8)
    proposal = coord.optimize()
    assert proposal is not None and proposal.is_promotable
    assert proposal.after.composite > proposal.before.composite
    assert proposal.vetoes == []

    coord.promote(proposal, approver="pm")
    promoted = store.read_prompt_version("drafter_system_prompt")
    assert promoted.version != "v1"                       # a new version was registered
    assert store.audits[-1].after_composite == proposal.after.composite
```

- [x] **Step 2: Run the integration test** — `... pytest tests/unit/learning/test_integration.py -q` → 1 passed.

- [x] **Step 3: Full offline acceptance** — `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit -q` → all green (existing suite + the new `tests/unit/learning/*`).

- [x] **Step 4: Commit**

```bash
git add backend/tests/unit/learning/test_integration.py
git commit -m "test(learning): end-to-end offline learning loop (seed -> optimize -> promote)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Done-When (acceptance)

- The Coordinator reads its gradient only through `PhoenixLearningStore` (INV-1/V2-INV-1); with no recorded signal, `optimize()` returns `None` (Phoenix-off → learning halts) — tested.
- Reflection edits exactly one component per child with recorded dimension credit (V2-INV-2); the firewall keeps answer-key fields out of the signal and the reflection prompt (INV-2) — tested.
- GEPA mechanics are present and pure: instance-wise Pareto frontier + selection, system-aware merge, veto gates; reflective mutation is critique-first.
- The efficacy harness reports real held-out lift for any injected backend and refuses to measure on the train split (V2-INV-3) — tested with the deterministic stub; Anthropic/Gemini backends plug in unchanged.
- `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit -q` is fully green offline; no test makes a cloud/API call; cloud/SDK imports are method-local.

## Deferred to the companion (GCP/live) plan
- Real `PhoenixLearningStore` over MCP/SDK (spans+annotations read, Experiments, Prompts registry, promotion writes); the `judge_client.score(...)` adapter over the Part-A panel; real Gemini/Anthropic drafter+judge+reflection.
- Measured held-out lift (target +20%, v1 §12); κ≥0.6 judge calibration; the live MCP-off counterfactual; the emergent DENY→APPROVE demo capture.
- The Anthropic/Claude efficacy run can execute in either environment the moment `anthropic` + `ANTHROPIC_API_KEY` are present (the harness + clients are built here).
- `anthropic` added to backend deps as an optional extra (the reflection/efficacy backend); method-local import keeps offline import clean.
- **Stagnation "from-scratch" restart** (v2 §4.6): only meaningful once the loop re-records new traces/annotations between promotions (so the weakest dimension actually shifts). The offline build uses a single static train signal per `optimize()` call, so restart is added in the live plan alongside the re-record step. Pareto diversity + held-out validation (both built here) are the offline anti-stagnation guards.
