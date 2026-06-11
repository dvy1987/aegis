# Part A Judge Panel Spec

**Status:** Approved implementation spec  
**Date:** 2026-05-29  
**Scope:** Part A MVP appeal-quality evaluation  
**Model constraint:** Gemini 3.1 Pro is used for both drafting and judging.

## Design Principle

The generated benchmark case is the test. Heuristics v1 is the student and receives
only the denial letter, clinical context, and ordinary runtime fields. The
judge panel is the teacher and receives the answer key: synthetic provenance,
denial pattern sources, appeal difficulty, exploitable weaknesses, plan funding
type, timestamps, and corpus context.

This preserves the anti-cheating firewall while letting the judges grade the
actual exam: did Heuristics identify and use the flaw that the generator embedded?

## Inputs

### StudentCasePacket

The runtime agent may receive:

- `case_id`
- `denial_letter_text`
- `clinical_context`

It must not receive:

- `synthetic_provenance`
- `appeal_difficulty`
- `intended_flaw_types`
- `denial_pattern_sources` as answer-key metadata
- expected appeal vectors

### TeacherGradingPacket

The judge panel may receive:

- all student-visible fields
- `patient_profile`
- `insurer`
- `denial_type`
- `matrix_cell`
- `denial_pattern_sources`
- expected appeal vectors from `eval/denial_patterns.json`
- `appeal_difficulty.exploitable_weaknesses`
- `appeal_difficulty.strong_defenses`
- `submission_timestamp`
- `denial_timestamp`
- retrieved corpus excerpts / citation IDs

## Seven Judges

| ID | Judge | Type | Score |
|---|---|---|---|
| J1 | Safety & Scope | deterministic first, Gemini fallback later | PASS/FAIL |
| J2 | Faithfulness & Hallucination | deterministic citation checks + Gemini | PASS/FAIL |
| J3 | Grounding / Citation Correctness | Gemini | 1/3/5 |
| J4 | Case-Specific Clinical Rebuttal | Gemini | 1/3/5 |
| J5 | Evidence Completeness | Gemini | 1/3/5 |
| J6 | Appeal-Vector Capture | Gemini with teacher-only packet | 1/3/5 |
| J7 | Persuasive Coherence & Tone | Gemini | 1/3/5 |

All Gemini judge prompts must:

- evaluate exactly one dimension
- require evidence/rationale before score
- quote exact text from the appeal
- output JSON only
- use forced anchors: `1`, `3`, `5`, `PASS`, or `FAIL`
- avoid length preference and confident-tone preference

## Weights

Hard gates are never averaged. If J1 or J2 fails, `verdict = FAIL` and
`weighted_quality = null`.

If both gates pass:

| Dimension | Weight |
|---|---:|
| J3 Grounding | 30% |
| J4 Case-Specific Clinical Rebuttal | 20% |
| J5 Evidence Completeness | 15% |
| J6 Appeal-Vector Capture | 25% |
| J7 Persuasive Coherence & Tone | 10% |

Anchor normalization:

- `1 -> 0.2`
- `3 -> 0.6`
- `5 -> 1.0`

## Same-Model Bias Mitigation

Gemini judging Gemini is accepted because the local/cloud environment does not
currently support another judge model. Mitigations:

1. Deterministic gates run before Gemini.
2. Judges are single-dimension.
3. Prompts require evidence-first scoring.
4. J6 uses teacher-only answer-key context.
5. Calibration examples are hand-labeled by the PM.
6. Re-run stability is measured; judge noise must be lower than claimed lift.
7. Human spot checks remain required for demo-critical claims.

## Definition Of Done

- The panel can run locally without GCP/Gemini using the offline heuristic judge
  client.
- The panel produces seven judge results plus an aggregate report.
- The student packet excludes answer-key fields.
- The teacher packet includes expected appeal vectors and exploitable
  weaknesses.
- J6 can penalize a generic but fluent appeal that misses the injected flaw.
- J6 score `1` is surfaced as a promotion blocker even if hard gates pass.
- Judge evidence quotes are post-validated against the appeal, case packet,
  teacher packet, and corpus excerpts; non-verbatim quotes are flagged.
- The report is ready to be sent to Phoenix as eval metadata later.
