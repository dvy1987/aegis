# Session 23 — Execution Handoff: two-step transparent Outcome Simulator

**Created:** 2026-05-31 (end of Session 22 work) · **Mode:** subagent-driven execution
**Read this first if you are a fresh/compacted session about to start coding.**

---

## Mission

Execute the **two-step Outcome Simulator plan** end-to-end, **subagent-driven**:
[`docs/plans/2026-05-31-outcome-simulator-two-step-plan.md`](../plans/2026-05-31-outcome-simulator-two-step-plan.md).

This finishes PRD FR8 honestly. Today the simulator is a single opaque LLM call gated by a
`threshold=10` hack. After this plan: the LLM does only **critique-first fuzzy feature judgment**
(1/3/5 anchors + evidence), and a **deterministic published rule set**
(`eval/simulator_rules.json`) scores those features into APPROVE/DENY (weighted sum + must-have veto
+ 0.70 threshold). The verdict becomes a pure, auditable function of (LLM anchors, published rules).

## Bootstrapping read order (cold start)

1. [`orientation-map.md`](orientation-map.md) — what's built vs designed (note the Session-22 callout).
2. [`docs/specs/2026-05-30-outcome-simulator-two-step-design.md`](../specs/2026-05-30-outcome-simulator-two-step-design.md) — the design + invariants (INV-S1…S5).
3. [`docs/plans/2026-05-31-outcome-simulator-two-step-plan.md`](../plans/2026-05-31-outcome-simulator-two-step-plan.md) — the 6 TDD tasks you will execute.
4. (Optional) [`learnings.md`](learnings.md) Session-22 entry — the substrate this builds on.

## How to run it (subagent-driven)

1. Invoke **`superpowers:subagent-driven-development`** pointed at the plan file above.
2. **One fresh subagent per task** (Tasks 1–6, in order — dependencies: T3 needs T1+T2; T5 needs T1–T4; T6 needs T5). Each: implements the TDD steps, runs the listed test command, pastes the actual output.
3. **Two-stage review between tasks** (spec compliance, then code quality), then commit per task with the message given in the task's final step. Tick the plan's `- [ ]` boxes.
4. Stop after Task 6; run the acceptance command (below) and report green/red.

## Hard constraints & gotchas (tell every subagent)

- **No GCP/Gemini/ADC on this machine.** Everything is unit-tested **offline** with `StubSimulatorClient` + `StubDrafterClient`. The real `GeminiSimulatorClient.assess` is written but tested for *construction only* — **never make a live call**. Cloud imports stay **inside methods**.
- **Test command (from `backend/`):** `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest <path> -q`.
- **Task 1 ripple (handled in-plan):** dropping the old `SimulatorResult.features` field breaks two existing `["features"]` assertions — Task 1 Step 4 neutralizes them. Pydantic v2 ignores the unknown `features=` kwarg the old `simulate()` still passes, and int→float coercion keeps old `score`/`threshold` assertions passing, so nothing else breaks. Run **targeted test paths** in Tasks 1–4 (the per-task commands already do); the broad suite is restored green at Task 5.
- **Task 5 is the breaking swap (one commit):** removing `simulate` + the `StubSimulatorClient(verdict=, score=)` constructor breaks `test_appeal_orchestrator`, `test_appeal_route`, `test_evaluated_run`, `test_aegis_v1_tools`, `test_simulator_client`. The plan updates all of them in the **same** Task 5 commit so the suite stays green. Do not split it.
- **Determinism facts to preserve:** `uniform_assessment(1)` → score **0.2** → DENY (must-have veto); `uniform_assessment(5)` → score **1.0** → APPROVE. Worked examples in the plan: weak-v1 = 0.38 (DENY), must-have-veto-despite-high-score = 0.84 (DENY). Tests assert these exact numbers.
- **INV-S2/S3 (transparency, critique-first):** the LLM (`assess`) emits critique + per-feature 1/3/5 marks **only** — never a score or verdict. The verdict is computed by `score_outcome`.
- **INV-S4 (insurer-visible only):** `assess(denial_text, clinical_context, appeal_letter)` — never pass synthetic provenance / answer key. One path for prod and eval.
- **INV-S5 (no hand-tuning):** weights/threshold are published and principled, then *verified* — never tuned to force the demo arc. Weak-v1 DENYs on genuine feature gaps.
- **Don't touch the safety gates:** PII/disclaimer/length stay in `self_check`/`deterministic_gates.py`; the simulator does not include them.

## Task checklist (titles only — full steps in the plan)

- [ ] T1 — feature/score models + `SimulatorResult` (float score + breakdown); neutralize stale `features` assertions
- [ ] T2 — rewrite `eval/simulator_rules.json` into the approval rubric + `load_simulator_rules`
- [ ] T3 — deterministic `score_outcome` (weighted sum + must-have veto + threshold + gaps)
- [ ] T4 — add `SimulatorClient.assess` + `StubSimulatorClient.assess` + `uniform_assessment` + `GeminiSimulatorClient.assess` (additive)
- [ ] T5 — rewire `simulator()` to assess→score; remove old `simulate`/threshold-10; update all consumer tests (one commit)
- [ ] T6 — update live integration test for the new shape; full offline acceptance

## Acceptance (done-when)

```
cd backend && env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1 tests/unit/evals tests/unit/agent -q
```
Expect all green. Then: the LLM emits only critique + 1/3/5 marks; `score_outcome` is a pure tested
function; `eval/simulator_rules.json` is the published rubric; the `threshold=10` hack and old
`simulate` path are gone; `simulator()` / `POST /v1/appeal` / `run_evaluated_case` all return the
transparent `SimulatorResult` (verdict + float score + feature_scores + gaps + critique). And
`tests/integration` **skips** cleanly without ADC.

## After this plan
- **Deferred (not this plan):** per-insurer rule sets; live-Gemini calibration of weights/threshold
  against the benchmark (DEP: GCP — verify, never hand-tune); any Learning-Coordinator evolution of
  the rubric (that's Plan 2, the Coordinator itself, which still needs DEP-1 Arize MCP read auth +
  DEP-2 live Gemini).

## PM working agreement (carry forward)
- Non-technical PM; explain plain-English before technical choices; ask, don't assume on
  product/architecture/copy. Full autonomy on tests, internal refactors, tooling.
- Commit per task (rollback safety). Commits land on `main`; nothing pushed to `origin` unless asked.
