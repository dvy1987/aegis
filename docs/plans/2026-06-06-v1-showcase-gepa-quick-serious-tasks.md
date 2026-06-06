# Tasks — V1 Showcase GEPA Quick + Serious Workflow

**Date:** 2026-06-06
**Status:** Approved for implementation by PM chat instruction on 2026-06-06
**Source plan:** `docs/plans/2026-06-06-v1-showcase-gepa-quick-serious-plan.md`

## Implementation Defaults

- Prioritize targeted quick-cohort learning signal over literal filename order if those conflict.
- Use a local file-backed session ledger first.
- Surface rollback only when a rollback checkpoint exists.
- Implement v1 only; do not switch to or depend on the swarm runtime.
- Do not modify draft case files.
- Every frontend-triggered run must have diagnostics keyed by `session_id`.

## Tasks

### T1 — Manifest And Read-Only Case Selection

Target files:
- `eval/benchmarks/v1_showcase_100/manifest.json`
- `eval/benchmarks/v1_showcase_100/selection_report.md`
- `backend/app/aegis_v1/showcase_manifest.py`
- backend tests

Definition of done:
- Manifest is loaded from a fixed file, not dynamic draft-folder scanning at runtime.
- Quick cohort has 10 cases, targeted by insurer/denial type where feasible.
- Serious train and holdout have no overlap.
- Student-safe frontend metadata excludes answer-key fields.

### T2 — Promotion Wiring And Rollback

Target files:
- `backend/app/learning/fs_store.py`
- `backend/app/learning/phoenix_live.py`
- backend tests

Definition of done:
- A promoted drafter prompt writes to the filename pattern loaded by `load_drafter_prompt`.
- A promoted playbook writes to the directory and filename pattern loaded by `playbook_loader`.
- Rollback checkpoint metadata can restore the previous prompt/playbook files.

### T3 — Measurement Isolation

Target files:
- `backend/app/aegis_v1/pipeline.py`
- `backend/app/aegis_v1/tools.py`
- `backend/app/evals/part_a/measurement_run.py`
- backend tests

Definition of done:
- Measurement can run drafter plus simulator without Phoenix reads, Phoenix writes, judges, or learning.
- The implementation does not mutate process-global environment variables to isolate one request.

### T4 — GEPA Showcase Adapter

Target files:
- `backend/app/learning/showcase_v1.py`
- `backend/app/learning/run_live.py`
- backend tests

Definition of done:
- Quick and serious learning runs use session-scoped training splits.
- The adapter returns a proposal for PM review and does not auto-promote.
- Cancellation prevents later promotion.

### T5 — Backend Session API

Target files:
- `backend/app/aegis_v1/showcase_session.py`
- `backend/app/aegis_v1/showcase_api.py`
- backend tests

Definition of done:
- Frontend can start, poll, approve, reject, cancel, and roll back runs.
- Serious run is locked until quick run success.
- Session ledger records case ids, results, proposal, approval, promotion, cancellation, errors, and timestamps.
- Session ledger records current stage, stage timings, latest error, retryability, completed/total case counts, and Phoenix trace/span ids where applicable.
- Backend emits structured log fields keyed by `session_id` so Cloud Run logs can be filtered by a single run.

### T6 — Frontend Showcase UX

Target files:
- `frontend/src/app/showcase/page.tsx`
- `frontend/src/lib/data/live.ts`
- `frontend/src/lib/types.ts`
- `frontend/src/components/showcase/*`
- frontend tests

Definition of done:
- `/showcase` exposes Quick learning check and Serious learning pass.
- Serious pass is visibly locked until quick success.
- PM can review and approve a proposed update.
- UI copy avoids primary technical terms like candidate, GEPA, Phoenix, and playbook JSON.

### T7 — Verification And Demo Hardening

Target files:
- backend and frontend tests
- docs memory/handoff files

Definition of done:
- Backend targeted tests pass.
- Frontend targeted tests pass.
- New UX does not call old `POST /v1/showcase/evaluate`.
- Session end has memory and handoff updates.
