# Backend Reliability Review — Heuristics v1 (showcase quick/serious + /appeal)

**Date:** 2026-06-07
**Reviewer:** Amp (analysis only — no code changes made)
**Scope:** "Will the deployed v1 backend silently break when the PM opens the frontend and runs a quick/serious showcase run?"
**Method:** Read the deployed code paths (drafter/simulator/judge/reflection clients, showcase runner + API, coordinator, deploy script, Dockerfile, session store), cross-checked against the Google Gen AI SDK / Vertex behavior and Cloud Run execution model, pressure-tested with the oracle, and probed the live deployment.

**Live deployment probe (2026-06-07):**
- `GET /health` → `{"status":"ok"}` ✅
- `GET /v1/showcase/manifest` → **HTTP 500** ❌ (this is finding #1, confirmed in production)

> Bottom line: the quick run cannot start today — the showcase **manifest endpoint already 500s on the live service**, before a single Gemini call. Even once that is fixed, there are several more issues queued behind it (model-name mismatch, Cloud Run background-thread throttling, multi-instance session state, no run-level rate-limit/retry). Each must be cleared for "open frontend → quick run just works."

---

## Priority-ordered findings

Severity: **P0** = breaks the quick run / data-corrupting · **P1** = breaks under load or in serious run · **P2** = latent risk.

### P0-1 — Deployed image does not contain `eval/`, `playbooks/`, or `corpus/` (CONFIRMED LIVE: manifest 500s)
**What:** The Dockerfile (`backend/Dockerfile`) only does `COPY ./app ./app` (+ a few root files), and the build context is `backend/` (`deploy-v1.sh` runs `gcloud run deploy --source .` from `backend/`). But the runtime reads assets that live at the **repo root**, i.e. *outside* the `backend/` build context:
- `showcase_manifest.py` → `REPO_ROOT/eval/benchmarks/v1_showcase_100/manifest.json` and `eval/cases/drafts/*.json`
- `llm_judges.py` → `REPO_ROOT/eval/judges/part_a/*.md`
- `tools.py` → `PLAYBOOK_DIR = REPO_ROOT/playbooks` and `CORPUS_DIR = BACKEND_ROOT/corpus`
- `phoenix_live.py` → `_PROMPT_DIR = /backend/app/aegis_v1/prompts` (double-prefix bug in-container) and `_PLAYBOOK_DIR = /playbooks`

In the container, `Path(__file__).resolve().parents[N]` resolves to `/`, so these become `/eval/...`, `/playbooks`, `/backend/app/...` — none of which exist in the image.

**Impact:**
- `GET /v1/showcase/manifest` and `POST /v1/showcase/runs/quick` → **500 immediately** (start handler calls `load_showcase_manifest()`). Quick run never begins. *(Confirmed: live manifest endpoint returns 500.)*
- Judge prompt load fails → training/optimize stage crashes once reached.
- Learning store seed (`coordinator._seed → store.read_prompt_version`) reads `/backend/app/.../prompts` → fails.
- `/appeal` degrades but does *not* crash: missing corpus → `citations_used: 0`; missing playbook → cold-start playbook. This matches the known "live runs return citations_used: 0" symptom and is consistent evidence that the corpus is absent in the container.

**Why it slipped through:** the `/showcase` *frontend* smoke test was HTTP 200 (static route); the backend *manifest* endpoint was apparently never curled post-deploy. Local tests pass because the repo layout is intact locally.

**Note:** because `eval/` and `playbooks/` are outside the `backend/` build context, the Dockerfile *cannot* simply `COPY` them — the build context or asset layout has to change (or assets baked under `app/`, or fetched from GCS at startup). Decision for the PM.

---

### P0-2 — Judge & reflection default to `gemini-3.1-pro` (no `-preview`); deploy sets no override
**What:** The working/available model is `gemini-3.1-pro-preview` (PM-confirmed). Drafter, simulator, and the ADK agent all default to `gemini-3.1-pro-preview` ✅. But:
- `GeminiJudgeClient` (`llm_judges.py:251`) defaults to `gemini-3.1-pro` (no `-preview`).
- `GeminiReflectionClient` (`reflection_client.py:99`) defaults to `gemini-3.1-pro`.

The showcase runner constructs both with **no model argument** (`GeminiJudgeClient()`, `GeminiReflectionClient()`), and `deploy-v1.sh` sets **no** `AEGIS_JUDGE_MODEL` / `AEGIS_REFLECTION_MODEL` env var. The FastAPI server (`main_v1.py`) does not load `.env`.

**Impact:**
- Judge calls a model ID that 404s, and `GeminiJudgeClient` has **no fallback** (unlike drafter/simulator which fall back to `gemini-2.5-pro` on 404). → training/optimize stage hard-crashes the run.
- Reflection 404s → caught and returns the component **unchanged** → optimizer finds "no improvement" → proposal can be `None` → run fails with `no_learning_signal` (silent, looks like "the model just didn't learn").

**Inconsistency also present:** `case_generator/config.py`, `aegis_swarm/client.py`, `aegis_swarm/agent.py` also default to `gemini-3.1-pro`.

---

### P0-3 — Background work runs in a daemon thread; Cloud Run CPU throttling not disabled
**What:** `showcase_api.py` launches runs via `threading.Thread(target=run_quick_session, daemon=True).start()` and returns the HTTP response immediately. `deploy-v1.sh` uses `--cpu 2 --memory 1Gi --min-instances 1 --max-instances 3 --timeout 300s --concurrency 8` and **does not set `--no-cpu-throttling`**.

A project plan doc (`docs/plans/2026-06-05-showcase-live-eval-3stage-amp-spec.md`) explicitly calls `--no-cpu-throttling` "the single most important infra setting" — but the actual deploy script omits it.

**Impact:** After the POST returns, Cloud Run throttles CPU to ~0 when no request is in flight. The worker thread (which makes ~180–220 sequential Gemini calls for quick; thousands for serious over many minutes) stalls. Progress freezes; the frontend polls a session that never advances. Daemon threads can also be killed on instance shutdown/redeploy with no resume.

---

### P0-4 — Showcase session state is per-instance `/tmp`, but `max-instances=3`
**What:** `showcase_session.py` writes sessions to `/tmp/aegis_showcase_sessions`. Deploy allows up to 3 instances with concurrency 8. `min-instances 1` does **not** pin request routing.

**Impact:** `POST /runs/quick` (creates session + thread) can land on instance A while polling `GET /runs/{id}`, `cancel`, or `approve` land on instance B → "session not found" / stale state / approve-on-an-instance-that-never-ran. `/tmp` is also ephemeral. Intermittent and confusing.

---

### P1-5 — No run-level rate limiting / retry / resume around Gemini calls
**What:** The Google Gen AI SDK does auto-retry transient `429/5xx` (≈5 attempts, exp backoff) — so a *single* blip is usually absorbed. But there is **no app-level** rate limiter, no run-level checkpoint/resume, and no degradation policy. Call volume is high and fully sequential:
- Quick run ≈ **180–220** Gemini calls.
- Serious run ≈ **3,500–4,500+** calls (80 train + 20 holdout, `max_rounds=3`, panel of 6 judges per case per candidate per round).
- `/v1/showcase/evaluate` ≈ **23** calls per request (baseline + candidate + counterfactual).

**Impact:** `gemini-3.1-pro-preview` is a preview model on shared/dynamic capacity — sustained bursts can exhaust SDK retries and surface a final `429 RESOURCE_EXHAUSTED` / `503`, which aborts the whole run (only caught at top-level `fail_stage`, no resume). Serious run is the most exposed. Two related silent-failure traps:
- Simulator swallows failures → returns a **weak** assessment (looks like a bad draft, not an outage).
- Reflection swallows failures → **no-op** edit (looks like "no learning").

---

### P1-6 — Long synchronous work inside HTTP handlers exceeds the 300s timeout
**What:** `approve_run` runs `approve_session` **synchronously** in the request: post-measure of holdout (quick = 2 cases ≈ 4 calls; **serious = 20 cases ≈ 40 sequential calls**). `/v1/showcase/evaluate` runs 3–4 evaluated cases synchronously (~23 calls). Deploy `--timeout 300s`.

**Impact:** Serious approve and `/evaluate` can exceed 300s → **504**. Worse, in `approve_session` the promotion (`register_promotion`) happens *before* post-measure — a 504 leaves a promoted candidate with no post-measurement (inconsistent state).

---

### P1-7 — Official judging may hard-gate every showcase case (stripped teacher metadata)
**What:** `showcase_runner._case_obj()` passes only `case_id, denial_letter_text, clinical_context, dataset_split`. But `build_teacher_grading_packet()` / `safety_scope_gate()` expect richer fields (`insurer`, `denial_type`, `patient_profile.plan_funding_type`, `synthetic_provenance`, `denial_pattern_sources`, …). `approve_session()` also does **not** check `proposal.is_promotable` before promoting.

**Impact:** Panel may hard-fail → `weighted_quality = None` → UI composites collapse to `0`; distorted learning signal; optimizer can return a vetoed candidate that gets promoted anyway. The run "completes" but shows no real lift — a silent demo failure. *(Flagged by oracle; worth verifying against the teacher-packet schema before relying on it.)*

---

### P1-8 — Phoenix learning-signal path is best-effort and can no-op
**What:** `OtelPhoenixRecorder.annotate()` swallows all exceptions; OTEL export is batched (background). `deploy-v1.sh` sets `PHOENIX_COLLECTOR_ENDPOINT` but `PHOENIX_HOST` only conditionally, and does not set `PHOENIX_CLIENT_HEADERS` (the CLI path does). The recorder comment notes the Phoenix client can misuse the collector endpoint as the API base URL unless `PHOENIX_HOST` is set.

**Impact:** Spans may exist but annotations don't land → `LivePhoenixLearningStore` finds no signal → quick run spends many Gemini calls and then fails `no_learning_signal`. Phoenix MCP is supposed to be load-bearing for the demo, so this is doubly important.

---

### P2-9 — Process-wide env mutation under concurrency
`evaluate_showcase()` temporarily sets `PHOENIX_MCP_ENABLED=false` via `os.environ`. With `--concurrency 8`, a concurrent request/run in the same process can observe MCP disabled → contaminated results. Should be request-scoped.

### P2-10 — Non-atomic session writes
`ShowcaseSessionManager._save()` uses direct `write_text()`. Concurrent worker/GET/cancel writes can yield partial-JSON reads (500) or lost cancel/approve. Use temp-file + atomic rename, or a real state store.

### P2-11 — ADK session state likely in-memory
If any ADK web/session endpoints are used, in-memory session state has the same multi-instance problem as P0-4.

---

## Recommendations (demo-safe path, in order)

These are scoped for "open the frontend and the quick run just works for the hackathon," not a production rebuild. **No code changes have been made.** Recommend doing them in this order:

1. **Fix asset packaging (P0-1).** Decide one approach with the PM:
   - (a) Move/copy `eval/`, `playbooks/`, `corpus/` under `backend/` (or under `app/`) so they're inside the build context and `COPY`-able, and fix the `parents[N]` path math + the `phoenix_live.py` `/backend/...` double-prefix; or
   - (b) Fetch these from GCS at container startup.
   Then **re-deploy and `curl /v1/showcase/manifest` (expect 200)** as the gating smoke test.
2. **Pin all model envs (P0-2)** in `deploy-v1.sh`: `AEGIS_DRAFTER_MODEL`, `AEGIS_SIMULATOR_MODEL`, `AEGIS_JUDGE_MODEL`, `AEGIS_REFLECTION_MODEL` all = `gemini-3.1-pro-preview`. (Cheapest single fix; also consider a judge fallback later.)
3. **Make Cloud Run demo-safe (P0-3, P0-4):** add `--no-cpu-throttling`, and for the demo use `--max-instances=1` (+ consider `--concurrency=1`) so the daemon thread keeps CPU and session `/tmp` state stays on one instance. Stopgap, not scalable.
4. **Keep approve/evaluate within timeout (P1-6):** either background `approve_session` like the runs, or raise `--timeout` (max 3600s) for the demo; and verify promotion isn't left half-done on timeout.
5. **Make Phoenix signal failures visible (P1-8):** set `PHOENIX_HOST` (+ headers) explicitly; don't silently swallow annotation failures during showcase — surface a clear diagnostic so a "no_learning_signal" failure is distinguishable from a Phoenix misconfig.
6. **Carry full case metadata into official judging (P1-7)** and gate `approve_session` on `proposal.is_promotable`, so composites/proposals are meaningful.
7. **Add a small app-level rate limiter / pacing around the judge + drafter loops (P1-5)** before attempting the serious run; the quick run is the priority for "just works."

**Smoke-test sequence after fixes:** `curl /health` → `curl /v1/showcase/manifest` (200) → start a *tiny* quick run (e.g. 2 train / 2 holdout) end-to-end including cancel and approve, watching that the session actually advances and Phoenix gets annotations.

**Revisit a real architecture** (Cloud Tasks / Cloud Run Jobs + Firestore/Cloud SQL session store + per-case idempotent checkpoints + centralized Gemini rate limiter) only if: more than one user triggers runs, the serious run must be reliable, runs must survive redeploys, or polling must work across instances.

---

## Is the library/Vertex path in the critical path?

**No for `/appeal` (degrades gracefully):** missing Vertex/corpus → ungrounded draft (`citations_used: 0`) + risk flag, not a crash. **Yes, indirectly, for the showcase learning loop:** the judges' grounding dimension and the seed prompt/playbook reads (P0-1) are blocked by the same packaging issue, so the library gap shows up as low scores / failed seed reads rather than a clean error. Fix P0-1 first; then decide whether grounded citations matter for the demo.
