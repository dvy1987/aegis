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

### Follow-up fixed same session — per-appeal Outcome Simulator re-wired (commit `280f7f4`)

Moving the simulator out of the Student (Task 5) left the per-appeal APPROVE/DENY **orphaned** — no
product path produced it (the served ADK agent is the Student; the frontend is a scaffold with no API
calls). Fixed *properly* (offline-buildable; live calls wait for GCP only):
- **`SimulatorClient`** protocol + `StubSimulatorClient` (offline) + `GeminiSimulatorClient` (live logic
  extracted from `tools.simulator`); `simulator()` now delegates to an injected client (mirrors
  `DrafterLLMClient`). Threshold-10 weak-v1 demo arc lives in `GeminiSimulatorClient`.
- **Product entrypoint:** `app.aegis_v1.appeal_orchestrator.run_appeal_with_outcome()` → returns
  `AppealRunResult{appeal_package, outcome}`. Runs Student then simulator; **no judges** (grading needs
  the teacher key — that stays in `run_evaluated_case`). The simulator runs in this orchestration layer,
  never as a Student tool (separation of powers, D11).
- **HTTP:** `POST /v1/appeal` (`app.aegis_v1.appeal_api`, included into `main_v1`), `Depends`-injected
  clients so it's offline-testable via `dependency_overrides`. This is the endpoint the UX should call
  per appeal (the frontend wiring is still to-do — frontend is currently a scaffold).
- **GCP-machine test:** `backend/tests/integration/test_live_appeal.py` runs the real Gemini
  drafter+simulator (and a real-Phoenix eval variant) end-to-end; auto-skips without ADC. Run it on the
  wired machine: `cd backend && env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/integration -q`.
  *(Note: `tests/integration/` also has pre-existing `test_agent.py`/`test_server_e2e.py` that need a
  live server and fail offline — not part of the offline `tests/unit` acceptance.)*
- Offline acceptance is now **35 passed** for `tests/unit/{aegis_v1,evals,agent}`.

---

## 2026-06-03 — Eval automation vs Gumloop faithful pass

**Source:** Cross-check of `run_true_gumloop_all_500.py` output against manual review on cases 02, 03, 05.

### What happened
- Goal: **faithful Gumloop** (18 prompts × 500 cases) with fix-and-re-evaluate until APPROVE/DISCARD.
- `backend/scripts/run_true_gumloop_all_500.py` (and earlier `run_gumloop_prompt_pass_batches_11_500.py`) reported **500 APPROVE**.
- Those scripts are **not** equivalent to running Gumloop's 18 LLM critic nodes. They implement a **narrow Python heuristic encoder** with false positives (e.g. `[REDACTED]` counted as `algo_boilerplate_fingerprint` while case-specific diagnosis remained in letter body).
- Known defects found in follow-up review: case_02 algo boilerplate, case_03 benefit-category dupes, case_05 male + postmenopausal in `clinical_context`, truncated APPEAL RIGHTS on some algo fixes, MCG year false negatives then false positives, etc.

### Rules for every future agent (non-negotiable)
1. **Never claim** "Gumloop complete," "500 APPROVE," or "corpus eval-ready" based on `run_true_gumloop_all_500.py` or batch scripts alone.
2. **Definition of done for eval:** Gumloop UI or PM-approved external chat running prompts 01–18 + arbiter 08, with saved per-case JSON — not script verdict counts.
3. **Do not present automation as chat-equivalent Gumloop** without stating the gap in the same message.
4. **`eval/gumloop_runs/true-swarm-500/`** and **`manual-llm-sample/11-500-full-swarm-batches/`** are **not** proof of quality — treat as draft hints only until PM re-runs.
5. Script output may be used for **grep-style defect lists** only after PM asks; fixes require PM-visible verification on a sample.

### Revisit when
- PM completes independent Gumloop pass and updates this entry with new source of truth for approved cases.
