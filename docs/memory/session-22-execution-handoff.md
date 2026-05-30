# Session 22 — Execution Handoff: build the learning-loop substrate (Plan 1)

> ✅ **COMPLETE (2026-05-30).** Plan 1 (substrate F1–F7) executed end-to-end, subagent-driven.
> All 9 tasks done; acceptance suite green offline — `26 passed` for
> `tests/unit/aegis_v1 tests/unit/evals tests/unit/agent`. Commits `2a5e9c3..ab1bcd2` on `main`
> (not pushed to `origin`). Outcomes & deltas-from-plan recorded in
> [learnings.md](learnings.md) (Session 22 entry). **Next: write Plan 2 (the Learning
> Coordinator) — see "After Plan 1 → Plan 2" below; unblock DEP-1 (Arize MCP read auth)
> and DEP-2 (live Gemini/Vertex) first.**

**Created:** 2026-05-30 (end of Session 21) · **Mode:** subagent-driven execution
**Read this first if you are a fresh/compacted session about to start coding.**

---

## Mission

Execute **Plan 1 (substrate F1–F7)** end-to-end, **subagent-driven**:
[`docs/plans/2026-05-30-learning-loop-substrate-plan.md`](../plans/2026-05-30-learning-loop-substrate-plan.md).

This makes the Aegis self-improvement loop physically possible and observable: an evolvable
LLM drafter, the insurer simulator moved out of the agent, all judge/sim signal captured onto
Phoenix as a **laundered** (firewall-safe) annotation, and one `run_evaluated_case()` entrypoint that
closes the eval loop. The Learning Coordinator algorithm itself is **Plan 2 — do not build it now.**

## Bootstrapping read order (cold start)

1. [`orientation-map.md`](orientation-map.md) — what's built vs only designed, and the gaps.
2. [`docs/specs/2026-05-30-learning-coordinator-design.md`](../specs/2026-05-30-learning-coordinator-design.md) — the design + invariants (esp. INV-2 firewall, INV-3 optimize-quality-not-verdict, INV-4 weak-but-improvable).
3. [`docs/plans/2026-05-30-learning-loop-substrate-plan.md`](../plans/2026-05-30-learning-loop-substrate-plan.md) — the 9 TDD tasks you will execute.
4. (Optional) `graphify-out/graph.html` or `/graphify query "…"` for repo structure.

## How to run it (subagent-driven)

1. Invoke the **`superpowers:subagent-driven-development`** skill and point it at the plan file above.
2. **One fresh subagent per task** (Tasks 1–9, in order — there are dependencies: T3 needs T1+T2; T4 needs T1; T8 needs T1–T7). Each subagent: implements the task's TDD steps, runs the listed test command, reports the actual output.
3. **Two-stage review between tasks** (per the skill): verify the test command genuinely passed (paste output), then check the diff against the task spec before moving on.
4. **Commit per task** using the commit line given in each task's final step. Tick the task's `- [ ]` checkboxes in the plan as you go.
5. Stop after Task 9; run the full acceptance suite (below) and report green/red.

## Hard constraints & gotchas (tell every subagent)

- **No GCP/Gemini/ADC on this machine.** Everything is unit-tested **offline** with `StubDrafterClient`, `OfflineHeuristicJudgeClient`, and `InMemoryPhoenixRecorder`. The real `GeminiDrafterClient`/`OtelPhoenixRecorder` are written but tested only for *construction* — **never make a live cloud call**; `run_simulator=False` in offline tests. Cloud impls keep their `google`/`phoenix`/`pandas` imports **inside methods** so the offline suite never imports them.
- **Test command (run from `backend/`):** `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest <path> -q`.
- **Task 5 ripple (the one cross-task break):** removing `simulator` from the agent (7→6 tools) and `simulator_result` from `AppealPackage` will break `tests/unit/agent/test_aegis_v1_agent.py` **and** likely `tests/unit/agent/test_aegis_v1_tools.py`. Update both: expect 6 tools, no `simulator` in the ordered flow, and stop asserting `AppealPackage.simulator_result` (the sim result now lives on `EvaluatedRun`).
- **Firewall is load-bearing (INV-2).** Task 9's `test_firewall.py` is *supposed* to be able to fail: the offline j6 judge leaks the answer key into `evidence_quotes`, and `laundered_signal()` (Task 6) is what strips it. If the firewall test fails, fix `laundered_signal`, not the test.
- **Keep v1 weak-but-improvable (INV-4):** the `drafter_v1.md` prompt is deliberately thin. Do not "improve" it — that's the Coordinator's job in Plan 2.
- **Offline test cases must use in-scope values** (`insurer="Cigna"`, `denial_type="Medical Necessity"`, `patient_profile.plan_funding_type="fully_insured"`) or the `safety_scope_gate` hard-fails before the panel runs. The plan's tests already do this; preserve it.
- **Pre-existing issue, not yours to fix here:** broad `tests/unit` may fail on a stale `from app.agent` import in `test_aegis_v1_agent.py` (Session 18 audit family). If you touch that file in Task 5, fix the import while you're there; otherwise scope your runs to the specific test paths.

## Task checklist (titles only — full steps in the plan)

- [ ] T1 — weak `drafter_v1.md` prompt + `DrafterLLMClient` protocol + `StubDrafterClient`
- [ ] T2 — deterministic guardrail post-filter
- [ ] T3 — rewrite `drafter()` → injected client + guardrails (kills the template)
- [ ] T4 — `GeminiDrafterClient` production path
- [ ] T5 — relocate Outcome Simulator out of the Student (6 tools); drop `simulator_result`
- [ ] T6 — `PhoenixRecorder` protocol + `InMemoryPhoenixRecorder` + `laundered_signal()`
- [ ] T7 — `OtelPhoenixRecorder` production path
- [ ] T8 — `EvaluatedRun` + `run_evaluated_case()` (closes the loop)
- [ ] T9 — firewall enforcement test + `playbooks/` convention doc

## Acceptance (Plan 1 done-when)

Run and report:
```
cd backend && env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1 tests/unit/evals tests/unit/agent -q
```
Expect all green. Then: the deterministic template is gone, the Student is 6 tools, `run_evaluated_case()`
produces `AppealPackage + PanelReport (+ optional simulator)` and writes a laundered signal onto a trace,
and the firewall test proves no answer-key string reaches the Student or the annotation.

## After Plan 1 → Plan 2 (next, separate session)

Write Plan 2 via `writing-plans` from spec §7–§8: per-dimension specialist optimizers + meta-merge,
Phoenix Experiments harness (frozen held-out + frozen judge config), Part A HITL promotion gate.
**Hard deps to unblock first:** DEP-1 (Arize MCP read auth for signal acquisition) and DEP-2 (live
Gemini/Vertex for the real drafter + judges).

## PM working agreement (carry forward)
- Non-technical PM; explain plain-English before technical choices; ask, don't assume on
  product/architecture/copy. Full autonomy on tests, internal refactors, tooling.
- Commit per task (rollback safety). This session's commits land directly on `main`; nothing pushed
  to `origin` unless asked.
