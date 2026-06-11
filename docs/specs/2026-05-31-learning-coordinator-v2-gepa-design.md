# Design Spec v2 — Learning Coordinator: GEPA-faithful algorithm, Phoenix-grounded I/O, pluggable intelligence

**Date:** 2026-05-31 · **Status:** Draft (deepens & supersedes §4–§7 of the v1 spec)
**Author:** Claude (Opus 4.8) · **Builds on:** [`2026-05-30-learning-coordinator-design.md`](2026-05-30-learning-coordinator-design.md) (v1 — roles, invariants, loop shape, substrate F1–F7, all still in force)

> This v2 keeps every decision and invariant of the v1 spec. It **replaces the algorithm in v1 §7**
> with a GEPA-faithful design, **grounds the Phoenix I/O (v1 §9 / F5) in the real Phoenix data model
> and MCP surface**, and **adds a pluggable-intelligence layer + efficacy harness** so the loop's
> *effectiveness* (not just its mechanics) is measurable offline using a real model (Claude) as an
> independent drafter/judge/reflection intelligence — no GCP required.

---

## 0. Two locked decisions (from PM, 2026-05-31)

| # | Decision |
|---|----------|
| **V2-D1** | **Engine = bespoke GEPA-faithful.** We implement GEPA's algorithm ourselves (reflective mutation, instance-wise Pareto frontier, system-aware merge, minibatch reflection + held-out scoring), tailored to our differentiators: signal read **from Phoenix** (INV-1), the **anti-cheating firewall** (laundered notes only, INV-2), **per-rubric-dimension** credit assignment, and **human-approved** promotion. No DSPy dependency. |
| **V2-D2** | **Build offline now, validate on GCP later.** This plan builds the full coordinator machinery + an efficacy harness, all offline-testable. A companion plan does live validation (real Phoenix MCP reads, real models, measured lift, κ calibration, MCP-off counterfactual, demo capture). |
| **V2-D3** | **Pluggable intelligence.** Every LLM role (drafter, judge, reflection) is a Protocol with Stub / Gemini / **Anthropic(Claude)** backends, so efficacy can be measured *here* with Claude as an independent, cross-model intelligence. |

GEPA reference: Agrawal et al., *"GEPA: Reflective Prompt Evolution Can Outperform Reinforcement
Learning"* (arXiv 2507.19457, ICLR 2026 oral). Headline: +10% vs GRPO / +14% vs MIPROv2 at up to 35×
fewer rollouts, with a *lower* val→test generalization gap — the last point is why it suits our 10+10
benchmark.

---

## 1. Why GEPA, mapped to Heuristics

GEPA's four mechanisms map almost 1:1 onto what the substrate already produces:

| GEPA mechanism | Heuristics realization |
|---|---|
| **Reflective mutation** — an LLM reads execution traces + *natural-language feedback* `feedback_text` and proposes a new instruction for one module | The judge panel already emits per-dimension **laundered `improvement` notes** (INV-2) on each trace. The reflection LM reads {current component text, failing cases, those notes} and proposes an edited component. |
| **Instance-wise Pareto frontier** — track best score *per training instance*; sample next candidate from the non-dominated front, weighted by how many instances it wins | We keep a candidate pool keyed by **per-case composite** on the held-out-train slice; sample the parent to mutate from the Pareto front (anti-stagnation). |
| **System-aware merge** (≤5×) — combine complementary lineages that improved *different* modules | Our components are `{global drafter prompt} ∪ {per-(insurer×denial_type) playbooks}`. Two lineages that improved *different* slices/dimensions merge cleanly. |
| **Minibatch reflect + full-val score** — reflect on b≈3 cases, accept only if it helps, then score on the Pareto/validation set | Reflect on a minibatch of failing train cases; score candidate on the frozen **held-out** set with the **frozen judge config** (v1 §7.5). |

**Component = "module" in GEPA terms.** Round-robin / weakest-first selection across:
`drafter_system_prompt` (global) and one component per touched `playbook[insurer×denial_type]`.
This gives clean credit assignment ("the appeal-vector reflection edited the Cigna×med-necessity
playbook").

**Per-dimension twist (our upgrade over vanilla GEPA).** GEPA reflects with whatever `feedback_text`
the metric returns. We structure that feedback **by rubric dimension**: the reflection prompt for a
component is told *which dimension is weakest on the minibatch* and is fed only that dimension's
laundered notes. This is the v1 "per-dimension specialist" idea, realized as **dimension-targeted
reflection** inside GEPA's single evolutionary loop (rather than N parallel optimizers + a merge step
of their own) — simpler, and it inherits GEPA's Pareto anti-stagnation for free.

---

## 2. Phoenix-grounded I/O (replaces v1 §9 hand-wave with the real data model)

Researched against Phoenix docs, the `arize-phoenix-client` Python package, and the
`@arizeai/phoenix-mcp` server. The Coordinator never talks to Phoenix directly; it goes through a
**`PhoenixLearningStore`** abstraction (one interface, two implementations: real + in-memory fake).

### 2.1 What Phoenix actually gives us

- **Spans/traces** carry OpenInference attributes (`span_kind`, input/output value+mime_type,
  `llm.model_name`, token counts, status, latency) plus **arbitrary metadata** — this is where our
  `{case_id, insurer, denial_type, slice, prompt_version, playbook_version, dataset_split,
  run_mode}` tags live (written in substrate F2). Read back via MCP `get-spans` / `get-trace` or
  the client's span query (dataframe with these columns).
- **Annotations / evaluations** — per-span records `{name, label, score, explanation,
  annotator_kind, metadata}`. The judge panel writes these in F2 (per-dimension score + the
  **laundered** improvement note as `explanation`; hard gates; `weighted_quality`; simulator
  verdict). Read back via MCP `get-span-annotations` or the client annotations API.
- **Datasets** — `benchmark_train`, `benchmark_holdout` (the 10+10 cases) as Phoenix datasets;
  examples are `{input, output, metadata}`. MCP `list-datasets` / `get-dataset-examples`.
- **Experiments** — `client.experiments.run_experiment(dataset, task, evaluators, dry_run=…)`;
  `task(example) -> output`, `evaluator(output, expected, metadata, …) -> {score,label,explanation}`
  (CODE or LLM kind). Read back via MCP `list-experiments-for-dataset` / `get-experiment-by-id`.
- **Prompts** — versioned registry: `upsert-prompt`, `get-prompt-version`,
  `add-prompt-version-tag`, `list-prompt-versions`. This is where each promoted `drafter_vN` /
  `playbook_vN` is registered (alongside the git-tracked file), giving Phoenix-native version
  history (v1 §4).

### 2.2 The `PhoenixLearningStore` interface (the only Phoenix contract the Coordinator depends on)

```python
class PhoenixLearningStore(Protocol):
    # --- READ (signal acquisition; INV-1: this is the only learning source) ---
    def read_scored_runs(self, *, dataset_split: str, prompt_version: str | None = None,
                         playbook_version: str | None = None) -> list[ScoredRun]:
        """Spans for a slice joined with their judge annotations → ScoredRun records
        (case_id, slice tags, per-dimension scores, hard-gate verdicts, weighted_quality,
        laundered improvement notes, simulator verdict). The Coordinator's gradient."""

    def read_prompt_version(self, component_id: str, version: str | None = None) -> ComponentVersion: ...
    def list_prompt_versions(self, component_id: str) -> list[ComponentVersion]: ...

    # --- WRITE (experiments + promotion) ---
    def run_experiment(self, *, dataset_split: str, candidate: Candidate,
                       judge_config_version: str) -> ExperimentResult:
        """Run the candidate components over a FROZEN dataset split, scored by a FROZEN judge
        config. Returns per-case + aggregate composite. (Real: Phoenix Experiments. Fake:
        in-memory run via the injected drafter/judge clients.)"""

    def register_promotion(self, candidate: Candidate, audit: PromotionAudit) -> None:
        """On PM approval: upsert the new component version (git + Phoenix Prompts) + write the
        audit record."""
```

`ScoredRun`, `ComponentVersion`, `Candidate`, `ExperimentResult`, `PromotionAudit` are Pydantic
models (defined in the plan). The **fake** (`InMemoryPhoenixLearningStore`) mirrors these shapes
exactly — it's the same store the existing `InMemoryPhoenixRecorder` (substrate F2) writes into, so
the offline loop reads back its own recorded signal, closing the loop without Phoenix.

**INV-1 enforcement (load-bearing test):** with the store's `read_scored_runs` returning empty (the
"Phoenix-off" counterfactual), `propose_candidate` must raise/return *no promotable candidate*. A
unit test asserts this — the demo claim "disable Phoenix → learning halts" becomes a tested fact.

---

## 3. Candidate & component model

```python
class Component(BaseModel):
    component_id: str           # "drafter_system_prompt" | "playbook:Cigna:medical_necessity"
    kind: Literal["prompt", "playbook"]
    version: str                # "v3"
    text: str | None = None     # prompt body (kind=prompt)
    playbook: dict | None = None  # tactics/required_evidence/dimension_targets (kind=playbook)

class Candidate(BaseModel):
    parent_id: str | None       # lineage (for merge)
    components: dict[str, Component]   # the full set this candidate would promote
    origin: Literal["reflect", "merge", "restart", "seed"]
    dimension_targets: list[str]       # which rubric dims this candidate aimed to lift (credit)
    diff_summary: str                  # human-readable, for the HITL card
```

A candidate is a **complete component set** (so an experiment runs a coherent configuration), but a
reflect-mutation changes exactly **one** component (GEPA discipline → clean attribution + small diffs,
honoring the v1 diff-size cap).

---

## 4. The algorithm (replaces v1 §7)

```
COORDINATOR.optimize(slice_filter, budget):
  pool ← [ seed_candidate (current live components, read from store) ]
  scores[c][case] ← run_experiment(c) per-case composites on the held-out (Pareto) split
  while budget remains and not converged:
    # 1. SELECT parent from the instance-wise Pareto frontier (anti-stagnation)
    parent ← pareto_sample(pool, scores)          # §4.1
    # 2. SELECT component to mutate (round-robin, then weakest-dimension-biased)
    comp_id ← select_component(parent)             # §4.2
    # 3. ACQUIRE dimension-targeted signal from Phoenix (firewalled)
    sig ← acquire_signal(comp_id, slice_filter)    # §4.3  — laundered notes only (INV-2)
    minibatch ← sample(sig.failing_cases, b=3)
    weakest_dim ← argmin_dimension(minibatch)
    # 4. REFLECT → mutated component (the LLM step; pluggable intelligence)
    new_comp ← reflection_client.reflect(
        component=parent.components[comp_id], dimension=weakest_dim,
        minibatch=minibatch, laundered_notes=sig.notes[weakest_dim])   # §4.4
    child ← parent.with(comp_id ← new_comp, origin="reflect", dim_targets=[weakest_dim])
    # 5. ACCEPT only if minibatch improves (cheap gate before full scoring)
    if minibatch_score(child) <= minibatch_score(parent): continue
    # 6. SCORE child on the frozen held-out split w/ frozen judge config
    scores[child] ← run_experiment(child, judge_config_version=FROZEN)
    pool.append(child)
    # 7. MERGE (≤5×): combine two non-dominated lineages that improved different components
    if should_merge(pool): pool.append(system_aware_merge(pick_two_lineages(pool)))   # §4.5
    # 8. STAGNATION restart: if a dimension hasn't improved in K rounds, reflect "from scratch"
    if stagnant(weakest_dim, K): pool.append(restart_candidate(comp_id, weakest_dim))
  best ← argmax_composite(pool, held_out)
  return PromotionProposal(best, before=seed, deltas=per_dimension, diff=…, vetoes=check_gates(best))
```

### 4.1 Pareto sampling
Per held-out case `i`, find the best composite `s*[i]` across the pool; the frontier `P*` = candidates
achieving `s*[i]` for ≥1 `i`, with strictly-dominated ones pruned. Sample a parent from `P*` with
probability ∝ number of cases it wins. (Faithful to GEPA Alg. 2.) Guards against the greedy
single-best stall.

### 4.2 Component selection
Round-robin across components (so every slice/prompt gets updates), but within a round bias toward the
component whose touched cases have the **lowest weakest-dimension scores** — spend reflection where the
headroom is.

### 4.3 Signal acquisition + firewall (INV-2)
`acquire_signal` reads `store.read_scored_runs(...)` and exposes to the reflection step **only**:
per-dimension scores, hard-gate verdicts, and **laundered** `improvement` notes. A build-breaking test
(reuses substrate F6's firewall test) asserts no answer-key field (`expected_appeal_vectors`,
`exploitable_weaknesses`, `appeal_difficulty`) ever reaches the reflection input. The simulator verdict
is visible as context but is **never** an optimization target (INV-3).

### 4.4 Reflection (the pluggable-intelligence step) — see §5
Structured meta-prompt: `{role: "improve this component for dimension X", current component text,
the b minibatch cases (insurer-visible inputs + the draft + the per-dimension score + laundered note),
hard constraints (keep disclaimer/citation/no-exclamation rules; ≤200-token diff; don't target the
simulator)}`. Returns an edited component + a one-line rationale. **Critique-first** (diagnose before
editing), mirroring the simulator's AlphaEval discipline.

### 4.5 System-aware merge
Pick two non-dominated candidates from **different lineages** that edited **different** components;
produce a child taking each lineage's improved component. Detect conflicts (same component edited both
ways) and skip/escalate. Capped at 5 invocations (GEPA default).

### 4.6 Local-minima safeguards (kept from v1 §7.4, now GEPA-backed)
Pareto diversity (§4.1) · stagnation "from-scratch" restart · held-out validation (reward never
measured on reflected cases) · weak-but-improvable seed (INV-4).

---

## 5. Pluggable intelligence + efficacy harness (V2-D3)

### 5.1 Role Protocols (3 backends each)
| Role | Protocol | Stub (unit tests) | Gemini (prod/GCP) | **Anthropic / Claude (efficacy here)** |
|---|---|---|---|---|
| Drafter | `DrafterLLMClient` *(exists)* | `StubDrafterClient` | `GeminiDrafterClient` | `AnthropicDrafterClient` *(new)* |
| Judge | `JudgeClient` *(exists)* | `OfflineHeuristicJudgeClient` | `GeminiJudgeClient` | `AnthropicJudgeClient` *(new)* |
| Reflection | `ReflectionClient` *(new)* | `StubReflectionClient` | `GeminiReflectionClient` | `AnthropicReflectionClient` *(new)* |

Cloud/SDK imports stay **inside methods** (offline-safe), exactly like the existing clients. The
Anthropic backends use the `anthropic` SDK (added as an *optional* dependency) and a key from env;
absent the SDK/key they raise a clear, skippable error — same gating discipline as the GCP tests.

**Why Claude as the efficacy intelligence is a feature, not a hack:** the v1 spec accepts
Gemini-judges-Gemini and lists same-model self-enhancement bias as a risk (v1 §10). Driving the
efficacy harness with Claude as an **independent** drafter/judge/reflection model gives a *cross-model*
read on whether the learning is real, which is a stronger signal than any single-model loop.

### 5.2 Efficacy harness
A runnable entrypoint (`evals/part_a/efficacy_harness.py` + a thin CLI) that, given an injected
backend set, executes the **full** loop on the synthetic cases and reports:
`{baseline_composite, optimized_composite, lift, per_dimension_deltas, promoted_diff,
held_out_breakdown, generalization_gap}`. Backend-agnostic:
- **Stub backend** → deterministic; used in a fast unit test that asserts the harness *runs and a
  rigged "good" reflection produces a measurable lift* (mechanics + that the metric is wired right).
- **Anthropic/Claude backend** → real efficacy on this machine when an `ANTHROPIC_API_KEY` is set
  (auto-skips otherwise, like the GCP tests).
- **Gemini backend** → efficacy on the wired machine (companion plan).

### 5.3 No-key fallback: assistant-orchestrated efficacy pass
Even with no key, "our own intelligence" can drive a one-shot efficacy measurement: the harness's
LLM steps are filled by Claude **via subagents** (the orchestrating assistant dispatches drafter /
judge / reflection subagents on the real cases, feeds their structured outputs into the Coordinator's
pure functions, and reads out the lift). This is a manual validation run, not automated CI, but it
needs no key and exercises the real algorithm with real intelligence. Documented as a runbook.

---

## 6. Promotion / HITL (refines v1 §8.1)

`PromotionProposal` is the HITL artifact: before/after composite, per-dimension deltas, the component
diff, the experiment id, and the **veto flags** (held-out regression, safety-gate regression,
hallucination>0, `simulator_approve_but_judges_fail` (INV-3), diff>200 tokens). Part A: PM approves →
`store.register_promotion(...)` bumps the version (git + Phoenix Prompts) and writes a
`PromotionAudit`. **Zero autonomous writes to live components.** Part B (later, by config) swaps the
PM for the autonomy-ladder hard gates — same machinery (v1 §8.2).

---

## 7. Build scope (this plan) vs companion plan

**This (offline) plan builds & unit-tests:** the models (§3), `PhoenixLearningStore` Protocol +
`InMemoryPhoenixLearningStore` fake (reading the substrate's recorded signal), signal acquisition +
firewall (§4.3), `ReflectionClient` Protocol + Stub + (construction-only) Gemini/Anthropic backends,
dimension-targeted reflective mutation (§4.4), Pareto pool (§4.1), component selection (§4.2),
system-aware merge (§4.5), stagnation restart, the experiment runner (fake), promotion proposal +
veto gates + audit (§6), the loop orchestrator (§4), and the **efficacy harness** (§5.2) with the
stub-backed mechanics test. INV-1 (Phoenix-off halts learning) and INV-2 (firewall) get dedicated
build-breaking tests. Everything green offline, no GCP, no key.

**Companion (GCP/live) plan, deferred:** real `PhoenixLearningStore` over MCP/SDK; real Gemini
backends; real Phoenix Experiments; measured held-out lift (target +20%, v1 §12); κ≥0.6 judge
calibration; the live MCP-off counterfactual; the emergent DENY→APPROVE demo capture. The
Anthropic/Claude efficacy run (§5.2) can happen in *either* environment the moment a key exists.

---

## 8. Invariants (v1 INV-1..6 hold; v2 adds)

- **V2-INV-1** — the Coordinator depends only on `PhoenixLearningStore`; no direct Phoenix calls, no
  reads from local `eval/` files. (Makes INV-1 testable and keeps the fake/real swap clean.)
- **V2-INV-2** — reflection edits **one** component per mutation; the full candidate is what gets
  experiment-scored and (maybe) promoted. (Credit assignment + small diffs.)
- **V2-INV-3** — efficacy is reported on the **held-out** split the reflection never saw; the harness
  refuses to report lift measured on training cases.

---

## 9. Risks & open questions

- **RISK-V2-1** — bespoke GEPA may under-perform the reference on subtle points (e.g. merge timing).
  Mitigation: faithful to Alg. 1/2; the efficacy harness measures real lift so we'll *know*, not guess.
- **RISK-V2-2** — Anthropic backend adds a dependency + a second model family in the loop. Mitigation:
  optional dep, method-local import, skip-guarded; used for efficacy/reflection, not prod drafting.
- **OQ-V2-1** — should the *production* reflection LM be Claude (strong reflector, cross-model) even
  when the drafter/judges are Gemini? GEPA recommends a strong reflection model. Default: configurable;
  decide after the efficacy run shows which reflector yields more lift.
- **OQ-V2-2** — Phoenix Experiments vs a lighter "score the candidate over the dataset via our own
  runner then log results as a Phoenix experiment record." Default: use the client's `run_experiment`
  on the wired machine; the fake uses our own runner. Revisit if the Experiments API is awkward.
- Carryover: DEP-1 (MCP read auth on Arize cloud was flaky) and DEP-2 (live Gemini) remain the
  companion plan's gating prerequisites.
