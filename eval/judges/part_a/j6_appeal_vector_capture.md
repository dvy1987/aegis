# J6 Appeal-Vector Capture

Teacher-only judge. Score whether the appeal **finds and properly rebuts every
embedded flaw** the synthetic case was built to test.

Use the teacher packet:

- `exploitable_weaknesses` (primary list — count each distinct flaw)
- `expected_appeal_vectors`
- `denial_pattern_sources`
- `matrix_cell.sub_tactic`

## What “properly rebutted” means

For each flaw, the letter must **directly attack** it and **support the attack with
facts stated in the letter** (or fair clinical facts from the case). Naming a flaw
without rebutting it does not count.

**This judge checks coverage and directness of flaw attacks — not whether sources
are invented** (faithfulness) or whether clinical detail is rich overall
(case-specific rebuttal).

## Scoring (1–5 only for this dimension)

Count how many distinct flaws from `exploitable_weaknesses` (and expected vectors
when they add flaws not already listed) are **properly rebutted** vs mentioned
without rebuttal vs missed.

| Score | When to use |
|-------|-------------|
| **5** | **All** distinct embedded flaws are directly attacked and properly rebutted with case facts. |
| **4** | Most flaws properly rebutted; one flaw partial or thin but directionally correct. |
| **3** | About half properly rebutted, OR several mentioned but only some backed by facts. |
| **2** | One or more flaws **mentioned** but **none** properly rebutted with facts. |
| **1** | Generic appeal; flaws missed or wrong issue entirely. |

Do not give 5 when only one of three flaws is rebutted. One-of-many = 3 or 4 at
best, depending on how many flaws exist and how strong the partial work is.

Quote appeal text and the teacher flaw it maps to. Output JSON with
`dimension = "appeal_vector_capture"` and `score` 1, 2, 3, 4, or 5.
