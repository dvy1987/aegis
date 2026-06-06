# Plan — Showcase 3-Stage Live Evaluation (Pre-test → Train → Post-test)

**Date:** 2026-06-05
**Status:** Draft for PM approval
**Owner:** next build session
**Oracle-reviewed:** yes (architecture pressure-tested 2026-06-05)

---

## 1. What the PM asked for

Replace the single **"Run evaluation now (live)"** button on `/showcase` with a modal that walks through three stages:

1. **Pre-test** — pick a **test set** (one or more denial letters from `eval/cases/drafts/`). Run the appeal drafter + live Outcome Simulator (APPROVE/DENY) on each. **No learning loop. No Phoenix traces.**
2. **Train** — pick a **training set** (cases from drafts). Run the **full learning loop** in `aegis-v1` (the GEPA `LearningCoordinator`). This stage **does** use Phoenix + judges (that is how learning works).
3. **Post-test** — re-run the **same test cases** from stage 1 through the live simulator. **No learning loop. No Phoenix traces.**

Result: a clean before/after on a held-out test set where the only thing that changed is the training stage.

Plus: the PM can **Pause/Exit at any time**, and on exit the backend **kills the loop and stops everything**.

### Why this is the right shape
The test stages are a *measurement* (drafter + simulator only). The train stage is the *intervention* (the learning loop). Keeping traces and judges out of the test stages is what makes the before/after honest — the test set stays genuinely held-out and uncontaminated by the learning signal.

---

## 2. Decisions that need PM sign-off before building

These are surfaced per the PM working-agreement. One recommendation each.

| # | Decision | Options | Recommendation |
|---|---|---|---|
| D1 | **Pause vs Exit semantics** | (a) Exit/Cancel only — stops after the current model call, not resumable. (b) True pause/resume — needs durable state, much more work. | **(a)** for v1. Label the control "Stop after current step". True resume is out of scope. |
| D2 | **How the trained prompt reaches Post-test** | (a) In-session apply — the new candidate is used for stage-3 runs only, nothing global changes. (b) Full `promote()` — globally swaps the production prompt. | **(a)**. The showcase demonstrates *what the learned candidate would do*; it must not silently change the live `/appeal` product for everyone. Global promotion stays a separate HITL action. |
| D3 | **Single slice vs multi-slice training** | (a) Constrain train (and ideally test) to one slice `Insurer:denial_type` for v1. (b) Allow multiple slices, run optimize per slice. | **(a)**. The learned playbook component is slice-specific; mixing slices makes the before/after hard to interpret and multiplies runtime. |
| D4 | **Caps for demo safety** | Test ≤ 5 cases, Train ≤ 8 cases, `max_rounds = 1`. | Accept these caps. They bound runtime (each case = real Gemini calls) and keep cancellation latency low. |
| D5 | **One session at a time** | The backend allows a single active live-eval session; a second request gets a friendly "already running" message. | Accept. Matches the demo (one operator) and the Cloud Run single-instance constraint. |

---

## 3. Critical correctness constraints (from oracle review)

These are the traps that make or break the feature. Each becomes a task + a test.

1. **Test stages must be truly trace-free AND judge-free AND memory-free.**
   Skipping `OtelPhoenixRecorder` is *not enough*. `run_aegis_v1_pipeline()` also calls `phoenix_mcp_lookup()` (a Phoenix *read* — it would feed learned memory into the "before" run and contaminate the comparison), and the app globally auto-instruments Gemini calls via `setup_telemetry()` → `register(auto_instrument=True)` (spans get exported regardless of the recorder). Test mode must disable the Phoenix memory read and suppress span export around the drafter/simulator calls.

2. **No process-global env mutation for isolation.** The existing `/v1/showcase/evaluate` flips `PHOENIX_MCP_ENABLED` via `os.environ` inside a request. That is thread-unsafe and will corrupt a concurrent background job. Use **function parameters**, never env toggles, in the new code paths.

3. **Training must learn only from the selected training cases — not old Phoenix data.** Today `acquire_signal()` reads *all* runs for `dataset_split="benchmark_train"` in the slice. We must seed and read a **session-scoped split**: `dataset_split = f"showcase_train_{session_id}"`.

4. **Train and test sets must be disjoint.** Enforced server-side. Otherwise we "test on the training set".

5. **Cancellation cannot kill an in-flight Gemini call.** Cooperative checkpoints only. Cancellation latency = the longest current LLM call. Mitigate with low caps + `max_rounds=1`.

6. **Phoenix export is batched.** After seeding the training split we must `force_flush()` and then retry `acquire_signal()` for a bounded window before optimizing; if still empty, mark stage 2 `no_signal` and run post-test on the baseline.

---

## 4. Architecture

```diagram
╭──────────────────────────────────────────────────────────────╮
│ /showcase page — "Run live evaluation" → 3-stage modal        │
│  Stage 1 pick test set → Stage 2 pick train set → Stage 3     │
│  polls every 1–2s · Stop-after-current-step button            │
╰───────────────┬──────────────────────────────────────────────╯
                │ HTTP (getApiBase)
   ┌────────────┼─────────────────────────────────────────────┐
   ▼            ▼                  ▼                            ▼
GET /v1/      POST /v1/        GET /v1/                  POST /v1/
showcase/     showcase/        showcase/                 showcase/
cases         session          session/{id}              session/{id}/cancel
(catalog)     (create+start)   (poll progress)           (cooperative stop)
                │
                ▼
   ╭───────────────────────────────────────────────────────╮
   │ ShowcaseSessionManager (in-process)                     │
   │  dict[session_id → SessionState]  +  Lock               │
   │  ThreadPoolExecutor(max_workers=1)                      │
   │  threading.Event per session (cancel token)            │
   ╰───────────────┬───────────────────────────────────────╯
                   ▼ background worker runs 3 stages
   ┌───────────────┼───────────────────────────────────────┐
   ▼               ▼                                         ▼
 STAGE 1         STAGE 2                                  STAGE 3
 run_test_case   seed split → force_flush →               run_test_case
 (no traces,     acquire_signal →                         (candidate
  no judges,     coordinator.optimize(check_cancel) →     applied,
  no memory)     keep proposal.candidate (no promote)     no traces)
```

### Cloud Run guardrails (must be set for the background thread to run)
- `--max-instances=1` (already effectively the demo config; make it explicit)
- single uvicorn worker (ADK default — do not add gunicorn workers)
- **CPU always allocated** (`--no-cpu-throttling`) — otherwise the worker thread stalls after the create-session response returns and progress freezes. This is the single most important infra setting.

---

## 5. Backend changes

All paths under `backend/app/`.

### 5.1 New: test-only run path
**File:** `app/evals/part_a/test_run.py` (new)

```python
class TestCaseResult(BaseModel):
    case_id: str
    verdict: Literal["APPROVE", "DENY"]
    score: float
    threshold: float
    letter_excerpt: str
    gaps: list[str] = []

def run_test_case(
    case_obj: dict[str, Any],
    *,
    drafter_client=None,
    simulator_client=None,
    candidate: "Candidate | None" = None,   # stage-3 in-session prompt/playbook override
) -> TestCaseResult:
    # 1. drafter pipeline with memory OFF and traces suppressed
    # 2. simulator()
    # 3. NO recorder, NO run_panel, NO phoenix_mcp_lookup read
```

It calls `run_aegis_v1_pipeline(...)` with the new override knobs (5.2) and then `simulator(...)`, all inside the span-suppression context (5.3).

### 5.2 Pipeline knobs
**File:** `app/aegis_v1/pipeline.py` (edit `run_aegis_v1_pipeline`)

Add optional params, all defaulting to current behaviour:
- `use_phoenix_memory: bool = True` → when `False`, skip the `phoenix_mcp_lookup()` call and pass an empty/neutral summary to `draft_appeal`.
- `drafter_prompt_text_override: str | None = None` → raw prompt text for an unpromoted candidate.
- `playbook_override: dict | None = None` → raw playbook for an unpromoted candidate; when set, skip `playbook_loader`.

**File:** `app/aegis_v1/tools.py` (`draft_appeal`) — accept `prompt_text_override`; when present, pass it straight to `client.draft(prompt=...)` instead of `load_drafter_prompt(version)`. The drafter client's `draft()` already takes a `prompt` string, so this is a thin pass-through.

### 5.3 Span suppression helper
**File:** `app/app_utils/telemetry.py` (add)

```python
@contextmanager
def suppress_tracing():
    # OpenTelemetry context flag honoured by exporters
    from opentelemetry import context as otel_context
    from opentelemetry.instrumentation.utils import _SUPPRESS_INSTRUMENTATION_KEY
    token = otel_context.attach(otel_context.set_value(_SUPPRESS_INSTRUMENTATION_KEY, True))
    try:
        yield
    finally:
        otel_context.detach(token)
```
Verify the key name against the installed OTel version during build; fall back to setting `OTEL_SDK_DISABLED`-style suppression only inside the context if needed. Test-mode drafter + simulator calls run inside this context so no spans export to Phoenix.

### 5.4 Cancellation checkpoints
**Files:** `app/learning/coordinator.py`, `app/learning/experiment.py`

Add an optional `check_cancel: Callable[[], None] | None = None` param to `LearningCoordinator.optimize()` and `LiveExperimentRunner.run()`. Call it (no-op if `None`) at each checkpoint:
- before each seed run, before each GEPA round, before reflection, before each candidate/merge experiment run, and between cases inside `LiveExperimentRunner.run()`.

`check_cancel` raises `ShowcaseCancelled` (new, in `app/learning/`); `optimize()` lets it propagate. Because no global state is mutated until `promote()` (which we never call here), an abort is clean. Do **not** subclass the coordinator; do **not** try to kill threads.

### 5.5 Session-scoped training builder
**File:** `app/learning/run_live.py` (add `build_live_coordinator_for_cases`)

```python
def build_live_coordinator_for_cases(slice_filter, case_ids, train_split, *, max_rounds=1):
    # dataset built ONLY from the selected case_ids (filtered from drafts)
    # LearningCoordinator(..., train_split=train_split, holdout_split=train_split, max_rounds=max_rounds)
```
And a seeding helper that records the selected training cases into `train_split` with `run_evaluated_case(run_simulator=False)`, then `force_flush()`.

### 5.6 Session manager
**File:** `app/aegis_v1/showcase_session.py` (new)

- `SessionState` dataclass: `session_id`, `status` (`pending|running|cancelled|failed|done`), `stage` (`pre_test|train|post_test`), `progress` (per-stage counts), `pre_results: list[TestCaseResult]`, `post_results`, `train_summary` (before/after composite, delta, vetoes, `no_signal` flag), `error`, `created_at`.
- Module-level `dict` + `threading.Lock` + `ThreadPoolExecutor(max_workers=1)` + per-session `threading.Event`.
- `create_session(test_ids, train_ids, slice)` → validates (disjoint, single slice, ids in catalog, caps), rejects with 409 if one already active, submits the worker, returns id.
- `_run_session(...)` worker: stage 1 loop (`run_test_case`, check cancel between cases) → stage 2 (seed split → force_flush → retry `acquire_signal` → `optimize(check_cancel)` → keep `proposal.candidate`) → stage 3 loop (`run_test_case(..., candidate=proposal.candidate)`). Writes progress under the lock after each unit.
- `cancel_session(id)` sets the Event.
- TTL cleanup of finished sessions.

### 5.7 API endpoints
**File:** `app/aegis_v1/showcase_api.py` (extend the existing router)

- `GET /v1/showcase/cases` → catalog from `eval/cases/drafts/` (student-safe fields only: `case_id`, `insurer`, `denial_type`, `headline`, `denial_letter_text`, `clinical_context`; **no** answer-key fields). Supports optional `?slice=` filter.
- `POST /v1/showcase/session` → body `{ test_case_ids, training_case_ids, slice }` → `{ session_id }`. 400 on validation failure, 409 if busy.
- `GET /v1/showcase/session/{id}` → full `SessionState` snapshot for polling.
- `POST /v1/showcase/session/{id}/cancel` → cooperative stop; 200 with updated status.

Keep the old `/v1/showcase/evaluate` for now (the existing page path) until the modal replaces it; remove in a cleanup task once the modal ships.

---

## 6. Frontend changes

All paths under `frontend/src/`. Respect `frontend/AGENTS.md` (design tokens, Lucide via `@/icons`, no AI-marketing copy, no Phoenix/Gemini branding in UI, WCAG AA, `'use client'` where needed).

### 6.1 Data layer
**File:** `lib/data/live.ts` (add) — `listDraftCases(slice?)`, `createShowcaseSession(body)`, `getShowcaseSession(id)`, `cancelShowcaseSession(id)`, all using `getApiBase()`.
**File:** `lib/types.ts` (add) — `DraftCaseSummary`, `ShowcaseSessionState`, `TestCaseResult`, `TrainSummary` mirroring the backend models.

### 6.2 Modal component
**File:** `components/showcase/LiveEvalModal.tsx` (new) — a 3-step modal:
- Step 1: multi-select test cases (from `GET /v1/showcase/cases`, filtered to chosen slice).
- Step 2: multi-select training cases (same slice, disjoint from test — disable already-picked ids).
- Step 3 (running): live progress per stage from polling (`pre_test → train → post_test`), before/after verdict table, train delta + vetoes, a persistent **"Stop after current step"** button that calls cancel and closes cleanly.

**Recommended session flow:** collect *both* sets in steps 1–2, then `POST /session` to start all three stages server-side; the modal switches to a progress view and polls. This keeps the long work entirely server-driven and cancellable, and avoids the client orchestrating three separate long calls.

### 6.3 Wire into the page
**File:** `app/showcase/page.tsx` — replace the single `runLive` button with a "Run live evaluation" button that opens `LiveEvalModal`. Keep the existing recorded-bundle view below for the default case browsing.

---

## 7. Test plan (TDD — write these first where practical)

Backend (`backend/tests/unit/...`):
1. `run_test_case` calls neither `run_panel`, nor `OtelPhoenixRecorder`, nor `phoenix_mcp_lookup` (assert via mocks/spies). **Guards constraint #1.**
2. `run_test_case` returns a verdict/score from the simulator and a letter excerpt.
3. `run_aegis_v1_pipeline(use_phoenix_memory=False)` does not invoke `phoenix_mcp_lookup`.
4. `draft_appeal(prompt_text_override=...)` uses the override, not `load_drafter_prompt`.
5. Session validation: rejects overlapping train/test, multi-slice, ids not in catalog, over-cap, and second concurrent session (409).
6. Cancellation: a fake coordinator/runner that checks `check_cancel` aborts with `ShowcaseCancelled` and the session ends `cancelled` with no `promote()` call.
7. Session-scoped split: seeding writes `showcase_train_{id}` and `acquire_signal` is queried with that split.
8. `no_signal` path: when `acquire_signal` stays empty, stage 2 marks `no_signal` and stage 3 runs on baseline.

Frontend (`frontend/src/__tests__/...`):
9. Modal renders 3 steps; cannot select the same case as both test and train.
10. Polling renders progress + before/after table; "Stop after current step" calls cancel.
11. Firewall: catalog/test results never expose answer-key fields (extends existing frontend firewall test).

---

## 8. Build order (each step ends green + committed)

1. **Backend isolation primitives** — pipeline knobs (5.2), `draft_appeal` override, `suppress_tracing` (5.3), `run_test_case` (5.1) + tests 1–4.
2. **Cancellation checkpoints** — `check_cancel` into coordinator + runner, `ShowcaseCancelled` + test 6.
3. **Session-scoped training** — `build_live_coordinator_for_cases` + seed/flush helper + tests 7–8.
4. **Session manager + endpoints** — `showcase_session.py`, four endpoints, validation + tests 5. Catalog endpoint.
5. **Frontend data layer + types** (6.1).
6. **Modal + page wiring** (6.2, 6.3) + tests 9–11.
7. **Cloud Run config** — set `--no-cpu-throttling`, `--max-instances=1`; redeploy backend + frontend; smoke-test a small session (test=2, train=2) end to end including cancel.
8. **Cleanup** — remove old `/v1/showcase/evaluate` path + the page's old `runLive` if fully replaced.

---

## 9. Out of scope (v1)
- True pause/resume across page close or backend restart.
- Hard-killing in-flight Gemini calls.
- Multi-slice training in one session.
- Concurrent sessions / multi-instance Cloud Run.
- Persisting session results (in-process only; lost on restart — frontend treats a missing session as "expired").

## 10. Risks
- **CPU throttling not set** → progress freezes after create-session. *Mitigation:* explicit `--no-cpu-throttling` in step 7; smoke test.
- **OTel suppression key name differs by version** → spans still export. *Mitigation:* verify against installed package during step 1; test asserts no export.
- **Phoenix batching** → `acquire_signal` empty right after seeding. *Mitigation:* `force_flush()` + bounded retry + `no_signal` fallback.
- **Cancellation latency** = longest LLM call. *Mitigation:* caps (D4) + `max_rounds=1` + UI copy "Stopping after current model call…".
