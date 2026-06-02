# Aegis Dataset Card (eval/cases/)

**Description:** Synthetic denial cases for evaluating the Aegis multi-agent system.

## Strict PHI Policy

As mandated by `AGENTS.md`, **no real PHI** is in this dataset. Every case is 100% synthetically generated.

## Lifecycle (source of truth)

1. **Draft** — all new cases live in `eval/cases/drafts/` as `case_<NN>_<insurer>_<denial>.json` (flat folder).
2. **Gumloop** — independent evaluator swarm (`gumloop/`); outcomes: APPROVE → move to `approved/`, REVISE (fix in drafts), or DISCARD.
3. **Approved** — `eval/cases/approved/` holds only Gumloop-passed cases (flat until further organization).
4. **Train / test split** — **after** approval, PM assigns cases to holdout vs training (e.g. under `part-a/train/` and `part-a/test/`). **Not** done at draft time.

The Gumloop swarm must not be imitated from generator prompts before the real review pass.

## What is in `drafts/` today (2026-06-02)

| ID range | Count | Role |
|----------|-------|------|
| `case_01` … `case_20` | 20 | Early calibration set (A+ pipeline, `cursor-manual-agent-aplus-v2`) |
| `case_21` … `case_210` | 190 | Benchmark matrix continuation |
| `case_211` … `case_220` | 10 | Benchmark matrix batch 1 (renumbered from 11–20 to avoid ID clash with calibration) |

**Total:** 500 files in a single flat `drafts/` directory (`case_01`–`case_500`). No train/test subfolders in drafts.

Rebuild commands:

- Calibration `case_01`–`case_20`: `cd backend && uv run python scripts/upgrade_calibration_aplus.py`
- Benchmark `case_21`–`case_220`: `cd backend && uv run python scripts/upgrade_benchmark_aplus.py`
- Extension `case_221`–`case_420`: `cd backend && uv run python scripts/generate_cases_221_420.py`
- Extension `case_421`–`case_500`: `cd backend && uv run python scripts/generate_cases_421_500.py`
- In-place letter + ref upgrade on existing drafts: `cd backend && uv run python scripts/upgrade_cases_01_220_web.py` (supports `--start` / `--end`)

**Default generation** (`build_aplus_case`): web-research cache + catalog references, claim-file / peer-to-peer letter enhancements, 200–500 word letter budget. See `backend/app/case_generator/GENERATION.md`.
- Frontend demo copy (optional, uses `case_11`–`case_20` student fields): `uv run python scripts/sync_frontend_test_fixtures.py`

## Generation pipeline

Cases are produced by the AlphaEval-aligned generator at `backend/app/case_generator/`:

```
ScenarioPlanner → DenialDrafter → ClinicalContextWriter → AdversarialDiversifier
  → SafetyRedactor → SchemaValidator → critic mini-panel
```

Configs: `eval/diversity_matrix.json`, `eval/banned_topics.json`, `eval/case_schema.json` (v1.1.0).

Default CLI: `cd backend && uv run python -m app.case_generator.cli --count <N>` → A+ pipeline → `eval/cases/drafts/`. See `backend/app/case_generator/GENERATION.md`. Legacy: `old_pipeline.py`, `old_run_manual_case_batch.py`.

### Manual A+ pipeline (2026-06-01)

`backend/app/case_generator/aplus/` — prompt-faithful P1–P5, specialty-aligned stories, flaw injection from `eval/denial_patterns.json`, word-count gates (P2: 200–500 words, P3: 80–250 words). Not Vertex Gemini.

Matrix index 11–20 maps to public IDs `case_211`–`case_220` via `benchmark_public_number()` so `case_11`–`case_20` stay available for calibration.
