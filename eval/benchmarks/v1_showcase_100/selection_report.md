# V1 Showcase 100 Selection Report

Date: 2026-06-06

## Decision

The quick run uses a targeted Cigna + medical-necessity cohort rather than literal `case_01` through `case_10`.

Selected quick training cohort:

- Insurer: Cigna
- Denial type: medical necessity
- Cases: `case_01`, `case_07`, `case_19`, `case_22`, `case_30`, `case_35`, `case_45`, `case_48`

Selected quick holdout cohort:

- Insurer: Cigna
- Denial type: medical necessity
- Difficulty: medium (`synthetic_provenance.appeal_difficulty.score == 3`)
- Cases: `case_13`, `case_46`

## Rationale

Literal cases 1-10 are mixed across three insurers and two denial types. That would make the quick run a noisier learning signal and a weaker demo. The selected quick cohort is single-insurer and single-denial-type, which matches the PM-approved priority for a targeted quick learning check.

The quick holdout is split out so the quick demo has a clean pre/post measurement set. The quick train cases merge into `serious_train`; the quick holdout cases merge into `serious_holdout`.

## Serious Split

- `serious_train`: first-100 cases excluding `serious_holdout`, 80 cases. Includes every `quick_train` case.
- `serious_holdout`: 20 medium-difficulty cases balanced across insurer + denial-type slices. Includes every `quick_holdout` case.

The serious holdout is not used for GEPA training.

Selected serious holdout:

- Aetna + medical necessity: `case_37`, `case_52`, `case_85`
- Aetna + prior authorization: `case_04`, `case_28`, `case_55`, `case_73`
- Cigna + medical necessity: `case_13`, `case_46`, `case_64`
- Cigna + prior authorization: `case_16`, `case_76`, `case_100`
- UHC + medical necessity: `case_34`, `case_61`, `case_91`, `case_97`
- UHC + prior authorization: `case_10`, `case_40`, `case_88`

Each holdout case has at least one same-insurer + same-denial-type case remaining in `serious_train`.

## Guardrails

- Draft case files are read-only inputs.
- The manifest references case ids; it does not modify or copy case content.
- Frontend metadata must expose only student-safe fields.
