# Session 24 — Execution Handoff: build the Learning Coordinator + optimize its prompts using the Claude session as the intelligence

**Created:** 2026-05-31 · **Mode:** subagent-driven build, then assistant-orchestrated prompt optimization.
**Read this first if you are a fresh/compacted session about to start.**

---

## TL;DR for the next session

There are **no GCP/Gemini credentials and no `ANTHROPIC_API_KEY`** on this machine. That is not a blocker — it changes *how* we get real intelligence into the loop:

> **The Claude Code session itself is the intelligence.** You (the orchestrating assistant) drive the
> drafter / judge / reflection roles via **subagents** on the real synthetic cases. That is how we
> measure *real* held-out lift and how we *optimize the actual prompts* — not stubs, not an API key.

Two phases, in order:
1. **Build** the Learning Coordinator offline, subagent-driven, from the plan (12 TDD tasks, all green with stubs/fakes). This is mechanics — it proves the loop *runs*.
2. **Optimize** the prompts with real intelligence (you + subagents): run the GEPA reflective loop by hand over the real cases, measure held-out lift, and iterate the drafter prompt + the reflection meta-prompt until the lift is real and stable. This proves the loop *works*.

---

## Cold-start read order

1. [`orientation-map.md`](orientation-map.md) — what's built vs designed.
2. [`docs/specs/2026-05-30-learning-coordinator-design.md`](../specs/2026-05-30-learning-coordinator-design.md) — v1: roles, invariants (INV-1..6), the closed loop, substrate F1–F7 (done).
3. [`docs/specs/2026-05-31-learning-coordinator-v2-gepa-design.md`](../specs/2026-05-31-learning-coordinator-v2-gepa-design.md) — **v2: the GEPA-faithful algorithm, Phoenix-grounded I/O, pluggable intelligence + efficacy harness.** This is the design of record.
4. [`docs/plans/2026-05-31-learning-coordinator-offline-plan.md`](../plans/2026-05-31-learning-coordinator-offline-plan.md) — **the 12 TDD tasks you execute in Phase 1.**
5. GEPA paper for grounding: arXiv 2507.19457 (reflective mutation + instance-wise Pareto + system-aware merge).

---

## Phase 1 — Build the coordinator (subagent-driven)

1. Invoke **`superpowers:subagent-driven-development`** pointed at the offline plan above.
2. **One fresh subagent per task** (Tasks 1–12, in order). Dependencies: T3 needs T1+T2; T5/T6/T7/T8 need T1; T9 needs T1; T10 needs T2–T9; T11 needs T10; T12 needs all. Each subagent: implements the TDD steps, runs the listed test command, pastes the actual output.
3. **Two-stage review between tasks** (spec compliance → code quality), commit per task with the message in the task's final step (trailer included). Tick the plan's `- [ ]` boxes.
4. Acceptance after T12: `cd backend && env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit -q` → all green; no test makes a cloud/API call; cloud/SDK imports are method-local.

New package: `backend/app/learning/` (models, store, signal, reflection_client, selection, mutation, merge, gates, experiment, coordinator, efficacy_harness). Tests under `backend/tests/unit/learning/`.

**Build gotchas (already handled in the plan — tell each subagent):**
- The offline loop uses a **static seeded train signal**, so it improves the **single weakest dimension** via the **drafter prompt first** (round-robin selection still touches the playbook, but the same-dimension tag adds no extra score). Tests assert the *drafter prompt* version bumps — do not "fix" them to the playbook.
- `register_promotion` only appends a component version when it actually changed (no duplicate `v1`s).
- Stagnation "from-scratch" restart is **deferred** (only meaningful once signal is re-recorded between promotions — Phase 2 / live plan). Pareto diversity + held-out validation are the offline anti-stagnation guards.
- Gemini/Anthropic reflection backends are written but unit-tested **construction-only**; never call them.

---

## Phase 2 — Optimize the prompts with the session as the intelligence (the part the PM asked for)

This is a **manual GEPA run**: you perform the reflective-evolution loop using real Claude reasoning
(yourself + subagents) in place of an API-keyed model, on the real cases, and you **edit the actual
prompt files** to lift held-out quality. The coordinator's *pure* logic (scoring, Pareto, gates) is
reused; only the LLM steps are filled by you.

### What you are optimizing (two prompts)
1. **The Student's weak baseline** — `backend/app/aegis_v1/prompts/drafter_v1.md` (746 bytes today). This is the "weights" the loop learns. v1 is deliberately thin (INV-4). You promote it to `drafter_v2.md`, `v3`, … as it improves.
2. **The optimizer's own meta-prompt** — `build_reflection_prompt(...)` in `backend/app/learning/reflection_client.py`. Improving *this* makes future reflections better (meta-optimization). Tune it after you've seen a few reflections land.

### The data
- **Train slice** (reflection reads its laundered notes): `eval/cases/drafts/case_*.json`.
- **Held-out slice** (where lift is measured — V2-INV-3, never reflect on these): `eval/cases/drafts/test_case_*.json`.
- Judge panel + rubric: `backend/app/evals/part_a/` — `run_panel` (panel.py), `OfflineHeuristicJudgeClient` (llm_judges.py), `build_teacher_grading_packet` (teacher_packet.py), `deterministic_gates.py`; rubric anchors in `docs/evals/2026-05-27-aegis-appeal-rubric.md`; judge prompts in `eval/judges/part_a/`.

### The three roles, played by subagents (with the firewall intact)
| Role | Subagent gets | Subagent must NOT get | Returns |
|---|---|---|---|
| **Drafter** | the current drafter prompt + the case's **insurer-visible** fields only (denial text, clinical context) | the teacher answer key | an appeal letter |
| **Judge** (run per dimension or as a panel) | the letter + the **teacher grading packet** (`build_teacher_grading_packet`) — judges legitimately see the answer key | — | per-dimension 1/3/5 + hard gates + a **laundered** improvement note per dimension |
| **Reflection** | the current prompt + the **weakest dimension** + only the **laundered** notes for it | any answer-key field (`expected_appeal_vectors`, `exploitable_weaknesses`, `appeal_difficulty`, `synthetic_provenance`) | a revised prompt |

INV-2 firewall is the one thing you must police by hand here: **drafter and reflection subagents see only insurer-visible inputs + laundered notes; only judge subagents see the teacher packet.**

### The loop (one optimization round)
1. **Baseline (held-out):** dispatch drafter subagents to draft all `test_case_*` with the current
   `drafter_vN.md`; dispatch judge subagents → per-case composite via `composite_score`. Record
   `baseline_composite` + per-dimension means.
2. **Signal (train):** draft + judge all `case_*`; aggregate per-dimension means; pick the **weakest
   dimension**; collect its **laundered** notes.
3. **Reflect:** dispatch a reflection subagent (or do it yourself) with {current prompt, weakest
   dimension, laundered notes, the hard constraints from `build_reflection_prompt`} → a revised
   `drafter_v(N+1).md`. Critique-first: diagnose before editing; ≤~200-token diff; keep the
   disclaimer / citation-only / no-exclamation rules; do **not** target the simulator verdict (INV-3).
4. **Score the candidate (held-out):** re-draft + re-judge `test_case_*` with the revised prompt →
   `optimized_composite`. **Lift = optimized − baseline.**
5. **Gate + decide:** apply `evaluate_vetoes` (held-out regression, safety/hard-gate regression,
   `simulator_approve_but_judges_fail`, diff>200 tokens). If clean and lift>0 → promote (write
   `drafter_v(N+1).md`, bump the version referenced by the agent/loader). Else revise and retry.
6. **Iterate:** with the new prompt, the weakest dimension shifts; repeat from step 2 on the next
   dimension until held-out composite plateaus or you hit a satisfying lift (v1 §12 target: ~+20%,
   e.g. 0.55→0.75 on held-out, on cases the reflection never saw).

### Capture the run so it's reproducible (turn the manual run into a committed artifact)
- Save each subagent's draft / judgment / reflection as JSON under `eval/efficacy_runs/2026-06-../`
  (gitignore-free; these are the evidence the loop worked).
- Add lightweight **fixture-replay clients** (`FixtureDrafterClient` / `FixtureJudgeClient` /
  `FixtureReflectionClient`) that replay those JSONs into the coordinator's pure logic, and a test
  asserting the recorded run reproduces the measured lift. This converts a one-shot manual session
  into an offline regression test (no keys, deterministic).
- Write a short `docs/evals/2026-06-..-coordinator-efficacy-run.md`: before/after `drafter_v*` prompts,
  per-dimension deltas, the lift number, and which reflections worked — this is the demo/eval evidence.

### Why this is legitimate, not a hack
The v1 spec accepts Gemini-judges-Gemini and flags same-model self-enhancement bias (v1 §10). Using
**Claude (you) as an independent drafter/judge/reflection** is a *cross-model* efficacy read — stronger
than a single-model loop. When GCP/keys arrive, the companion plan automates the exact same loop with
Gemini + live Phoenix; the prompts you optimize here carry over.

---

## Hard constraints & gotchas (tell every subagent)

- **No GCP/Gemini/ADC, no `ANTHROPIC_API_KEY`.** Phase 1 is fully offline with stubs/fakes. Phase 2's
  "intelligence" is subagents, not an API. Never attempt a live cloud/API call.
- **Test command (from `backend/`):** `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest <path> -q`.
- `git commit` from the repo root; `cd back to backend/` before pytest. Commit per task. Commits land
  on `main`; nothing pushed to `origin` unless asked. Every commit message ends with the
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>` trailer.
- **Firewall (INV-2)** is enforced in code (Task 3) AND must be respected by hand in Phase 2 (drafter
  & reflection subagents never see the answer key).
- **INV-1:** the coordinator reads its gradient only via `PhoenixLearningStore`; with no signal,
  `optimize()` returns `None` (tested). In Phase 2 the "store" is the recorded drafts+judgments.
- **INV-3:** optimize the judge composite, never the insurer APPROVE/DENY. A patch that flips the
  simulator to APPROVE while a hard gate fails is a veto, not a win.

## Acceptance (done-when)

- **Phase 1:** `cd backend && env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit -q` all green;
  the 12 tasks' boxes ticked; INV-1 (no-signal halt), INV-2 (firewall), V2-INV-2 (one component/child),
  V2-INV-3 (held-out only) each have a passing test.
- **Phase 2:** a recorded, reproducible efficacy run showing **measured held-out lift** from an
  optimized `drafter_v2+` (and a refined reflection meta-prompt), captured as fixtures + a short
  efficacy-run doc, with the firewall respected throughout.

## Deferred to the companion (GCP/live) plan
- Real `PhoenixLearningStore` over MCP/SDK; real Gemini drafter+judge+reflection; Phoenix Experiments +
  Prompts registry; κ≥0.6 judge calibration; the live MCP-off counterfactual; the emergent
  DENY→APPROVE demo capture. The prompts optimized in Phase 2 are the starting point there.

## PM working agreement (carry forward)
- Non-technical PM; explain plain-English before technical choices; ask, don't assume on
  product/architecture/copy. Full autonomy on tests, internal refactors, tooling.
- Commit per task (rollback safety). Nothing pushed to `origin` unless asked.
