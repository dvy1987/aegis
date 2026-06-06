# V1 Showcase 100 Selection Report

Date: 2026-06-06

## Decision

The quick run uses a targeted 10-case cohort rather than literal `case_01` through `case_10`.

Selected quick cohort:

- Insurer: Cigna
- Denial type: medical necessity
- Cases: `case_01`, `case_07`, `case_13`, `case_19`, `case_22`, `case_30`, `case_35`, `case_45`, `case_46`, `case_48`

## Rationale

Literal cases 1-10 are mixed across three insurers and two denial types. That would make the quick run a noisier learning signal and a weaker demo. The selected quick cohort is single-insurer and single-denial-type, which matches the PM-approved priority for a targeted quick learning check.

## Serious Split

- `serious_train`: first-100 cases excluding the quick cohort and serious holdout, 80 cases.
- `serious_holdout`: numeric cases 91-100, 10 cases.

The serious holdout is not used for GEPA training.

## Guardrails

- Draft case files are read-only inputs.
- The manifest references case ids; it does not modify or copy case content.
- Frontend metadata must expose only student-safe fields.
