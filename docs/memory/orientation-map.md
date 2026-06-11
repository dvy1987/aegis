# Orientation Map — Heuristics

**Created:** 2026-05-30 (Claude, via `/graphify` structural analysis of the full repo)
**Status:** Active · derived snapshot
**Purpose:** A one-read orientation for any agent picking up Heuristics cold — what it is, what's
*actually built* vs. *only designed*, and where the real gaps are. This is a derived synthesis,
not a source of truth: when it disagrees with [current-state.md](current-state.md),
[PRD.md](../prd/PRD.md), or the [architecture spec](../architecture/2026-05-27-heuristics-arch.md),
those win. Re-derive with `/graphify --update` after significant code changes.

> A queryable knowledge graph of the whole repo lives in `graphify-out/`
> (`graph.html`, `GRAPH_REPORT.md`, `graph.json`). Run `/graphify query "<question>"` instead of
> re-reading 182 files. Rebuild incrementally with `/graphify --update`.

> **Update (2026-05-30, Session 22):** Plan 1 substrate (F1–F7) is now **built** — the drafter is an
> evolvable LLM client behind guardrails, the Student is 6 tools, the Outcome Simulator runs in the
> orchestration/eval layer (`run_appeal_with_outcome` / `POST /v1/appeal` / `run_evaluated_case`),
> prompts are colocated per backend (`aegis_v1/prompts/`, `aegis_swarm/prompts/`; `src/prompts/`
> retired), `playbooks/` exists, and `run_evaluated_case` writes a firewall-safe laundered eval signal
> to a `PhoenixRecorder`. Still unbuilt (Plan 2): the Learning Coordinator and live Phoenix MCP reads
> (`phoenix_mcp_lookup` is still a stub). Sections below predate this — see
> [learnings.md](learnings.md) Session 22 entry for specifics.

---

## 1. What Heuristics is (in one paragraph)

A submission for the **Google Cloud Rapid Agent Hackathon — Arize partner track**. Heuristics drafts
US health-insurance **appeal letters** and is meant to **measurably improve** at the task by
introspecting its own **Arize Phoenix** traces via the **Phoenix MCP** server. The single
differentiating thesis: **Phoenix MCP is "structurally load-bearing"** — disabling it in the demo
should make quality visibly collapse. Built by a non-technical PM driving AI coding agents
(Amp / Droid / Antigravity / Codex) across ~20 documented sessions.

## 2. The intended system (two nested phases)

- **Part A / MVP** — one ADK agent (the **Student**) calling **6 tools** in fixed order:
  `case_parser → corpus_retrieval → phoenix_mcp_lookup → playbook_loader → drafter → self_check`.
  As of Session 22 the `drafter` is an **evolvable LLM client** (offline stub / Gemini prod) behind
  deterministic guardrails — no longer a fixed template. The **Outcome Simulator** runs in the
  wrapping orchestrator (`run_appeal_with_outcome` / `POST /v1/appeal`) and the eval harness, never as
  a Student tool (separation of powers). Human approval for every learning promotion. Intentionally a
  **weak v1** so the demo can show a before/after lift (the "Weak-v1" rule, PRD §15.5).
- **Part B / Full Plan** — a **"12-agent swarm"** (honest count: 10 LLM agents + 1 judge panel +
  1 simulator + 2 background meta-agents = 14 components; see arch §3.1). Coordinator → parallel
  researcher fan-out (Insurer Intel, Policy Detective, Medical Necessity, Legal, Precedent) →
  Strategist → Drafter ↔ Adversarial Reviewer → Quality Judge Panel → Outcome Simulator. A
  **Learning Coordinator** performs *SkillOpt-style textual gradient descent* on prompts/playbooks,
  gated by a **competency autonomy ladder** (Apprentice → Journeyman → Master, with auto-demotion).

## 3. Supporting subsystems

- **Synthetic case generator** (`backend/app/case_generator/`) — producer→critic swarm with
  "Realistic Imperfection (Authentic Shoddiness)", externalised configs
  (`eval/{diversity_matrix,banned_topics,case_schema}.json`), AlphaEval-2026-compliant scoring.
- **Gumloop evaluator** (`gumloop/`) — a 17-critic + Final Arbiter twin that grades generated cases
  (conceptual mirror of the case_generator's `c_*` critics).
- **Part A judge panel** (`backend/app/evals/part_a/`) — 7 judges (j1–j7), deterministic gates,
  offline-heuristic + Gemini-swappable clients, and the **Anti-Cheating Firewall**
  (Student blind to answer key; Teacher sees provenance; Learner trace-only).
- **Frontend** (`frontend/`) — Next.js scaffold + hand-built design system (warm-paper/sage,
  Calm motion). Hero page only; the workbench UI (T6.2) is not built.

## 4. Build vs. design — verified state (2026-05-30)

| Subsystem | State | Evidence |
|---|---|---|
| Part A v1 pipeline (`aegis_v1/`) | **Built**, tests pass | `agent.py`+`pipeline.py`+`tools.py`+`schemas.py` (~816 LoC); `pytest tests/unit` 8 passed |
| Case generator + Gumloop critics | **Built** | `case_generator/` swarm; 21 draft cases in `eval/cases/drafts/` |
| Part A judge panel | **Built** (offline path) | `evals/part_a/`; 6 unit tests pass; live Gemini judging needs GCP |
| **Part B swarm runtime** | **STUB** | `aegis_swarm/agent.py` is **15 lines** — "to be expanded in Part B" |
| **Learning Coordinator / Pattern Synthesizer** | **Not built** | no `learning_coordinator.py` / `pattern_synthesizer.py` anywhere |
| **`phoenix_mcp_lookup` (load-bearing tool)** | **STUB** | returns hardcoded `cold_start`/`disabled`; T4.1 live wiring pending |
| `playbooks/` dir | **Exists** (Session 22: README + convention doc); `proposals/` still missing | `playbooks/README.md` present; `proposals/` not yet on disk |
| Corpus | **Thin/flat** | 4 markdown authorities vs the planned clinical/legal/precedent/insurer tree |

## 5. Key gaps & risks (ordered by leverage)

1. **The self-improvement loop — the entire submission thesis — is unbuilt.** Part B swarm and the
   Learning Coordinator are stubs/absent. The graph confirms this: `Learning Coordinator` is a
   top cross-community *bridge* node, yet has no implementing code.
2. **Phoenix MCP is not actually load-bearing in code yet.** `phoenix_mcp_lookup` is hardcoded, so
   the demo counterfactual ("toggle MCP off → quality collapses") cannot work until T4.1 lands.
3. **Blueprint ↔ reality layout drift.** Arch spec §9 describes `backend/src/agent/orchestrator.py…`;
   reality is `backend/app/{aegis_v1,aegis_swarm,case_generator,evals}`. Future agents keep drifting
   against the stale map — reconcile the spec to the real layout.
4. **Same-model judging.** Gemini judges Gemini drafts (the G1 "different-family critic" plan was
   abandoned). Mitigation is deterministic gates + κ≥0.6 calibration only — calibration still pending.
5. **Stale-reference debt.** Session-18 audit found 16 inconsistencies; Session-20 fixed the
   high-priority ones, but demo capture (T3.5), live MCP (T4.1), the generation trial, judge
   calibration, and the workbench UI (T6.2) remain open.
6. **Environment constraint:** the dev machine in use has **no GCP/Gemini/ADC**, so Vertex case
   generation, live judging, and agent runs **cannot execute locally** — only the offline-heuristic
   judge and the deterministic v1 pipeline run here.

## 6. Highest-leverage next moves

- Capture the **weak-v1 demo recording (T3.5) before any prompt improvement** — it is irrecoverable afterward.
- Make `phoenix_mcp_lookup` real against live traces (T4.1) — without it the headline claim is hollow.
- Ship a **minimum** learning loop (even Part-A offline `learn.py` with human approval) so
  "it improves" is demonstrable end-to-end.
- Reconcile the architecture spec's repo layout to the real `app/` structure.

## 7. Graph landmarks (from `graphify-out/GRAPH_REPORT.md`)

- **God nodes:** `_run_critic()`, `Final Arbiter`, `generate_one_case()`, `OfflineHeuristicJudgeClient`,
  `run_aegis_v1_pipeline()`, `run_panel()`, `Learning Coordinator`.
- **Bridge nodes (high betweenness):** `run_aegis_v1_pipeline()`, `_run_one (Part A)`,
  `Learning Coordinator` — the seams where the eval, runtime, and learning subsystems meet.
- 715 nodes · 1046 edges · 50 communities · 0% AMBIGUOUS edges.
