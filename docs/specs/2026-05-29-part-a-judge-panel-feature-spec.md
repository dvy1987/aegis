---
status: Approved
constitution: docs/constitution.md@1
slug: part-a-judge-panel
approved_by: PM
approved_on: 2026-05-29
---

# Feature Spec: Part A Judge Panel

## Summary

Part A needs a judge panel that grades Aegis v1 appeal drafts against the
synthetic-case generator's hidden test design. The runtime agent is the
student: it sees only the denial letter, clinical context, and ordinary parsed
fields. The judge panel is the teacher: it sees the full synthetic provenance,
expected appeal vectors, and corpus context needed to grade whether Aegis found
the real flaw in the denial.

Gemini 3.1 Pro is the only available model family for both drafting and
judging. This is accepted as a constraint. The panel must compensate with
deterministic gates, narrow single-dimension judge prompts, evidence-first
reasoning, low-temperature JSON output, calibration, and human spot checks.

## Functional Requirements

- **FR-JP-1:** The evaluator MUST construct a `StudentCasePacket` that excludes
  `synthetic_provenance`, `appeal_difficulty`, intended flaw metadata, and
  expected appeal vectors.
- **FR-JP-2:** The evaluator MUST construct a `TeacherGradingPacket` that
  includes the full generated case, matrix cell, denial pattern sources,
  exploitable weaknesses, strong defenses, timestamps, plan funding type, and
  local corpus/citation context.
- **FR-JP-3:** The judge panel MUST contain seven independent dimensions:
  Safety & Scope, Faithfulness & Hallucination, Grounding, Case-Specific
  Clinical Rebuttal, Evidence Completeness, Appeal-Vector Capture, and
  Persuasive Coherence.
- **FR-JP-4:** Safety & Scope and Faithfulness & Hallucination MUST be hard
  pass/fail gates. They must never be averaged into quality scores.
- **FR-JP-5:** Weighted quality MUST be computed deterministically from the five
  non-gate dimensions using forced 1/3/5 anchors.
- **FR-JP-6:** Appeal-Vector Capture MUST grade whether the appeal attacks the
  actual flaw embedded by the generator, using teacher-only provenance.
- **FR-JP-7:** The panel MUST run locally without GCP/Gemini by using an offline
  heuristic judge client for tests and dry runs. Offline scores are diagnostics
  only, not official benchmark scores.
- **FR-JP-8:** The implementation MUST allow a Gemini judge client to be swapped
  in later without changing panel aggregation logic.

## Non-Functional Requirements

- **NFR-JP-1:** No PHI may be introduced in fixtures, prompts, judge reports, or
  Phoenix trace payloads. Satisfies Constitution C-2.1.
- **NFR-JP-2:** Judge prompts must be single-dimension and analysis-first.
  Satisfies Constitution C-1.2 and C-1.3.
- **NFR-JP-3:** No new runtime dependency may be added without PM approval.
  Satisfies Constitution C-4.2.
- **NFR-JP-4:** Judge reports must preserve per-dimension scores and evidence;
  the weighted score is a summary, not the sole promotion gate.

## Acceptance Criteria

- **AC-JP-1.1:** Given a generated case, when `StudentCasePacket` is built, then
  answer-key fields are absent.
- **AC-JP-2.1:** Given a generated case, when `TeacherGradingPacket` is built,
  then exploitable weaknesses and expected appeal vectors are available to the
  judge panel.
- **AC-JP-3.1:** Given a v1 appeal package, when the panel runs offline, then it
  returns seven judge results and a deterministic aggregate report.
- **AC-JP-4.1:** Given a missing disclaimer or PHI pattern, when the panel runs,
  then the Safety & Scope gate fails and the aggregate verdict is `FAIL`.
- **AC-JP-6.1:** Given a generic appeal that misses the injected flaw, when J6
  scores it, then Appeal-Vector Capture is low even if the letter is fluent.
- **AC-JP-7.1:** Given no GCP/Gemini configuration, when unit tests run, then
  tests pass using the offline heuristic judge client.

## Edge Cases

1. Legacy generated cases may have `unknown` matrix fields or
   `Legacy manual generation` pattern sources. The panel must still run but
   mark the report with `weak_teacher_packet`.
2. A letter may be safe and grounded but miss the hidden appeal vector. This is
   a quality failure, not a hard-gate failure.
3. A letter may cite local corpus correctly while inventing a patient fact. This
   is a J2 hard-gate failure.
4. A generated case may be strongly appealable procedurally but weak clinically.
   J6 should reward finding the procedural vector; J4 should separately score
   clinical specificity.

## Out Of Scope

- Replacing Gemini 3.1 Pro as judge model.
- Phoenix Cloud experiment integration.
- Full Learning Coordinator promotion logic.
- Regenerating the benchmark dataset.
- Adding new insurers, denial types, or a vector database.

## Needs Clarification

None for this feature.
