# Learnings

Known patterns and gotchas. Newest at the bottom. Each entry is dated and cites evidence.

---

## 2026-05-30 — Structural audit (Claude, via `/graphify`)

Findings from a full-repo knowledge-graph analysis. See
[orientation-map.md](orientation-map.md) for the complete synthesis and `graphify-out/` for the
queryable graph.

- **The submission thesis is unbuilt.** Part B's swarm runtime (`backend/app/aegis_swarm/agent.py`)
  is a 15-line stub, and there is no `learning_coordinator.py` / `pattern_synthesizer.py`. The
  self-improvement loop — the whole Arize-track pitch — exists only in docs.
- **`phoenix_mcp_lookup` is a stub** returning hardcoded `cold_start`/`disabled` values. The demo
  counterfactual ("disable Phoenix MCP → quality collapses") cannot be demonstrated until the live
  wiring (T4.1) is done. Treat the "load-bearing" claim as *aspirational until T4.1 lands*.
- **Gotcha — blueprint/reality layout drift.** The architecture spec (§9) describes
  `backend/src/agent/orchestrator.py`, `researchers/`, `learning/`, etc. The real code lives in
  `backend/app/{aegis_v1,aegis_swarm,case_generator,evals}`. Trust the code, not the spec's tree;
  the spec needs reconciling.
- **Gotcha — missing dirs.** `playbooks/` and `proposals/` (referenced throughout the architecture
  and HITL design) do not exist on disk. Any code assuming they're present will fail.
- **Same-model judging is the accepted reality.** The G1 plan for a different-family
  (Claude-on-Vertex) critic was dropped; Gemini judges Gemini. Lean on deterministic gates +
  κ≥0.6 calibration as the only bias mitigations.
- **Environment gotcha.** Some dev machines have **no GCP/Gemini/ADC**. On those, Vertex case
  generation, live judging, and agent runs cannot execute — only the offline-heuristic judge
  (`OfflineHeuristicJudgeClient`) and the deterministic v1 pipeline run locally. Check for ADC
  before assuming a cloud path works.
- **Onboarding shortcut.** A `/graphify` graph of the repo persists in `graphify-out/`. Use
  `/graphify query "<question>"` and `/graphify --update` instead of re-reading the corpus.

---

## 2026-05-30 — Plan 1 substrate executed (Session 22, Claude, subagent-driven)

Executed [the substrate plan](../plans/2026-05-30-learning-loop-substrate-plan.md) (F1–F7). All 9
tasks done; `26 passed` offline for `tests/unit/{aegis_v1,evals,agent}`. Commits `2a5e9c3..ab1bcd2`
on `main`. Key facts and deltas-from-plan for whoever builds Plan 2:

- **Prompts are now colocated per backend** (PM-approved during execution). Part A weak baseline:
  `backend/app/aegis_v1/prompts/drafter_v1.md`; Part B swarm prompts (incl. the original 210-line
  drafter): `backend/app/aegis_swarm/prompts/`. The shared `backend/src/prompts/` dir is **retired**.
  `case_generator/prompts/` already used this pattern. `drafter_client.PROMPT_DIR` = colocated dir.
  *Why it matters:* the plan wrongly treated `drafter_v1.md` as new — it had overwritten a real swarm
  prompt; nothing in code had ever loaded `src/prompts/*`, so the move was safe.
- **`drafter()` now defaults to a LIVE Gemini client.** Calling `drafter()` / `run_aegis_v1_pipeline()`
  with no `client`/`drafter_client` will attempt a Vertex call. **Offline code/tests MUST inject
  `StubDrafterClient()`.** Unlike `simulator()`, the drafter has **no** try/except fallback.
- **T3 and T4 are coupled** (committed together in `afadeae`): `drafter()`'s function-body import
  pulls in `GeminiDrafterClient` unconditionally, so T3's test can't be green without T4. The
  plan/handoff listed only "T4-needs-T1".
- **Pipeline `drafter_client` threading (plan T8 step 4) was pulled forward into T5** — needed so the
  pipeline test stays offline once the drafter went live.
- **`ParsedCase.denial_type` is a snake_case Literal** (`medical_necessity`, …) distinct from the
  case/teacher-layer human string `"Medical Necessity"`. Test data must use the snake_case form.
- **Plan-2 follow-ups (known, deliberately deferred):**
  1. `panel.py:159` still reads `appeal_package.get("simulator_result", {})` → always `{}` for Part A
     now (simulator left the Student). Evaluator-disagreement detection is **inert**; pass the sim
     result into `run_panel()` explicitly (or compute it in `run_evaluated_case`) instead of probing
     the package.
  2. `laundered_signal()` filters `evidence_quotes` against the letter but passes judge `reasoning`
     and `improvement` **verbatim** — a live Gemini judge could echo answer-key text there. Tighten
     before trusting the laundered signal as an Optimizer reward.
- **`playbooks/` now exists** (was a missing dir) with a `README.md` convention doc; `playbook_loader`
  still cold-starts when a slice file is absent.
