# Synthetic case generation — which path to use

## Default (use this)

**A+ pipeline** — ERISA-style denial letters, flaw injection, web-sourced + catalog `denial_letter_references`, claim-file / peer-to-peer letter enhancements.

| Command | When |
|---------|------|
| `cd backend && uv run python -m app.case_generator.cli --count N` | Ad-hoc cases into `eval/cases/drafts/` |
| `cd backend && uv run python scripts/run_manual_case_batch.py --batch N` | Matrix batch (10 cases per batch) |
| `cd backend && uv run python scripts/upgrade_calibration_aplus.py` | Rebuild `case_01`–`case_20` |
| `cd backend && uv run python scripts/upgrade_benchmark_aplus.py` | Rebuild `case_21`–`case_220` |
| `cd backend && uv run python scripts/generate_cases_221_420.py` | Generate `case_221`–`case_420` |
| `cd backend && uv run python scripts/generate_cases_421_500.py` | Generate `case_421`–`case_500` (500 total) |
| `cd backend && uv run python scripts/upgrade_cases_01_220_web.py` | In-place upgrade refs + letter surface on existing drafts |

Code: `app/case_generator/aplus/` (`build_aplus_case` in `aplus/pipeline.py`).

### What `build_aplus_case` does (P1–P5)

1. **P1** scenario brief + denial patterns  
2. **P2** `draft_denial_letter` → ERISA-style notice  
3. **P2b** `enhance_denial_letter` → claim-file block, insurer P2P, policy naming (from public-source patterns)  
4. **P3** clinical context  
5. **P4** `inject_flaws`  
6. **P5** stylistic diversify  
7. **QA** `fit_letter_word_budget` (200–500 words for letter, 80–250 for context)

### References and “web research”

Generation does **not** call the live internet per case. By default `use_web_research=True` merges:

- Static catalog: `eval/references/denial-letter-realism-sources.json`  
- Pre-researched cache: `eval/references/web-research-cache-2026-06-02.json`

Disable web merge (catalog only): `build_aplus_case(..., use_web_research=False)` or CLI `--no-web-research`.

## Legacy (`old_*` — do not use unless you mean to)

| File | What it was |
|------|-------------|
| `manual_batches/old_manual_producer.py` | Short “Dear Member” letters |
| `scripts/old_run_manual_case_batch.py` | Batch script for legacy producer |
| `old_pipeline.py` + `old_agents.py` | Vertex/Gemini LLM swarm |
| `scripts/old_rewrite_cases.py` | One-off backfill via Gemini pipeline |
