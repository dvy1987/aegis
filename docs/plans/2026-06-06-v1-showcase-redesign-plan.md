# Plan — V1 Showcase Redesign (Multi-Slice GEPA + 6-Box Layout)

**Date:** 2026-06-06
**Status:** Implemented through local unit/build verification. Backend manifest, reject/rollback primitives, quick/serious runners, multi-slice coordinator support, mid-loop cancellation, regression warning, and the primary 6-box frontend layout are built. Live credentialed rehearsal and PM visual review on a runnable machine remain.
**Source plan superseded for the v1 showcase push:** `docs/plans/2026-06-06-v1-showcase-gepa-quick-serious-plan.md`
**Source task list partially superseded:** `docs/plans/2026-06-06-v1-showcase-gepa-quick-serious-tasks.md`

This document captures the redesign agreed in the 2026-06-06 PM session. It builds on top of the existing partially-implemented quick/serious workflow and re-shapes both the backend learning loop and the frontend showcase page.

## Locked decisions

| # | Decision | Rationale |
|---|---|---|
| 1 | Quick run = 8 train + 2 holdout (was 10/0). | Even the demo run gets a clean held-out check. |
| 2 | Serious run = 80 train + 20 holdout (was 80/10). | More credible measurement. |
| 3 | Quick is a **subset** of Serious. Quick's 8 train ⊆ Serious's 80 train; Quick's 2 holdout ⊆ Serious's 20 holdout. | Prevents the demo slice from being underrepresented in the serious pass and protects the quick-promoted prompt from being silently overwritten. |
| 4 | GEPA evolves the **drafter prompt + every per-insurer/per-denial playbook** in both quick and serious runs (multi-slice). The single-slice path is preserved as a fallback. | Matches the product story; tests multi-slice plumbing on small data before serious. Drafter and learner never see the teacher packet — INV-2 firewall preserved. |
| 5 | Sequential rollback (LIFO stack). Promotions stack; only the most recent is rollbackable; rolling that back exposes the next layer. | One-click reversal without skipping ahead. |
| 6 | Promotion stack lives in a JSON file alongside the showcase session ledger. | Simplest persistence; matches existing local-JSON ledger pattern. |
| 7 | Reject is its own status, distinct from Cancel. Proposal preserved, no promotion, run ends in `rejected`. | Clear semantic separation between operator cancellation and PM declining an update. |
| 8 | `/showcase` rebuilt as a 6-box layout: Demo and Serious side-by-side; each contains Pre-training / Training / Post-training. Each sub-box shows a grid of green/red simulator-outcome blocks. Grayed-out blocks with status messages until data exists. | Honest, visible end-to-end view of the loop. |
| 9 | Training box has two rows of case blocks: top = simulator-on-training-cases **before** training, bottom = simulator-on-training-cases **after** training. The "after" row runs **after GEPA optimization but before PM approval**, using the candidate prompt that has not been written to disk yet. | Lets the PM see what training actually changed before deciding whether to approve. |
| 10 | Legacy v1-vs-v3 versus panel + diff card + counterfactual card stay as a separate "Compare versions" section **below** the 6-box layout. They continue using `POST /v1/showcase/evaluate`. | Keep them as a known-working secondary view; the new layout is the primary story. |
| 11 | If post-training measurement on the holdout shows a regression vs pre-training, the system actively warns the PM with a "post-measure score dropped — consider rolling back" banner. | Catches bad promotions early. |
| 12 | Serious holdout case selection: each holdout case must be **medium difficulty** AND have **at least one case with the same insurer × denial type in the training set**. Relaxation rules below (Holdout Selection Rules). | Ensures a fair, balanced holdout. |

## Verifications confirmed in this session

- **`/v1/appeal` already evolves with promotions.** It reads the active drafter prompt from `backend/app/aegis_v1/prompts/active_drafter_prompt.txt` (or `AEGIS_DRAFTER_PROMPT_VERSION` env). When GEPA promotes a new drafter prompt, the next `/v1/appeal` call picks it up automatically. **No change needed for the `/v1/appeal` path itself.**
- **Today `/v1/appeal` defaults to `drafter_v1`** after the day-zero reset. `drafter_v2` is archived and retained on disk for legacy compare-view compatibility, but it is not the default active prompt.
- **v1 writes to Phoenix project `default`**, not `aegis-hackathon`. Swarm writes to `aegis-swarm`. They use different recorder classes; they cannot collide.

## Scope of change vs current code

This is a meaningful redesign, not a small patch. Five things shift:

1. **Manifest restructuring** — splits change, quick becomes a subset of serious, loader validation flips.
2. **Workflow restructure** — measurement gets split into three distinct steps per run (pre-training on test cases, training on training cases x 2, post-training on test cases after approval).
3. **Multi-slice optimization** in the Learning Coordinator — drafter + N playbooks.
4. **Promotion stack** with sequential rollback rules.
5. **Showcase page rebuild** — 6-box layout + new buttons (Reject, Roll back).

## Per-area changes

### A. Manifest (`eval/benchmarks/v1_showcase_100/`)

- Add a new `quick_holdout` field (2 cases) to `manifest.json`. Quick splits 10 cases into 8 train + 2 holdout.
- Resize `serious_holdout` from 10 to 20 cases. Resize `serious_train` accordingly so the totals stay at 100 cases (every case used).
- Make quick a subset of serious: `quick_train ⊆ serious_train`, `quick_holdout ⊆ serious_holdout`.
- Update `backend/app/aegis_v1/showcase_manifest.py`:
  - Add a `quick_holdout: list[ShowcaseCase]` field on `ShowcaseManifest`.
  - Replace the current "no overlap" validation with a subset check.
  - Validate `len(quick_train) == 8`, `len(quick_holdout) == 2`, `len(serious_train) == 80`, `len(serious_holdout) == 20`.
  - Validate `serious_train ∩ serious_holdout == ∅` (the only disjoint pair).
- Add a `headline` field on `ShowcaseCase` (default to `case_id` when missing) so the API response satisfies the frontend `CaseSummary` type.
- Update `selection_report.md` to explain the new structure.

### B. Holdout selection rules (Serious holdout = 20 cases)

The 20 must include the 2 quick_holdout cases (already locked Cigna mednec). For the 18 additional cases:

1. **Primary rule:** each candidate case must be **medium difficulty** AND have **at least one case with the same insurer × denial type in the serious training set** (after the train list is finalized).
2. **First relaxation:** if the primary rule cannot fill 20 holdouts, allow **easy difficulty** alongside medium.
3. **Second relaxation:** if even that cannot fill 20 holdouts, drop the insurer constraint — require only that **the same denial type** appears in the training set.

Selection should be deterministic so the manifest is reproducible. Rationale for picks goes into `selection_report.md`.

### C. Workflow restructure (backend)

The current quick run measures pre/post on the same 10 training cases. New design:

| Stage | What runs | On which cases | Using which prompt | Phoenix? Judges? |
|---|---|---|---|---|
| 1. Pre-training (test) | drafter + simulator | quick_holdout (2) / serious_holdout (20) | currently promoted | No / No |
| 2. Training pre-row | drafter + simulator | quick_train (8) / serious_train (80) | currently promoted | No / No |
| 3. GEPA optimization | drafter + judges + reflection | training cases | candidate prompts evolved | Yes / Yes |
| 4. Training post-row | drafter + simulator | training cases | **candidate prompt (not yet on disk)** | No / No |
| 5. PM reviews | — | — | — | — |
| 6. Promotion | write candidate to disk; push onto promotion stack | — | — | — |
| 7. Post-training (test) | drafter + simulator | quick_holdout (2) / serious_holdout (20) | newly promoted | No / No |

Stage 4 needs the measurement runner to accept a **prompt text** directly (override the on-disk prompt for that one request, no global mutation). This is **only** wired into the measurement runner — it does **not** leak into `/v1/appeal`.

`run_quick_session` and a new `run_serious_session` both follow this same 7-stage pattern. The differences are:
- Test/train case sets used (quick vs serious).
- Number of GEPA rounds (smaller for quick, larger for serious).

### D. Learning Coordinator — multi-slice

Today the coordinator optimizes one slice (`Cigna:medical_necessity`). New behavior:

- The seed candidate carries the drafter prompt + N playbooks (one per insurer × denial type appearing in the training pool that has at least one case).
- Round-robin selection rotates across all components (drafter + every playbook).
- Signal acquisition is per-component:
  - Drafter signal pools across all slices.
  - Each playbook signal is filtered to its own slice.
- Reflection minibatches are slice-specific for playbooks; pooled for the drafter.
- Promotion gates evaluate per-component **and** per-slice composite, not just global composite — otherwise a regression in one slice can hide behind an improvement in another.

For the **quick run**, this still goes through the multi-slice code path even though only one playbook (`Cigna:medical_necessity`) will be present. This is the cheap smoke test of the multi-slice plumbing.

The single-slice code path stays available as a fallback (e.g., behind an env flag like `AEGIS_LEARNING_MODE=single_slice`) so we can revert if multi-slice misbehaves.

For showcase runs, the default is **multi-slice ON**. This is intentional even for the quick run: quick is the low-cost smoke test for the same multi-slice machinery that serious will use. The fallback exists only as a recovery lever if multi-slice blocks the demo.

### E. Promotion stack with sequential rollback

- New file: `promotion_stack.json` next to the showcase session ledger (default `/tmp/aegis_showcase_sessions/promotion_stack.json`; configurable via `AEGIS_SHOWCASE_LEDGER_DIR`).
- Each promotion appends an entry: `{run_type, session_id, promoted_at, drafter_version_before, playbook_snapshots_before, content_hashes, ...}`.
- New endpoint `GET /v1/showcase/rollback-target` — returns the top entry of the stack (or `null`) so the frontend knows whether the Roll back button should be visible.
- New endpoint `POST /v1/showcase/rollback` — pops the top entry, restores the prior drafter prompt version + playbook contents, removes the entry. Verifies content hashes before restoring; aborts with an explicit error if disk has drifted.
- `approve_session` saves a checkpoint **before** calling `register_promotion`. If the checkpoint write fails, the promotion is aborted (don't promote without a way back).

### F. Reject endpoint + status

- Add `'rejected'` to `RunStatus` and `'waiting_for_approval'` already covers the stage.
- New `mark_rejected(session_id, reviewer)` on `ShowcaseSessionManager`. Preserves `proposal` for inspection; sets `status='rejected'`.
- New endpoint `POST /v1/showcase/runs/{id}/reject` (request body: `{reviewer: str}`).
- Frontend: add `rejectRun()` in `live.ts`, "Reject update" button shown on `needs_approval`.

### G. Mid-loop cancellation

Both `_measure` and `_seed_training_signal` need to poll `manager.get(session_id).cancelled` between cases. If cancelled, return early without running further cases and without emitting further Phoenix traces.

### H. Approve session must branch on `run_type`

`approve_session` is currently hard-coded to use `manifest.quick_train` for post-measurement. Change to:
- If `session.run_type == 'quick'` → post-measure on `manifest.quick_holdout`.
- If `session.run_type == 'serious'` → post-measure on `manifest.serious_holdout`.

### I. Regression warning logic

After the post-training stage finishes, compare:
- Pre-training composite (mean simulator score on holdout cases) vs
- Post-training composite (mean simulator score on the same holdout cases).

If post < pre by more than a small tolerance (e.g., ≥ 1 case flips from green to red, or composite drop ≥ 5%), set a `regression_detected: true` flag on the session and surface a banner in the UI: "post-measure score dropped — consider rolling back". The Roll back button is already available; this is just an active nudge.

### J. Frontend rebuild (`/showcase`)

New layout:
- Two main columns: **Demo** and **Serious**, side-by-side.
- Each column has three stacked sub-boxes: **Pre-training**, **Training**, **Post-training**.
- Each sub-box is either:
  - Grayed out with a status message (e.g., "Locked until Quick succeeds", "Waiting for approval"), or
  - A grid of small case blocks colored green (APPROVE) / red (DENY).
- The Training sub-box has **two rows** of blocks: top = before, bottom = after.
- New top-level buttons:
  - **Run quick check** (always available; live)
  - **Run serious pass** (disabled until a quick run is in `successful` status)
  - **Approve update** (visible when run is in `needs_approval`)
  - **Reject update** (visible when run is in `needs_approval`)
  - **Cancel run** (visible while the run is in progress)
  - **Roll back** (visible when `GET /v1/showcase/rollback-target` returns an entry)
- Active regression warning banner when applicable.
- Below the 6-box layout: kept-as-is "Compare versions" section using the existing `VersusPanel` + `DiffCard` + `CounterfactualCard`.

Frontend type updates:
- Add `'rejected'` to `ShowcaseRunSession.status`.
- Add `headline: string` to backend manifest response (matching the existing `CaseSummary`).
- Add `rollbackRun()` and `getRollbackTarget()` to `live.ts`.

## What's at risk of breaking

1. **Manifest loader tests** will fail until the overlap-rejection rule flips to a subset-validation rule. `tests/unit/aegis_v1/test_showcase_manifest.py` and `test_showcase_api_runs.py` need updates (8 quick cases, 2 quick_holdout, 20 serious_holdout).
2. **`approve_session`** post-measure is hard-coded to `manifest.quick_train`. Will be wrong as soon as serious is introduced; must branch on `run_type`.
3. **Existing `_measure(phase="pre", cases=quick_train)` semantics** change. The `pre_measure_results` and `post_measure_results` payload shapes change — anything reading them (frontend, tests) needs updating in lockstep.
4. **Multi-slice Learning Coordinator** is the highest-risk change. Today's tests assume single-slice. Multi-slice changes credit-assignment behavior. Mitigation: keep the single-slice path under an env flag as a fallback.
5. **`OtelPhoenixRecorder` writes to project `default`** — new session-scoped split names will create many small splits (e.g., `showcase_quick_train_quick_20260606_...`, `showcase_serious_train_serious_20260606_...`). Fine for free tier, just noisy. Acceptable.
6. **Promotion stack file is new state.** If it gets corrupted or out-of-sync with disk, rollback could write the wrong content. Mitigation: store content hashes for each snapshot; refuse to restore on hash mismatch; explicit error.
7. **Candidate-prompt-text capability in measurement runner** must be tightly scoped. It must not bleed into `/v1/appeal`, which already correctly reads only from disk-promoted prompts.
8. **Multi-component GEPA** could produce a proposal where the drafter improved but a playbook regressed. Promotion gates need per-slice composite checks.

## Resolved checks

- **Resolved:** when the PM clicks Run Serious, the system re-measures all 20 serious holdout cases from scratch. It does not reuse Quick's 2 post-training holdout results. This keeps the serious measurement window consistent.
- **Resolved:** regression warning threshold is "at least 1 case flips APPROVE→DENY OR mean simulator score drops by more than 5%." This is intentionally conservative for the demo: it warns the PM, but does not auto-rollback.
- **Resolved:** `ShowcaseCase` strips `synthetic_provenance`, expected vectors, exploitable weaknesses, and other answer-key-bearing fields. The manifest response only carries student-safe case metadata plus the denial text/context needed to run the drafter.

## Implementation status

1. **Done:** Manifest restructure + loader validation flip + `headline` field + tests update.
2. **Done:** Promotion stack module + rollback endpoints.
3. **Done:** Reject endpoint + status + manager method.
4. **Done:** Measurement runner gains candidate prompt/playbook override capability, scoped to measurement.
5. **Done:** Approve-session branches on `run_type` and emits regression warnings after holdout post-measure.
6. **Done:** `run_quick_session` follows the redesigned 7-stage pattern.
7. **Done:** Multi-slice Learning Coordinator is default-on for showcase quick and serious runs; single-slice remains a fallback concept.
8. **Done:** `run_serious_session` exists and follows the same workflow over 80 train / 20 holdout.
9. **Done:** Mid-loop cancellation polling in measurement and training-signal seeding.
10. **Done:** Frontend primary 6-box layout, case-block grids, reject + rollback buttons, serious-button disabled state, and regression banner.
11. **Partially done:** Tests and builds pass locally for focused backend and frontend. Full live credentialed smoke run remains because this machine cannot run the dev server and lacks local ADC.
12. **Done:** Memory + handoff updates are part of session close-out.

## Remaining operational work

- Deploy/restart the backend and frontend in the real demo environment.
- Run a live credentialed quick run with `PHOENIX_API_KEY` and Google ADC available.
- PM visual review of `/showcase` on a machine that can run the frontend.
- Decide Cloud Run execution posture if live background sessions prove unreliable: CPU-always-on, Cloud Tasks, or a poll-driven `/advance` endpoint.
