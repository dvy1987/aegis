# Live Showcase Learning UX Plan

Date: 2026-06-05
Status: Superseded working draft

> Superseded on 2026-06-06 by `docs/plans/2026-06-06-v1-showcase-gepa-quick-serious-plan.md`.
> The old 4-held-out-set / 8-training-set evolution model is retired for the immediate v1 showcase push.
> Carry forward only the non-contradictory principles: clean measurement isolation, HITL approval, cancellable jobs, accessible language, and session ledger.

## Summary

This document captures the current shared plan for turning `/showcase` into a live, demo-friendly learning workflow. It is not an approved implementation spec yet.

The goal is to show a clean before/after learning story: Aegis is measured on held-out denial letters, trains on separate training letters, shows exactly what changed, requires a person to approve the update, then measures again on the same held-out letters.

The current `/showcase` button should evolve into this guided modal/wizard. The UX should keep the existing Aegis visual language from `docs/design-brief.md`: calm, restrained, premium consumer-health, no technical helper copy, no AI-marketing voice, no exclamation marks.

## Core Product Model

The showcase workflow uses a curated v1 demo benchmark, defined separately from this plan:

- 4 held-out test sets, 5 cases each, 20 test cases total.
- 8 training sets, 10 cases each, 80 training cases total.
- Test cases and training cases never overlap.
- The same held-out test sets remain stable across sessions.
- Each session can train on one unused training set.
- Previously used training sets are locked and shown as completed.

Useful run presets:

- Quick demo: one 5-case held-out set.
- Standard v1 demo: two held-out sets, 10 cases total. The exact "first 10" should mean the first 10 cases in the curated held-out manifest, not raw `case_01` through `case_10`.
- Full measurement: all four held-out sets, 20 cases total.

The page should avoid repo and implementation language. Use terms such as:

- "Held-out letters"
- "Training letters"
- "Writing approach"
- "Learned rules"
- "Approved update"
- "Measure before"
- "Train Aegis"
- "Measure after"

Avoid default UX terms such as:

- drafts folder
- candidate
- prompt version
- playbook JSON
- eval corpus
- benchmark split

## Workflow

### 1. Measure Before

The user selects one or more held-out test sets.

Allowed behavior:

- Run each selected held-out case through the v1 drafter and outcome simulator.
- Show per-set approval counts, e.g. `2 / 5 approved`.
- Show average simulator score and case-level verdicts.
- Allow quick demo mode by selecting only one 5-case set.
- Allow fuller demo mode by selecting all four held-out sets.

Hard isolation rules:

- No Phoenix reads.
- No Phoenix writes.
- No judge panel.
- No learning loop.
- No learning annotations.
- No test case data entering the learning store.

This stage should be labeled in the UX as a held-out measurement with Phoenix and judges off.

The "Where Aegis started" baseline should also record the active writing approach and learned rules at the moment the pre-test starts. If no learned playbook exists yet for a slice, the UX should show that plainly as "no learned rules yet" rather than exposing implementation details.

### 2. Train Aegis

The user selects exactly one available training set from the eight curated training sets.

Allowed behavior:

- Run the full v1 LearningCoordinator on the selected training set.
- Use the existing Phoenix-backed learning path for training data only.
- Allow judges during training if required by the learning loop.
- Produce a proposed update that may include both writing approach changes and learned rules.

Locked behavior:

- Training sets already used in prior successful sessions are shown as green/completed and cannot be selected again.
- Training cannot use held-out test cases.
- Training cannot begin unless at least one held-out set has completed the pre-test stage.

### 3. Review And Approve

The training stage produces a proposed update. The UX must show the update before it becomes active.

The update should be explained in accessible language:

- "Writing approach" means the drafter instructions changed.
- "Learned rules" means the playbook changed for the relevant insurer and denial type.
- "Why Aegis changed this" should summarize laundered learning signal, not expose hidden answer keys.

The person must explicitly approve the update before promotion.

Approval behavior:

- If approved, backend promotes the drafter/playbook update and records the approval.
- If rejected, backend records rejection and does not run post-test.
- If cancelled, backend stops the job and does not promote anything.

### 4. Measure After

The user selects one or more held-out sets for post-test.

Rules:

- Only held-out sets that completed pre-test are available.
- The same exact held-out cases are rerun after promotion.
- The stage uses the newly promoted writing approach and learned rules.
- The same hard isolation rules apply: no Phoenix, no judges, no learning loop, no annotations.

The UX compares before and after:

- approval count before vs after
- average simulator score before vs after
- case-level flips: denied to approved, still denied, approved stayed approved
- training set used
- approved update summary

### 5. Results And Evolution

The page should show a bold half-and-half split:

Left side: "Where Aegis started"

- selected held-out set results before training
- approval rate, e.g. `2 / 5 approved`
- average simulator score
- expandable "What Aegis knew then"
- label: `Phoenix off | judges off | held-out measurement`

Right side: "Where Aegis is now"

- same held-out set results after promotion
- approval rate, e.g. `4 / 5 approved`
- case-level changes
- expandable "What changed in the latest approved update"
- current writing approach and learned rules after the latest run, with the detailed view focused on the latest run rather than every historical prompt/playbook version
- label: `Phoenix off | judges off | held-out measurement`

Below the split, show an evolution timeline with 8 training blocks:

- gray = not run
- active = running
- green = trained and promoted
- cancelled or failed = stopped or incomplete

Each completed block should show compact held-out outcomes across the four test sets:

```text
Set A 1/5 | Set B 2/5 | Set C 3/5 | Set D 2/5
```

Recommended color thresholds for each 5-case held-out set:

- 0-1 approved = red, needs work
- 2-3 approved = yellow, improving
- 4-5 approved = green, strong

Note: PM initially proposed making 2-5 green. Current working recommendation is stricter: 2-3 should read as improvement, not solved. Revisit if the demo needs a more optimistic visual threshold.

## Backend Shape

This workflow should be a cancellable long-running job, not a single blocking browser request.

Minimum backend capabilities:

- Start showcase session.
- Select or update pre-test held-out sets.
- Run pre-test batches.
- Cancel queued batches before they begin.
- Select one available training set.
- Run training.
- Return proposed update summary.
- Approve and promote update.
- Run post-test batches.
- Fetch job/session state for polling.
- Cancel job.

The backend should persist a session ledger with:

- session id
- selected held-out sets
- selected training set
- pre-test results per case
- training run summary
- proposed writing approach changes
- proposed learned rule changes
- approval decision
- promotion result
- post-test results per case
- cancellation/failure timestamps
- aggregate before/after approval and simulator scores

Cancellation requirements:

- The user can exit the flow at any stage.
- Queued test batches can be removed before they begin.
- If a model call has already started, the backend may not be able to kill the remote call immediately, but it must not start the next case or promote anything after cancellation.
- Cancelled jobs must be marked clearly and remain visible in the session ledger.

## Frontend Direction

The modal should feel like a guided operational workflow, not a technical console.

Recommended stages:

1. Measure before
2. Train Aegis
3. Review update
4. Measure after
5. Results

UX principles:

- Keep the first screen simple: choose one or more held-out sets.
- Allow a quick demo path with one 5-case set.
- Allow a standard v1 demo path with the first two curated held-out sets, 10 cases total.
- Use calm status language and progress bars.
- Avoid helper text that points to folders or implementation details.
- Use expandable details for raw writing approach and learned rules.
- Show accessible summaries first; raw drafter/playbook text belongs behind an advanced disclosure.
- Keep the main result visually clear enough for a 3-minute demo.

## Key Invariants

- Held-out cases never train the system.
- Test stages never call judges.
- Test stages never touch Phoenix.
- Training can use judges and Phoenix because it is explicitly the learning phase.
- Human approval is required before promotion.
- Post-test measures the promoted update, not an unapproved temporary update.
- Previously used training sets are locked.

## Open Questions

- Should the training set be constrained to the same insurer and denial type as the held-out set currently being displayed, or can a session use any unused training set?
- Should post-test run automatically after approval, or should the user explicitly start it?
- How much raw drafter/playbook content should be exposed behind advanced dropdowns?
- Should the evolution timeline show all prior sessions or only the latest successful session plus summary blocks?
- What exact backend storage location should hold showcase session ledgers?
- Should failed training sets become retryable or remain marked as failed until manually reset?
