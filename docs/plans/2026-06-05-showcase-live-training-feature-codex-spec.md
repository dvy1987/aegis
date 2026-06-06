---
artifact: feature-spec
status: Superseded Draft
constitution: docs/constitution.md@1
slug: showcase-live-training
sources:
  - user request, 2026-06-05
  - docs/superpowers/specs/2026-06-01-aegis-frontend-design.md
---

# Showcase Live Training Workflow

> Superseded on 2026-06-06 by `docs/plans/2026-06-06-v1-showcase-gepa-quick-serious-plan.md`.
> This remains useful as a high-level requirement sketch, but it does not contain the current quick/serious run model, targeted quick cohort selection, serious lock, promotion rollback, or retired 8-batch decision.

## Summary

The `/showcase` page must let the PM run a live three-stage evaluation and training workflow from the UX. Test stages run only the appeal drafter and live simulator; the training stage runs the learning loop; the same test cases are used before and after training.

## Problem

The current showcase surface can show recorded evidence and run a one-shot live comparison, but it cannot drive a new live training cycle from the UX. The demo needs a controlled workflow where the PM chooses test cases, chooses training cases, runs learning, then retests the original cases without contaminating the learning signal.

## User Scenarios

### US-1: Pre-training test set run

As the PM, I choose one or more synthetic denial letters as the test set and run the appeal drafter plus live simulator on them before training.

### US-2: Training set run

As the PM, I choose one or more synthetic denial letters as the training set and run the full Aegis v1 learning loop on those cases.

### US-3: Post-training retest

As the PM, I rerun the same pre-training test cases after training and see the live simulator verdicts again.

### US-4: Pause or exit

As the PM, I can stop the workflow at any point, and backend work for that showcase workflow stops as soon as the current cancellable boundary is reached.

## Functional Requirements

### FR-1: Launch Modal

The `Run live evaluation` action MUST open a modal workflow instead of immediately starting a one-shot evaluation.

### FR-2: Test Case Selection

The first stage MUST allow selecting one or more synthetic denial letters from the repository draft-case library as the test set.

### FR-3: Pre-training Test Isolation

The first stage MUST run only the appeal drafter and live simulator on the selected test set. It MUST NOT run the learning loop, judge panel, promotion logic, or any evaluation step that creates learning signal.

### FR-4: Training Case Selection

The second stage MUST allow selecting one or more synthetic denial letters from the repository draft-case library as the training set.

### FR-5: Learning Loop Run

The second stage MUST run the full Aegis v1 learning loop for the selected training set and return a human-readable training result.

### FR-6: Post-training Retest Isolation

The third stage MUST rerun the same test cases selected in FR-2 using the post-training state available to the workflow. It MUST NOT run the learning loop, judge panel, promotion logic, or any evaluation step that creates learning signal.

### FR-7: Cancellation

The PM MUST be able to pause or exit during any stage. After cancellation, the backend MUST mark the workflow cancelled and stop remaining queued stage work.

### FR-8: Results Visibility

The modal MUST show per-case simulator verdicts for both test stages and a compact training summary for the training stage.

### FR-9: Existing Evidence Preservation

The existing recorded showcase evidence below the modal MUST remain available when no live workflow is active.

## Non-Functional Requirements

### NFR-1: Safety

All workflow inputs and outputs MUST remain synthetic-case-derived and MUST include no PHI.

### NFR-2: Demo Control

The workflow MUST make it clear which stage is active, which stages are complete, and whether the run was cancelled.

### NFR-3: Accessibility

The modal MUST support keyboard navigation, labelled controls, visible focus states, and WCAG 2.2 AA contrast.

### NFR-4: Trace Hygiene

Test stages MUST be distinguishable from learning/eval traces if platform instrumentation records low-level spans. They MUST NOT be used as scored training signal by the Learning Coordinator.

## Acceptance Criteria

### AC-FR-1.1

Given the PM is on `/showcase`, When they select `Run live evaluation`, Then a modal opens at the test-set stage and no backend run starts until the PM starts the stage.

### AC-FR-2.1

Given the modal is on the test-set stage, When the PM selects one or more draft cases, Then the stage can be started.

### AC-FR-3.1

Given the PM starts the first stage, When the stage runs, Then each selected case returns an appeal draft summary and simulator verdict without judge-panel scores.

### AC-FR-4.1

Given the pre-training test stage completed, When the modal advances, Then the PM can select one or more training cases from the same draft-case library.

### AC-FR-5.1

Given the PM starts the training stage, When training completes, Then the modal shows whether a proposal was produced, whether it was promotable, and the before/after composite if available.

### AC-FR-6.1

Given the training stage completed, When the PM starts the final stage, Then the backend reruns exactly the test cases chosen in the first stage.

### AC-FR-7.1

Given any stage is pending or running, When the PM chooses pause or exit, Then the backend marks the workflow cancelled and no later stages start.

### AC-FR-8.1

Given either test stage completes, When results are shown, Then each result includes case id, insurer, denial type, simulator verdict, score, and a short letter excerpt.

### AC-FR-9.1

Given no live workflow result has replaced the page evidence, When the PM closes the modal, Then the recorded v1/v3 showcase evidence remains visible.

## Edge Cases

- If no test cases are selected, the first stage cannot start.
- If no training cases are selected, the second stage cannot start.
- If cancellation is requested while a single live model call is already in progress, queued work after that call must stop and the run must be marked cancelled.
- If the learning loop has no Phoenix signal, the training stage must return a no-signal result rather than fabricating improvement.
- If the backend is unavailable, the modal must show a recoverable error and preserve any completed stage results.

## Out of Scope

- Real patient denial letters or PHI.
- Live filing with insurers.
- Automatic promotion without human review.
- Replacing the recorded showcase evidence page.
- Building the Part B swarm workflow into this modal.

## Constitution Waivers

None.

## Needs Clarification

None.

## Review Checklist

- [x] No implementation details in requirements.
- [x] Every FR has acceptance coverage.
- [x] Out of scope is specific.
- [x] Safety and trace-hygiene requirements are explicit.
