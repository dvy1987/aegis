# V1 Showcase 100 Selection Report

Date: 2026-06-10 (preview cohort: 7 cases)

## Quick preview cohort (cases 101–200)

The preview run uses a **separate** 7-case bundle from the Gumloop-reviewed `case_101`–`case_200` batch. It does **not** overlap the serious benchmark (cases 1–100).

| Role | Insurer | Denial type | Cases |
|---|---|---|---|
| Training (5) | Cigna | Medical necessity | `case_101`, `case_116`, `case_132`, `case_145`, `case_184` |
| Holdout (2) | Cigna | Medical necessity | `case_126`, `case_131` |

### Selection rationale

**Slice:** Cigna + medical necessity (28 cases available in 101–200).

**Holdout pair (closest-to-medium in slice):**

| Case | Treatment lane | Why holdout |
|---|---|---|
| `case_126` | Gastroparesis — Enterra gastric electrical stimulation | Geriatric criteria misapplied to young patient; insurer's HDE/investigational defense is the main counter |
| `case_131` | Oncology — post-treatment surveillance CT | Real guideline exists, procedurally clean; appeal hinges on rising CEA + age-mismatched criteria |

**Training (diverse clinical lanes):**

| Case | Treatment lane |
|---|---|
| `case_101` | Neurology — CGRP migraine preventive |
| `case_116` | Rehab — supervised PT continuation |
| `case_132` | Orthopedics — knee MRI |
| `case_145` | Women's health — recurrent BV suppressive therapy |
| `case_184` | Behavioral health — rTMS for TRD |

All 28 Cigna med-nec cases in 101–200 score `appeal_difficulty` 5 (easy); no true medium holdouts exist in this batch.

## Serious benchmark (cases 1–100)

Unchanged pending production-run resize (target: 50 cases total):

- `serious_train`: 80 cases (all of 1–100 except holdout)
- `serious_holdout`: 20 medium-difficulty cases balanced across insurer × denial-type slices

## Guardrails

- Draft case files are read-only inputs.
- The manifest references case ids; it does not modify case content.
- Quick cohort cases must be numbered 101–200 and must not overlap the 1–100 serious benchmark.
