# V1 Showcase 100 Selection Report

Date: 2026-06-10 (preview cohort: 7 cases)

## Quick preview cohort (cases 101–200)

The preview run uses a **separate** 7-case bundle from the Gumloop-reviewed `case_101`–`case_200` batch. It does **not** overlap the serious benchmark (cases 1–100).

| Role | Insurer | Denial type | Cases |
|---|---|---|---|
| Training (5) | Cigna | Medical necessity | `case_101`, `case_145`, `case_184`, `case_192`, `case_195` |
| Holdout (2) | Cigna | Medical necessity | `case_126`, `case_131` |

### Selection rationale

**Slice:** Cigna + medical necessity (28 cases available in 101–200).

**Pairing rule:** each holdout shares `insurer + denial_type + sub_tactic` with ≥2 training cases.

| Holdout | Sub-tactic | Training partners |
|---|---|---|
| `case_126` | `not_evidence_based` | `case_101`, `case_145`, `case_184` (3) |
| `case_131` | `frequency_excessive` | `case_192`, `case_195` (2) |

| Case | Role | Sub-tactic | Treatment lane |
|---|---|---|---|
| `case_101` | Train | `not_evidence_based` | Neurology — CGRP migraine preventive |
| `case_145` | Train | `not_evidence_based` | Women's health — recurrent BV suppressive therapy |
| `case_184` | Train | `not_evidence_based` | Behavioral health — rTMS for TRD |
| `case_192` | Train | `frequency_excessive` | Oncology — carfilzomib infusion frequency |
| `case_195` | Train | `frequency_excessive` | Endocrine — Dexcom G7 CGM |
| `case_126` | Holdout | `not_evidence_based` | Gastroparesis — Enterra gastric electrical stimulation |
| `case_131` | Holdout | `frequency_excessive` | Oncology — post-treatment surveillance CT |

All 28 Cigna med-nec cases in 101–200 score `appeal_difficulty` 5 (easy); no true medium holdouts exist in this batch.

## Serious benchmark (cases 1–100)

Unchanged pending production-run resize (target: 50 cases total):

- `serious_train`: 80 cases (all of 1–100 except holdout)
- `serious_holdout`: 20 medium-difficulty cases balanced across insurer × denial-type slices

## Guardrails

- Draft case files are read-only inputs.
- The manifest references case ids; it does not modify case content.
- Quick cohort cases must be numbered 101–200 and must not overlap the 1–100 serious benchmark.
