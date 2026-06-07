# Gumloop faithful pass — 500 draft cases

**Latest run:** 500 APPROVE · 0 REVISE · 0 DISCARD  
**Script:** `backend/scripts/run_true_gumloop_all_500.py`  
**Reports:** `eval/gumloop_runs/true-swarm-500/<case_id>.json`  
**Drafts:** `eval/cases/drafts/` (edited in place)

## What this is

Automated encoder of `gumloop/prompts/01..18` + `gumloop/architecture.md` tier rules, with fix-and-re-evaluate (up to 3 rounds). **Not** 500×18 live LLM nodes in Gumloop UI — criteria are implemented in Python so results are reproducible.

## Fixes applied this session (why earlier passes were wrong)

| Issue | What went wrong | Fix |
|--------|------------------|-----|
| **case_02** `algo_boilerplate_fingerprint` | `[REDACTED]` in summary but MRI/diagnosis in body; false APPROVE | Generic EXPLANATION, full redaction, APPEAL RIGHTS restored |
| **case_03** benefit-category dupes | Advisory dupes ignored | Collapsed to one sentence |
| **step_therapy_vague_mcg** | Notice dates `2026` counted as MCG edition | Check guideline sentences only |
| **83 false REVISE** | Provider regex captured `Dear Member` as provider name | Regex + redacted-inconsistency logic fixed |
| **Truncated letters** | Word-budget trim dropped APPEAL RIGHTS | Protected tail blocks in `fit_letter_word_budget` |
| **11 missing flaws** | Algo fix ran before inject; stripped `ignored_physician` / state-mandate anchors | Inject after algo; `documentation submitted` wording |

## Spot-check pointers

- **case_02:** `eval/gumloop_runs/true-swarm-500/case_02_cigna_priorauth.json`
- **case_03:** `eval/gumloop_runs/true-swarm-500/case_03_aetna_mednec.json`

## Script limitations

`backend/scripts/run_gumloop_prompt_pass_batches_11_500.py` and `eval/gumloop_runs/manual-llm-sample/11-500-full-swarm-batches/` use a narrow checker — APPROVE counts are not equivalent to a full Gumloop UI pass. See `docs/memory/learnings.md` (2026-06-03).
