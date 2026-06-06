# Plan — V1 Showcase GEPA Quick + Serious Workflow

**Date:** 2026-06-06  
**Status:** Draft for PM review  
**Supersedes:**  
- `docs/specs/2026-06-05-live-showcase-learning-ux-plan.md`
- `docs/specs/2026-06-05-v1-demo-benchmark-split-plan.md`
- `docs/plans/2026-06-05-showcase-live-eval-3stage-amp-spec.md`
- `docs/plans/2026-06-05-showcase-live-training-feature-codex-spec.md`

This is the current source-of-truth planning draft for making `/showcase` run the real Aegis v1 GEPA learning loop from the frontend.

## Executive Summary

Build a working v1 showcase learning product quickly by borrowing the swarm's split discipline, not the swarm runtime.

The frontend should let the PM trigger two v1 learning runs:

1. **Quick run** — a targeted 10-case checkpoint run. It proves the full frontend-triggered v1 GEPA loop works and may promote with explicit PM approval.
2. **Serious run** — unlocked only after a successful quick run. It trains on a larger v1 training pool and measures on a clean held-out set.

The core demo claim becomes:

> Aegis v1 can run a live human-approved learning loop from the UX, promote a writing/playbook update, and show before/after simulator outcomes on clean measurement cases.

## Current Decision Model

### Locked

- Use v1, not the swarm, for the immediate working showcase.
- Borrow from the swarm:
  - explicit split manifest
  - explicit run modes
  - promotion gates
  - session ledger
  - visible human-approved autonomy language
  - simple credit summary
- Do not implement the old 8-training-batch evolution timeline.
- Do not require the Part B swarm for this workflow.
- Serious run is locked until the quick run has completed successfully.
- Quick run may promote, but only with rollback checkpoint and PM approval.
- If quick run is approved/promoted, the serious run starts from that quick-approved prompt/playbook checkpoint, not from untouched original v1.
- Measurement stages must not create learning signal.

### Updated Split Model

The old split was:

```text
20 held-out test cases
80 training cases
8 training batches of 10
```

That model is retired for this v1 product push.

The new split is:

```text
Quick run:
  quick_train: 10 targeted cases
  purpose: prove the loop works and create an approved checkpoint

Serious run:
  starting point: quick-approved checkpoint, if quick promotion happened
  serious_train: cases 11-90, or curated equivalent from first-100 manifest
  serious_holdout: cases 91-100, or curated equivalent from first-100 manifest
  purpose: train v1 on the serious pool and measure on clean held-out cases
```

Important nuance: the PM used "cases 1-10" and "cases 11-100" as the desired first-100 structure. The implementation should still create a manifest so we do not blindly trust raw filename order if it produces a poor or mixed quick cohort. If raw `case_01` through `case_10` are not a coherent quick cohort, escalate before finalizing the manifest.

## Quick Run Case Selection

The quick run needs more careful curation than a random first ten because it is the first live product proof.

Preferred quick cohort:

1. Single insurer + single denial type, 10 cases.
2. If that is not possible, same denial type across two insurers, balanced 5/5 or as close as possible.
3. If that is not possible, same denial type across three insurers, balanced as evenly as possible.
4. Avoid mixing denial types in the quick cohort unless no coherent same-denial cohort exists.

Preferred properties:

- Commercial plan only.
- In-scope insurers: Aetna, Cigna, UHC.
- In-scope denial types: medical necessity or prior authorization.
- Medium difficulty preferred.
- No known QA warnings.
- Enough similar failure pattern signal for GEPA to learn something coherent.
- No PHI or real patient data.

Why single-slice is preferred:

- v1 playbook learning is slice-specific.
- A same-insurer/same-denial cohort gives GEPA a cleaner signal.
- The UX story is easier: "Aegis learned how to handle this kind of denial."
- It reduces the risk that the quick run creates a broad but weak update.

## Serious Run Case Selection

The serious run should preserve an honest held-out measurement.

Recommended structure:

```text
serious_train:
  80 cases
  target: cases 11-90 if quality and slice coverage are acceptable

serious_holdout:
  10 cases
  target: cases 91-100 if quality and slice coverage are acceptable
```

If raw filename ranges do not support clean measurement, the manifest may curate equivalent slots from the first 100 cases, but this must be made explicit in the selection report.

Serious training should preferably align with the quick run's learned slice enough that the second pass can build on the checkpoint, while still being broad enough to reduce overfitting.

If the quick run produces an approved promotion, that approved writing approach and learned-rule state becomes the seed for the serious run. The original v1 state remains available as a rollback checkpoint, but it is not the default serious-run starting point after quick success.

## Borrowed From Swarm

### 1. Explicit Split Manifest

Create a fixed manifest, likely:

```text
eval/benchmarks/v1_showcase_100/manifest.json
eval/benchmarks/v1_showcase_100/selection_report.md
```

The manifest should include:

- benchmark id
- source range: first 100 draft cases
- quick cohort case ids
- serious train case ids
- serious holdout case ids
- insurer and denial type for each case
- difficulty score where available
- curation notes
- any deviations from raw filename order

The workflow must read from this manifest, not dynamically scan arbitrary drafts.

### 2. Explicit Run Modes

v1 should gain explicit internal modes:

```text
measure_only
train_gepa
review_update
promote
post_measure
rollback
```

Mode rules:

- `measure_only`: drafter + current promoted playbook + simulator only. No Phoenix reads, no Phoenix writes, no judges, no learning.
- `train_gepa`: full v1 LearningCoordinator. Phoenix and judges allowed because this is the learning stage.
- `review_update`: show proposed writing/playbook changes. No promotion yet.
- `promote`: explicit PM approval writes the update to the exact locations v1 runtime reads.
- `post_measure`: same isolation as `measure_only`, after approved promotion.
- `rollback`: restore the previous promoted checkpoint if serious holdout regresses or PM rejects the checkpoint.

### 3. Promotion Gates

Borrow the swarm's posture, simplified for v1:

- no hard-gate regression
- no quality regression on holdout when holdout exists
- diff size cap
- no promotion after cancellation
- no auto-promotion without HITL
- rollback checkpoint before each promotion
- serious run cannot unlock until quick run status is successful

Quick promotion gate:

- candidate beats quick baseline or at least passes configured GEPA gates
- no hard gate failures
- diff is small enough to review
- PM explicitly approves
- pre-quick version is saved as rollback point

Serious promotion gate:

- serious holdout after-promotion measurement must be no worse than before
- hard gates pass
- PM explicitly approves
- prior checkpoint remains rollbackable

### 4. Session Ledger

Persist a simple ledger for frontend progress and audit.

Suggested location:

```text
backend/app/aegis_v1/showcase_sessions/
```

or, if repo writes are undesirable in Cloud Run:

```text
GCS JSON under a v1-showcase-sessions prefix
```

This is a product/architecture decision to confirm before implementation. For fastest local/demo work, file-backed JSON is simplest.

Each session record should include:

- session id
- run type: quick or serious
- run modes completed
- case ids used
- selected slice
- pre-measure results
- GEPA training summary
- proposed writing approach changes
- proposed learned rule changes
- approval decision
- promoted versions
- rollback checkpoint
- post-measure results
- errors
- cancellation state
- timestamps

### 5. Visible Autonomy Language

Use only:

```text
Current mode: Human-approved learning
```

Do not implement Apprentice/Journeyman/Master in this v1 showcase.

### 6. Simple Credit Summary

Show accessible change categories:

```text
Changed: writing approach
Changed: learned rules
```

If possible, show the weakest rubric dimension that triggered the change:

```text
Focused on: case-specific clinical rebuttal
```

Avoid exposing implementation terms as primary UX copy:

- candidate
- component id
- GEPA mutation
- playbook JSON
- prompt version

Raw prompt/playbook text can live behind an advanced disclosure.

## Workflow

### Quick Run

Purpose: prove the full v1 loop works from the frontend.

Flow:

1. PM clicks `Run quick learning check`.
2. Backend loads the quick cohort from the manifest.
3. Backend runs `measure_only` on the quick cohort.
4. Backend runs `train_gepa` on the quick cohort.
5. Backend returns a proposed update.
6. PM reviews the accessible change summary and advanced raw diff.
7. PM approves or rejects.
8. If approved, backend creates rollback checkpoint and promotes.
9. Backend runs `post_measure` on the quick cohort.
10. Frontend marks quick run successful only if the run completed, was approved/promoted, and post-measure finished without cancellation.

Notes:

- This is allowed to train and measure on the same quick cohort because the purpose is operational proof, not broad generalization.
- The UX must not overclaim the quick run as held-out generalization.

### Serious Run

Purpose: stronger v1 training pass with clean measurement.

Precondition:

- Quick run status is successful.
- If the quick run was approved/promoted, the promoted quick checkpoint is the serious run's starting prompt/playbook state.
- If quick succeeded operationally but no promotion occurred, the serious run starts from the current promoted v1 state and the ledger must say no quick checkpoint was applied.

Flow:

1. PM clicks `Run serious learning pass`.
2. Backend loads `serious_holdout` and runs `measure_only`.
3. Backend loads `serious_train` and runs `train_gepa`.
4. Backend returns a proposed update.
5. PM reviews and approves/rejects.
6. If approved, backend creates rollback checkpoint and promotes.
7. Backend reruns `serious_holdout` with `post_measure`.
8. If holdout regresses materially, UX should show the regression and offer rollback.

Notes:

- Serious training should not use serious holdout cases.
- Serious holdout is the credible before/after proof.
- The serious "before" measurement represents the current promoted state at serious-run start, which normally means the quick-approved checkpoint.

## Backend Architecture

### Existing Pieces To Reuse

- `run_aegis_v1_pipeline`
- `run_appeal_with_outcome`
- `LearningCoordinator`
- `LivePhoenixLearningStore`
- `LiveExperimentRunner`
- `PanelJudgeAdapter`
- `GeminiReflectionClient`
- `phoenix_mcp_lookup`
- swarm split discipline from `benchmark_dataset.py` as a pattern, not as direct runtime dependency

### Pieces To Fix First

Promotion wiring is the first critical fix.

Current known issue:

- v1 runtime reads playbooks from root `playbooks/`.
- live learning store currently points at `backend/app/aegis_v1/playbooks`.
- v1 runtime loads prompts as `prompts/{version}.md`.
- promotion writes prompt files as `drafter_system_prompt__{version}.md`.

Before showcase UX work, make this invariant true:

```text
approved GEPA proposal -> promoted prompt/playbook -> next v1 run uses it
```

### New Backend Components

#### Manifest Loader

File:

```text
backend/app/aegis_v1/showcase_manifest.py
```

Responsibilities:

- load the fixed manifest
- validate no overlap between serious_train and serious_holdout
- validate quick cohort case count
- expose student-safe case metadata to frontend
- never expose answer-key fields

#### Measurement Runner

File:

```text
backend/app/evals/part_a/measurement_run.py
```

Responsibilities:

- run drafter + simulator only
- disable Phoenix reads
- suppress Phoenix writes/traces
- skip judges
- skip learning
- return case-level verdict/score/excerpt

#### Showcase Session Manager

File:

```text
backend/app/aegis_v1/showcase_session.py
```

Responsibilities:

- one active session at a time
- start quick run
- start serious run only after successful quick run
- progress polling
- cancellation token
- no promotion after cancellation
- session ledger persistence
- rollback checkpoint metadata

#### GEPA Session Adapter

File:

```text
backend/app/learning/showcase_v1.py
```

Responsibilities:

- build `LearningCoordinator` for manifest-selected cases
- seed Phoenix with session-scoped training split
- run full GEPA with configured max rounds
- return proposal without auto-promoting
- call promotion only after explicit approval

Session split names should be unique:

```text
showcase_quick_train_{session_id}
showcase_serious_train_{session_id}
```

### API Endpoints

Extend `backend/app/aegis_v1/showcase_api.py`.

Recommended endpoints:

```text
GET  /v1/showcase/manifest
POST /v1/showcase/runs/quick
POST /v1/showcase/runs/serious
GET  /v1/showcase/runs/{session_id}
POST /v1/showcase/runs/{session_id}/approve
POST /v1/showcase/runs/{session_id}/reject
POST /v1/showcase/runs/{session_id}/cancel
POST /v1/showcase/runs/{session_id}/rollback
```

The old `POST /v1/showcase/evaluate` can remain temporarily for compatibility, but the new frontend should not use it.

## Frontend Architecture

### Page Model

`/showcase` should become a compact operational surface:

- current promoted state
- quick run card
- serious run card
- before/after result panel
- latest approved update summary
- rollback state if available

The old 8-block evolution timeline should be replaced by a two-step timeline:

```text
Quick checkpoint -> Serious pass
```

### UX States

Quick run card:

- ready
- running
- needs approval
- promoted
- failed
- cancelled

Serious run card:

- locked until quick success
- ready
- running
- needs approval
- promoted
- holdout regressed
- rolled back
- failed
- cancelled

### Copy Guidance

Use:

- "Quick learning check"
- "Serious learning pass"
- "Measure before"
- "Train Aegis"
- "Review update"
- "Approve update"
- "Measure after"
- "Human-approved learning"
- "Writing approach"
- "Learned rules"

Avoid:

- "candidate" in primary UI
- "GEPA" in primary UI
- "Phoenix" in measurement labels
- "playbook JSON" in primary UI
- "drafts folder"

## Phased Implementation Plan

### Phase 0 — Spec Reconciliation

Tasks:

- Mark superseded docs so old plans do not drive implementation.
- Keep useful inherited constraints in this plan.
- Update current-state memory with the new quick/serious model.

Definition of done:

- Future agents see this plan as the current source of truth.
- Contradictory 8-batch/20-held-out/80-training language is clearly retired.

### Phase 1 — Manifest And Case Selection

Tasks:

- Build metadata extraction for first 100 cases as read-only inspection.
- Propose quick cohort using the selection priority above.
- Propose serious train/holdout split.
- Write manifest and selection report after PM review.

Definition of done:

- Manifest exists.
- Quick cohort is targeted or has a documented exception.
- Serious train and holdout have no overlap.
- Selection report explains any deviation from raw filename ranges.

### Phase 2 — Promotion Wiring Repair

Tasks:

- Align prompt promotion filenames with `load_drafter_prompt`.
- Align playbook promotion path with `playbook_loader`.
- Add tests proving promoted prompt/playbook affect the next v1 run.
- Add rollback checkpoint writing and restoration.

Definition of done:

- A promoted GEPA proposal changes the next v1 draft path.
- Rollback restores the prior prompt/playbook.

### Phase 3 — Measurement Isolation

Tasks:

- Add `measure_only` runner.
- Add pipeline knobs to disable Phoenix memory reads.
- Add tracing suppression for measurement.
- Add tests proving no judges, no recorder, no Phoenix read/write in measurement.

Definition of done:

- Pre/post measurement cannot leak into learning signal.
- Measurement returns simulator verdicts and scores.

### Phase 4 — GEPA Showcase Adapter

Tasks:

- Build session-scoped GEPA adapter.
- Seed training signal using session-specific split.
- Force flush/retry Phoenix reads.
- Return proposal for review.
- Add cancellation checkpoints.

Definition of done:

- Quick GEPA can run on manifest-selected cases.
- Proposal is returned without auto-promotion.
- Cancellation prevents promotion.

### Phase 5 — Backend Session API

Tasks:

- Add session manager.
- Add quick run endpoint.
- Add serious run endpoint with quick-success lock.
- Add approve/reject/cancel/rollback endpoints.
- Persist session ledger.

Definition of done:

- Frontend can start and poll a quick run.
- Serious run returns locked until quick success.
- Approval promotes.
- Cancel stops queued work.
- Ledger records the full run.

### Phase 6 — Frontend Showcase UX

Tasks:

- Replace current single live button with quick/serious workflow cards.
- Add progress polling.
- Add approval review modal.
- Add before/after results panel.
- Add two-step timeline.
- Add rollback action when available.

Definition of done:

- PM can run quick from the browser.
- PM can approve quick promotion.
- PM can run serious only after quick success.
- UI shows what changed in accessible language.

### Phase 7 — Verification And Demo Hardening

Tasks:

- Unit tests for backend manifest, measurement, promotion, session manager.
- Frontend tests for locked serious state, approval flow, cancel flow.
- Smoke run with tiny fixture mode.
- Cloud Run deployment settings review.
- End-to-end live rehearsal.

Definition of done:

- Backend tests pass.
- Frontend tests pass.
- A browser-triggered quick run completes.
- Serious run lock/unlock works.
- No old `/showcase/evaluate` path is used by the new UX.

## Contradiction Audit

The following older ideas are explicitly retired:

- Four held-out test sets of five cases each.
- Eight training batches of ten cases each.
- 8-block evolution timeline.
- Full measurement across four held-out sets.
- Train cap of eight cases for the final quick/serious model.
- Post-test using only an unpromoted in-session candidate.
- Arbitrary draft-folder selection in the final UX.
- Treating `POST /v1/showcase/evaluate` as the main live learning path.

The following older ideas are still valuable and carried forward:

- Measurement must be Phoenix-off, judge-off, learning-off.
- Training can use Phoenix and judges.
- No process-global env mutation for request isolation.
- Session-scoped training split to avoid reading old Phoenix signal.
- Cooperative cancellation.
- Force flush/retry after Phoenix trace seeding.
- One active showcase session at a time.
- Calm, simple UX language aligned to the design brief.
- Session ledger with case ids, results, proposal, approval, promotion, cancellation.

## Risks And Mitigations

### Risk 1: Quick Cohort Is Not Coherent

Raw cases 1-10 may not share insurer/denial type.

Mitigation:

- Manifest selection must inspect metadata before locking.
- Prefer targeted quick cohort over blind filename order.
- Escalate if PM must choose between literal raw numbering and coherent learning signal.

### Risk 2: Promotion Does Not Affect Runtime

This is currently the highest technical risk.

Mitigation:

- Fix and test promotion wiring before frontend work.

### Risk 3: Small Quick Run Overfits

Quick promotion can pollute the serious baseline.

Mitigation:

- Save rollback checkpoint.
- Label quick as operational checkpoint, not generalization proof.
- Serious holdout remains clean.

### Risk 4: Live GEPA Is Slow

GEPA involves model calls, judges, Phoenix writes, and Phoenix reads.

Mitigation:

- Run one active session.
- Use progress polling.
- Use cancellable checkpoints.
- Start with configured max rounds for quick run.

### Risk 5: Measurement Accidentally Writes Traces

The backend is globally instrumented.

Mitigation:

- Add explicit trace suppression helper.
- Test measurement isolation.

## Open Questions For PM

These should be resolved before implementation starts:

1. If raw `case_01` through `case_10` are not a coherent quick cohort, should we prioritize literal numbering or targeted learning signal?
2. Should the quick run and serious run share the same insurer/denial slice when feasible?
3. Should session ledgers be local JSON first, or GCS JSON from the start?
4. What maximum runtime is acceptable for the quick run in a live demo?
5. Should rollback be visible as a button in the first version, or only available as backend/admin action?

## Current Recommendation

Prioritize targeted learning signal over literal raw numbering if there is a conflict. The quick run is the proof that the product works; it should be coherent enough for GEPA to produce a visible update.

Use local JSON session ledgers for fastest implementation unless Cloud Run persistence becomes a blocker. If persistence across deploys/restarts matters immediately, use GCS JSON.

Build v1 only. Do not switch to swarm.
