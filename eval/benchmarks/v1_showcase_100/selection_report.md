# V1 Showcase 100 Selection Report

Date: 2026-06-09 (preview cohort updated)

## Quick preview cohort (cases 101–200)

The preview run uses a **separate** 10-case bundle from the Gumloop-reviewed `case_101`–`case_200` batch. It does **not** overlap the serious benchmark (cases 1–100).

| Role | Insurer | Denial type | Cases |
|---|---|---|---|
| Training (8) | Cigna | Medical necessity | `case_101`, `case_116`, `case_118`, `case_124`, `case_132`, `case_134`, `case_145`, `case_146` |
| Holdout (2) | Cigna | Medical necessity | `case_126`, `case_131` |

### Holdout selection note

The 101–200 batch has no `appeal_difficulty.score == 3` (medium) Cigna medical-necessity cases. Holdout cases were chosen as the **closest-to-medium** pair in that slice (fewest exploitable weaknesses among score-5 cases).

## Serious benchmark (cases 1–100)

Unchanged from 2026-06-06:

- `serious_train`: 80 cases (all of 1–100 except holdout)
- `serious_holdout`: 20 medium-difficulty cases balanced across insurer × denial-type slices

The serious holdout is not used for GEPA training during the quick preview run.

## Guardrails

- Draft case files are read-only inputs.
- The manifest references case ids; it does not modify case content.
- Quick cohort cases must be numbered 101–200 and must not overlap the 1–100 serious benchmark.
