# Implementation Plan: Part A Judge Panel

## Executive Summary

Build a local, testable Part A judge panel that grades Heuristics v1 appeal drafts
against the synthetic-case generator's hidden test design. The panel separates
student-visible case data from teacher-only grading data, runs hard gates before
quality scoring, and supports both an offline heuristic client for this machine
and a Gemini 3.1 Pro client for the configured cloud environment.

## Technical Stack

- Python 3.11
- Pydantic v2
- Existing `google-genai` dependency through `google-adk`
- No new dependencies
- Existing local corpus in `backend/corpus`
- Existing generated cases in `eval/cases`

## Architecture Overview

```
Generated Case JSON
  ├─ StudentCasePacket ──> Heuristics v1 runtime
  └─ TeacherGradingPacket ──> Judge Panel

Heuristics v1 AppealPackage
  └─ Part A Judge Panel
       ├─ J1 Safety & Scope gate
       ├─ J2 Faithfulness & Hallucination gate
       ├─ J3 Grounding
       ├─ J4 Case-specific rebuttal
       ├─ J5 Evidence completeness
       ├─ J6 Appeal-vector capture
       └─ J7 Persuasive coherence
             ↓
       deterministic aggregate report
```

## Phased Breakdown

### Phase 0 — Eval Contract

- **T0.1 [FR-JP-1..8, C-1.2, C-1.3]** Write the approved feature spec and
  judge-panel spec.  
  **DoD:** Specs define packet boundaries, seven judges, same-model mitigation,
  and acceptance criteria.

- **T0.2 [FR-JP-4, C-1.2]** Canonicalize the disclaimer string for judge gates.  
  **DoD:** Safety gate checks `Not legal or medical advice. Draft assistance only.`

### Phase 1 — Core Data Model

- **T1.1 [FR-JP-1, FR-JP-2, C-2.1]** Implement `StudentCasePacket` and
  `TeacherGradingPacket`.  
  **DoD:** Unit test proves answer-key fields are absent from student packet and
  present in teacher packet.

- **T1.2 [FR-JP-2, FR-JP-6]** Map denial pattern sources and appeal difficulty
  into expected appeal vectors.  
  **DoD:** Teacher packet exposes `expected_appeal_vectors` and
  `exploitable_weaknesses`.

### Phase 2 — Gates And Judges

- **T2.1 [FR-JP-4, C-2.1]** Implement deterministic J1 Safety & Scope gate.  
  **DoD:** Missing disclaimer, PHI, guarantee language, or scope drift fails.

- **T2.2 [FR-JP-4, C-1.2]** Implement deterministic citation precheck for J2.  
  **DoD:** Untraceable citation IDs fail before LLM judging.

- **T2.3 [FR-JP-3, FR-JP-7, FR-JP-8]** Implement judge-client interface with
  offline heuristic and Gemini clients.  
  **DoD:** Offline client runs in unit tests; Gemini client is swappable later.

- **T2.4 [FR-JP-3, FR-JP-6]** Add seven prompt templates under
  `eval/judges/part_a/`.  
  **DoD:** Prompts are single-dimension, evidence-first, and JSON-only.

### Phase 3 — Aggregation And Runner

- **T3.1 [FR-JP-5, C-1.2]** Implement deterministic aggregation.  
  **DoD:** Hard-gate fail returns `FAIL`; passing gates compute weighted quality
  from J3-J7 only. J6 score `1` is reported as a promotion blocker.

- **T3.1b [FR-JP-3, C-1.3]** Post-validate judge evidence quotes.  
  **DoD:** Any evidence quote not found verbatim in the appeal, case packet,
  teacher packet, or corpus excerpts is surfaced as a report risk flag.

- **T3.2 [FR-JP-7]** Implement local CLI runner.  
  **DoD:** Can evaluate one or more generated cases using local v1 and offline
  judge client, writing `eval/runs/<timestamp>/panel_report.json`.

### Phase 4 — Tests

- **T4.1 [AC-JP-1.1, AC-JP-2.1, C-2.1]** Add packet-boundary tests.  
  **DoD:** Student packet has no answer key; teacher packet has answer key.

- **T4.2 [AC-JP-4.1]** Add deterministic hard-gate tests.  
  **DoD:** Safety failures produce aggregate `FAIL`.

- **T4.3 [AC-JP-6.1]** Add J6 offline heuristic test.  
  **DoD:** A generic letter that misses expected vectors scores lower than a
  flaw-aware letter.

## Risk & Mitigation

| Risk | Mitigation |
|---|---|
| Gemini judges reward Gemini writing style | Deterministic gates, single-dimension prompts, evidence quotes, PM calibration |
| Teacher packet leaks into Heuristics v1 trace | Packet-boundary tests and explicit API separation |
| Legacy cases have weak provenance | Mark reports with `weak_teacher_packet`; later regenerate/backfill |
| Offline heuristic is mistaken for official score | Name it diagnostic-only in code, docs, and CLI output |

## Requirement Traceability

| Requirement | Tasks | Verification |
|---|---|---|
| FR-JP-1 | T1.1 | AC-JP-1.1 |
| FR-JP-2 | T1.1, T1.2 | AC-JP-2.1 |
| FR-JP-3 | T2.3, T2.4 | AC-JP-3.1 |
| FR-JP-4 | T2.1, T2.2, T3.1 | AC-JP-4.1 |
| FR-JP-5 | T3.1 | aggregator unit test |
| FR-JP-6 | T1.2, T2.4 | AC-JP-6.1 |
| FR-JP-7 | T2.3, T3.2, T4.* | unit tests |
| FR-JP-8 | T2.3 | interface/import test |
| C-1.2 | T2.*, T3.1 | hard-gate tests |
| C-1.3 | T0.1 | calibration procedure documented |
| C-2.1 | T1.1, T2.1, T4.1 | packet-boundary and safety tests |
| C-4.2 | all | no new dependency |

## Timeline Estimate

Size: Medium. Core local implementation is one focused coding session. Gemini
cloud validation and calibration are a later session once GCP is configured.
