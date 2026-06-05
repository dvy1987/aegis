# V1 Demo Benchmark Split Plan

Date: 2026-06-05
Status: Working Draft

## Summary

This document captures the current shared plan for curating the v1 demo benchmark used by the live `/showcase` learning workflow. It is separate from the UX/backend workflow plan.

The goal is to create a reviewed 100-case benchmark split from the first 100 draft cases:

- 20 held-out test cases
- 80 training cases
- no overlap
- held-out cases selected for medium difficulty and coverage by training cases

This plan should produce a dedicated benchmark directory/manifest for the split. It should not move, rename, or edit the source draft case files unless explicitly approved later.

## Source Pool

Use only the first 100 generated draft cases for this v1 demo benchmark.

Source path:

```text
eval/cases/drafts/case_01_*.json through eval/cases/drafts/case_100_*.json
```

Do not include later generated cases in this split yet, because the next batch is still being generated and reviewed.

## Target Structure

Create one curated benchmark manifest, with two groups:

1. Held-out test sets
2. Training sets

Held-out test sets:

- 4 sets
- 5 cases per set
- 20 cases total
- medium difficulty preferred
- stable across showcase sessions

Training sets:

- 8 sets
- 10 cases per set
- 80 cases total
- one training set can be used per showcase learning session
- completed training sets become locked in the UX

The split should be a fixed, reviewed artifact, not generated dynamically at runtime.

The UX can expose three run sizes from this fixed split:

- Quick demo: 1 held-out set, 5 cases.
- Standard v1 demo: first 2 curated held-out sets, 10 cases.
- Full measurement: all 4 held-out sets, 20 cases.

## Selection Criteria

### Held-Out Test Cases

Preferred criteria:

- `appeal_difficulty.score == 3`, treated as medium difficulty.
- Commercial plan only.
- In-scope insurer: Aetna, Cigna, or UHC.
- In-scope denial type: Medical Necessity or Prior Authorization.
- No known case-quality warnings from prior QA.
- Denial type and insurer should be covered by at least one training case.
- Prefer exact slice coverage: same insurer plus same denial type in training.
- Prefer multiple training examples per held-out slice when possible.

Rationale: a denial type can behave differently by insurer. For example, prior authorization for Aetna may not teach the same tactics as prior authorization for UHC. Exact insurer plus denial-type coverage is therefore preferred over broad denial-type coverage.

Fallback criteria:

- If exact insurer plus denial type coverage is not possible for a held-out case, require at least denial-type coverage.
- If too few medium cases exist in a slice, choose the nearest acceptable case only after manual review.

Current inspection indicates exact slice coverage should be feasible in the first 100 cases because the six core slices repeat often:

- Aetna + Medical Necessity
- Aetna + Prior Authorization
- Cigna + Medical Necessity
- Cigna + Prior Authorization
- UHC + Medical Necessity
- UHC + Prior Authorization

### Training Cases

Training cases should cover every held-out case's insurer and denial type.

Training set goals:

- Include all non-held-out cases from the first 100.
- Avoid putting all examples of one important slice into the held-out group.
- Preserve enough examples per slice for the learning loop.
- Prefer balanced sets where each 10-case training set has a mix of insurers and denial types.
- Avoid using known-bad or unrepaired cases unless they have been independently reviewed.

## Proposed Curation Process

### Step 1: Extract Metadata

Build a table for cases 1-100 with:

- case id
- file path
- insurer
- denial type
- appeal difficulty score
- specialty
- sub-tactic
- denial pattern anchors
- known QA notes or warnings

This step should be read-only.

### Step 2: Identify Held-Out Candidates

Filter for likely held-out candidates:

- difficulty score 3
- valid insurer
- valid denial type
- no known QA issue

Group candidates by insurer plus denial type.

### Step 3: Choose 20 Held-Out Cases

Pick 20 held-out cases across the six core slices.

Recommended target balance:

- At least 2 cases from each core slice where possible.
- No single insurer dominates the held-out set.
- No single denial type dominates the held-out set.
- Prefer pattern diversity within each slice.

Example target distribution, subject to actual case quality:

```text
Aetna + Medical Necessity: 3-4
Aetna + Prior Authorization: 3-4
Cigna + Medical Necessity: 3-4
Cigna + Prior Authorization: 3-4
UHC + Medical Necessity: 3-4
UHC + Prior Authorization: 3-4
```

The total must equal 20.

### Step 4: Build Four Held-Out Sets

Split the 20 held-out cases into four 5-case sets.

Each set should be internally mixed:

- more than one insurer when possible
- both denial types when possible
- varied specialties and pattern anchors
- no obvious cluster of near-duplicates

Set names should be UX-friendly:

- Held-out Set A
- Held-out Set B
- Held-out Set C
- Held-out Set D

### Step 5: Build Eight Training Sets

Assign the remaining 80 cases into eight 10-case training sets.

Training set goals:

- Each set is varied enough to produce meaningful learning signal.
- Across all eight sets, every held-out slice has training coverage.
- If possible, each training set should include at least one case from multiple insurers and both denial types.

Set names should be UX-friendly:

- Training Set 1
- Training Set 2
- Training Set 3
- Training Set 4
- Training Set 5
- Training Set 6
- Training Set 7
- Training Set 8

### Step 6: Validate Coverage

For every held-out case, validate:

- no overlap with training
- same insurer plus denial type exists in training
- same denial type exists in training
- pattern anchors are not unique to held-out only, where feasible
- difficulty is medium or explicitly justified

Validation should produce a report that can be reviewed before implementation.

### Step 7: Commit Manifest

Once reviewed, write a fixed manifest.

Potential location:

```text
eval/benchmarks/v1_demo_100/manifest.json
```

Potential companion report:

```text
eval/benchmarks/v1_demo_100/selection_report.md
```

The manifest should include:

- benchmark id
- source case range
- held-out sets
- training sets
- case metadata needed by the UX
- coverage summary
- curation notes

## Manifest Behavior

The `/showcase` workflow should read from the committed manifest, not scan the drafts folder directly.

Benefits:

- stable demo behavior
- clean audit trail
- no accidental use of still-unreviewed generated cases
- easier explanation to judges
- simpler UX

## Open Questions

- Should every held-out set contain all three insurers, or is broader balance across all 20 enough?
- Should each held-out set contain both denial types, or is all-20 balance enough?
- Should the eight training sets be balanced individually or only as an 80-case whole?
- Should training sets be ordered intentionally from easier to harder learning signal, or kept neutral?
- Should cases with `appeal_difficulty.score == 1` be excluded from training, or are they useful for easier early signal?
- Should cases with `appeal_difficulty.score == 5` be included in training, or held back for later stress tests?
