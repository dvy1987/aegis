# Design Spec — Aegis Learning Coordinator & Closed Self-Improvement Loop

**Date:** 2026-05-30 · **Status:** Draft (brainstorming output, pending PM review)
**Author:** Claude (brainstorming session) · **Skill:** `superpowers:brainstorming`
**Companion docs:** [architecture spec](../architecture/2026-05-27-aegis-arch.md) ·
[eval rubric v2](../evals/2026-05-27-aegis-appeal-rubric.md) ·
[orientation-map](../memory/orientation-map.md) · [PRD](../prd/PRD.md)

> This is a **design spec**, not an implementation plan. It defines *what* to build and *why*.
> The implementation plan (task breakdown) is the next artifact, produced via `writing-plans`.

---

## 1. Context & problem

Aegis's entire Arize-track thesis is a **self-improvement loop**: the appeal agent gets
*measurably better* by learning from its own Phoenix traces. As of 2026-05-30 that loop does not
exist, and three structural facts block it (verified against code):

1. **The drafter is deterministic Python templating** (`aegis_v1/tools.py:drafter()`), so there is
   no prompt surface to evolve — the agent is at a *fixed point*, not a local minimum.
2. **The judge panel's output never reaches Phoenix.** `app_utils/telemetry.py` only
   `auto_instrument`s raw LLM/tool I/O; the rich `PanelReport` (per-dimension scores, judge
   reasoning, `improvement` notes, `appeal_vector_capture`, hard gates, `evaluator_disagreement`)
   is discarded.
3. **The pipeline and the judge panel are not connected** — nothing joins an `AppealPackage` with a
   `TeacherGradingPacket`, runs the panel, and writes results back to Phoenix.

This spec closes the loop end-to-end: it gives the agent an **evolvable surface**, **captures the
eval signal onto Phoenix traces**, and adds a **Learning Coordinator** that reads that signal *from
Phoenix* and proposes improvements. It deliberately keeps the v1 agent **weak-but-improvable**
(thin starting prompt, empty memory — a low start with real headroom) so genuine improvement is
demonstrable.

### Locked decisions (from brainstorming)

| # | Decision |
|---|----------|
| D1 | Drafter becomes an **LLM call** driven by an evolvable system prompt + injected playbook + Phoenix memory. Deterministic *guardrails* (disclaimer, citation-only, no-exclamation) remain as a post-filter. |
| D2 | Scope = **full closed loop** (substrate fixes F1–F6 + the Coordinator). |
| D3 | **Part A offline** (manual trigger, human-approved promotion) first, **architected to become Part B** (autonomous) by config — no rewrite. |
| D4 | Learnable surface = **Drafter system prompt (global) + per-(insurer×denial_type) playbooks (local)**. |
| D5 | Primary objective = **honest held-out composite lift** (~+20%, e.g. 0.55→0.75). Demo arc & MCP-off collapse must be genuine consequences. |
| D6 | Runtime = **Gemini/Vertex target + offline test harness** (OfflineHeuristicJudge + stubbed LLM); no cloud calls in local dev. |
| D7 | Algorithm = **per-dimension specialists + meta-merge** (rubric-dimension decomposition), with mini-beam + stagnation restart + held-out validation as local-minima safeguards. |
| D8 | Part A HITL = Coordinator **proposes + runs the held-out experiment**; **human approves promotion**. |
| D9 | **Phoenix is load-bearing for learning** (not just runtime): all training signal, experiments, and prompt versions live in Phoenix; the Coordinator reads via MCP (SDK fallback). |
| D10 | **Five-role separation of powers** (below). Optimizer is blind to the answer key. |
| D11 | **Outcome Simulator moves out of the Student pipeline into the eval layer.** Student = 6 tools. Simulator is a guardrail + demo signal, **never the learning target**. |

---

## 2. Invariants (must hold for every change downstream)

- **INV-1 — Phoenix is load-bearing for learning.** The Coordinator's gradient signal, candidate
  comparisons, and version history come *from Phoenix* (MCP-first, Phoenix-client SDK fallback).
  No learning from local `eval/` files or a side database. **Disable Phoenix/MCP → learning halts**
  (distinct from, and additional to, the runtime MCP counterfactual).
- **INV-2 — Anti-Cheating Firewall.** Student and Optimizer never see `expected_appeal_vectors`,
  `exploitable_weaknesses`, `appeal_difficulty`, or any answer-key field. The Optimizer reads only
  **laundered** per-dimension `improvement` notes surfaced through Phoenix. A build-breaking test
  asserts this.
- **INV-3 — Optimize quality, not the insurer verdict.** The learning target is the **judge
  composite** (`weighted_quality` + hard gates). The simulator APPROVE/DENY is never a reward.
  A patch that flips simulator→APPROVE while judges→FAIL is a **promotion veto**, not a win.
- **INV-4 — Weak-but-improvable, not broken.** The v1 starting prompt is thin in *strategy*
  (no tactics, no memory) but produces structurally valid, safe, on-rubric letters. Improvement
  headroom is real and measured on held-out cases.
- **INV-5 — Separation of powers** (§3): the entities that *draft*, *score quality*, *predict the
  insurer outcome*, *propose patches*, and *approve promotions* are all distinct.
- **INV-6 — Honesty.** No overclaiming; the demo arc is an emergent consequence of measured
  quality gains, not a staged or self-optimized number.

---

## 3. Five-role separation of powers

| Role | Implemented by | Sees answer key? | Learning target? | On UX? |
|------|----------------|------------------|------------------|--------|
| **Student** | LLM Drafter (evolvable prompt + playbook + Phoenix memory) | No (INV-2) | — (it is *being* improved) | the appeal letter |
| **Quality Judges** | Deterministic gates + Quality Judge Panel (j1–j7) | Yes | **Yes** (composite) | quality breakdown |
| **Outcome Simulator** (insurance approver) | Transparent rules + 1 LLM feature-extraction call | No (rules only) | **No** — guardrail + demo signal | APPROVE/DENY flip |
| **Optimizer** | Per-dimension specialists + meta-merge | No (laundered notes) | — | internal |
| **Patch Approver** | Part A: PM · Part B: hard gates + autonomy ladder | sees experiment evidence | — | promotion audit |

Rationale for the two separations the PM specifically asked about:
- **Simulator ≠ Judges:** different questions ("would the insurer approve?" vs "how good is this
  letter?") against different ground truths; they legitimately diverge, and the divergence is itself
  signal (`evaluator_disagreement` flags). Collapsing them invites optimizing the transparent rule
  proxy (Goodhart) and makes the demo flip circular.
- **Patch-Approver ≠ Judges:** no marking your own homework. The approver applies checks the judge
  never makes — **held-out generalization**, safety-regression veto, diff-size cap, calibration
  sanity, evaluator-disagreement veto — and its decision rule is **mostly non-LLM** so judge bias
  (we accept Gemini-judges-Gemini) cannot propagate into promotions.

---

## 4. The evolvable surface ("weights")

### 4.1 Global: Drafter system prompt
- Versioned file `backend/src/prompts/drafter_vN.md` **and** registered as a Phoenix Prompt.
- v1 is deliberately thin (INV-4). Each promotion bumps `N`.
- Injected at runtime into the LLM drafter call (F1).

### 4.2 Local: per-slice playbooks
- `playbooks/<insurer>__<denial_type>_vN.json` (git-tracked, versioned, Phoenix-registered).
- Schema: `{insurer, denial_type, version, tactics[], required_evidence[], dimension_targets{}, provenance{}}`.
  `dimension_targets` records which rubric dimension each tactic was added to improve (credit
  assignment + audit).
- Loaded by `playbook_loader` and injected into the drafter call. Cold-start = `status: "missing"`,
  empty tactics (so v1 starts weak).

### 4.3 Phoenix memory (read-only at runtime)
- `phoenix_mcp_lookup` returns per-slice `failure_patterns` + `success_traits` derived from past
  *traces + eval annotations* via MCP. Empty at cold start. This is a **runtime** input, not part
  of the evolvable weights, but it is the runtime load-bearing mechanism (and the same Phoenix data
  the Coordinator learns from).

---

## 5. The closed loop (data flow)

```
        ┌──────── git-tracked + Phoenix Prompts/registry ────────┐
        │  drafter_vN.md   playbooks/<insurer>__<denial>_vN.json   │
        ▼                                                          │
[StudentCasePacket] ─► Drafter(LLM: drafter_vN + playbook + phoenix_memory)
        │                        │                                 │
        │                        ▼                                 │
        │                  AppealPackage ──trace(tagged: slice, prompt_version,
        │                        │                playbook_version, dataset_split) ─► Phoenix
        │                        ▼                                                    │
        │   EVAL LAYER (independent of Student):                                      │
        │     • Quality Judges (gates + j1–j7) ─► PanelReport                         │
        │     • Outcome Simulator              ─► SimulatorResult                     │
        │                        │                                                    │
        │                        └── annotate trace (per-dim scores, gates,           │
        │                            laundered improvement notes, sim verdict) ──────►│
        │                                                                             │
   (Coordinator) ─── MCP read: failing held-out-train traces + per-dimension ─────────┘
        │             improvement notes + current prompt/playbook versions
        │   per-dimension specialists → targeted fragments → META-MERGE → candidate vN+1
        ▼
   Phoenix Experiment: candidate vN+1 vs vN on FROZEN held-out set, FROZEN judge config
        ▼
   Patch Approver  ── Part A: PM reviews before/after + diff → promote/reject
                   └─ Part B: hard gates + autonomy ladder decide
        ▼  on promote: bump version (git + Phoenix Prompts), write audit record
        └────────────────────────────► (loop)
```

---

## 6. Substrate fixes (F1–F6) — prerequisites bundled into this spec

- **F1 — LLM drafter.** Replace template `drafter()` with a Gemini call driven by `drafter_vN` +
  injected playbook + Phoenix memory. Deterministic post-filter enforces: exact disclaimer present,
  citations restricted to retrieved corpus IDs, no exclamation marks, schema validity. *Safety is
  not at the LLM's mercy.*
- **F2 — Judge→Phoenix wiring.** Write `AppealPackage`/`TraceMetadata` as span attributes; write
  `PanelReport` + `SimulatorResult` back onto the trace as Phoenix **evals/annotations** keyed by
  `case_id`/`trace_id`. Laundered `improvement` notes stored as annotations the Optimizer may read;
  raw answer-key fields never written to a Student/Optimizer-readable surface (INV-2).
- **F3 — Evaluated-run entrypoint.** A benchmark runner that, per case: builds the StudentCasePacket,
  runs the drafter pipeline → trace, builds the TeacherGradingPacket, runs the eval layer, annotates
  the trace. One command produces a fully-scored, Phoenix-resident run.
- **F4 — Real injection points.** Create `playbooks/` (dir + schema + versioned loader); make
  `phoenix_mcp_lookup` read real per-slice memory via MCP.
- **F5 — Coordinator I/O via Phoenix.** Reads via Phoenix MCP (Phoenix-client SDK fallback);
  candidate comparison via **Phoenix Experiments**; version history via **Phoenix Prompts**.
- **F6 — Firewall enforcement test.** Build-breaking assertion that answer-key fields never appear
  in Student or Optimizer inputs.
- **F7 — Simulator relocation (per D11).** Remove simulator from the 7-tool Student pipeline
  (Student = 6 tools ending at `self_check`); run it in the eval layer. Revise the v1 agent contract
  + `tests/unit/agent/test_aegis_v1_agent.py`.

---

## 7. The Learning Coordinator algorithm (per-dimension specialists + merge)

### 7.1 Signal acquisition (from Phoenix)
Query Phoenix (MCP) for the train slice: traces with `weighted_quality` below target or any hard-gate
FAIL, plus their per-dimension scores and laundered `improvement` notes, plus the prompt/playbook
versions that produced the best vs worst traces. Aggregate per rubric dimension.

### 7.2 Per-dimension specialists
One specialist per quality dimension (`grounding` 0.30, `appeal_vector_capture` 0.25,
`case_specific_clinical_rebuttal` 0.20, `evidence_completeness` 0.15, `persuasive_coherence` 0.10).
Each specialist:
- reads **only its dimension's** aggregated signal (the laundered notes + score distribution),
- proposes a **targeted fragment** — a prompt rule **or** a playbook entry scoped to that dimension,
- emits 2–3 **diverse** candidate fragments (mini-beam) to avoid greedy traps,
- records `dimension_targets` provenance for credit assignment.

Specialists run in parallel and are independent (clean attribution: "the appeal-vector specialist
added a 'hunt the specific denial defect' step").

### 7.3 Meta-merge
Compose non-conflicting fragments into one `drafter_vN+1` / `playbook_vN+1`. Detect conflicts (e.g.
persuasive-coherence "be concise" vs evidence-completeness "add detail") and resolve by dimension
weight; escalate unresolved conflicts to the approver. Cap total diff size (token budget).

### 7.4 Local-minima safeguards
- **Diversity:** mini-beam of 2–3 fragments per specialist.
- **Stagnation restart:** if a dimension fails to improve over K rounds, generate a
  "rewrite this dimension's guidance from scratch" candidate, unanchored to the weak phrasing.
- **Held-out validation:** reward is measured on cases the gradient did **not** touch (INV-3 + D5),
  so the loop cannot overfit the notes.
- **Weak-but-improvable start** (INV-4).

### 7.5 Experiment & evaluation
The merged candidate runs as a **Phoenix Experiment** against the current version, on a **frozen
held-out validation set**, scored by a **frozen, versioned judge config** (the approver's stable
yardstick — distinct from the live judge whose notes trained the patch).

---

## 8. Promotion / approval

### 8.1 Part A (now) — human-approved
Coordinator autonomously: acquires signal → proposes candidate → runs the held-out experiment →
presents **before/after composite + per-dimension deltas + the prompt/playbook diff + risk/veto
flags** to the PM. PM clicks promote or reject. **Zero autonomous writes to live prompts.**

### 8.2 Part B (later, by config) — autonomous
Same machinery; auto-promote only if **all** hard gates pass: composite lift ≥ +3% on held-out,
safety regression ≤ 0.05, hallucination rate = 0, adversarial/quality not regressing on any
dimension, no `simulator_approve_but_judges_fail` (INV-3 veto), diff ≤ 200 tokens, ≤5 promotions/day.
One-click rollback always available; auto-demote the autonomy stage if composite drops >10% over 10
runs. Apprentice → Journeyman → Master ladder per README thresholds.

### 8.3 Promotion audit (always)
Every promote/reject writes an audit record: candidate diff, experiment id, before/after numbers per
dimension, gates evaluated, approver (human id or "auto-gate"), timestamp. Stored git-tracked +
referenced from Phoenix.

---

## 9. Phoenix data model

- **Traces:** one per run, tagged `{case_id, insurer, denial_type, slice, plan_type, state,
  prompt_version, playbook_version, dataset_split, run_mode, agent_role}`.
- **Annotations/Evals:** per-dimension scores, hard-gate verdicts, `weighted_quality`,
  `appeal_vector_capture`, `evaluator_disagreement`, simulator verdict, **laundered** improvement
  notes. Keyed to the trace.
- **Datasets:** `benchmark_train`, `benchmark_holdout` (current 10+10 synthetic cases; expandable).
- **Prompts:** version history per evolvable artifact (`drafter_vN`, playbook versions).
- **Experiments:** one per candidate (`exp_<slice>_<vN>_vs_<vN+1>`).

---

## 10. Anti-reward-hacking & failure modes

| Failure mode | Guard |
|--------------|-------|
| Optimize the transparent simulator (Goodhart) | INV-3: judges are the target; simulator is veto-only |
| Overfit the judge's notes | Held-out validation + frozen judge config for the gate (§7.5) |
| Same-model self-enhancement bias | Non-LLM approver gates; quote verification; calibration κ≥0.6 |
| Answer-key leakage into Student/Optimizer | INV-2 + F6 build-breaking test |
| Greedy local minimum | Mini-beam + stagnation restart + from-scratch candidate (§7.4) |
| Silent instrumentation rot | Trace-fidelity gate: runs missing required metadata excluded from benchmark |
| Merge conflicts degrade prompt | Conflict detection + weight-based resolution + diff cap (§7.3) |

---

## 11. Offline test harness (D6)

Entire control flow is unit-testable without GCP: `OfflineHeuristicJudgeClient` + a **stubbed LLM
drafter** (deterministic fake) + a **fake Phoenix client** (in-memory trace/annotation store
implementing the same read/write interface as MCP). Tests assert: loop closes, signal flows,
firewall holds (F6), promotion gates fire correctly, stagnation restart triggers. Real Gemini/Vertex
+ live Phoenix MCP are integration-tested in a GCP session.

---

## 12. Success metrics

- **Primary:** held-out composite lift v1→vN ≥ +20% (target 0.55→0.75), on cases the Optimizer never
  trained on.
- **Loop integrity:** with Phoenix/MCP disabled, the Coordinator cannot produce a promotable
  candidate (INV-1 demonstrated).
- **Per-dimension attribution:** each promotion names which dimension(s) it improved and by how much.
- **Demo arc:** at least one hero case flips weak-v1 DENY → improved-vN APPROVE as an *emergent*
  result of measured quality gains (not optimized directly).

---

## 13. Dependencies, risks, open questions

- **DEP-1 (hard):** MCP trace/annotation **read** must work against Arize cloud (current-state notes
  auth was flaky; SDK worked). Required for INV-1's MCP-first claim. Surfaced as a prerequisite.
- **DEP-2:** Live Gemini/Vertex access (T4.1) for real drafter + judges; absent on dev machine.
- **RISK-1:** 10+10 benchmark is small — held-out lift may be noisy. Mitigation: report per-dimension
  + confidence; expand benchmark if signal too noisy (ties to assumption A1, Day-5 gate).
- **OQ-1:** Should the frozen gate judge be a *different model family* than the drafter if/when one
  becomes available (G1 was abandoned)? Default: same model, frozen config, deterministic gates.
- **OQ-2:** Playbook granularity — strictly `insurer×denial_type`, or also a global meta-playbook
  (Pattern Synthesizer, Part B)? Default: per-slice now; meta-playbook deferred to Part B.

---

## 14. Out of scope

- Part B 12-agent runtime swarm (separate effort; this spec targets the v1 agent as Student).
- Pattern Synthesizer / cross-slice meta-playbook (Part B).
- Live filing, real PHI, non-commercial plans (permanent non-goals per README).
- Frontend workbench UI (T6.2) — consumes this loop's outputs but specced separately.
