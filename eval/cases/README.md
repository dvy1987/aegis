# Eval cases layout

## Lifecycle (current)

```
drafts/          ← all synthetic cases land here (flat: case_01 … case_220)
    │
    ▼  Gumloop evaluator swarm (APPROVE / REVISE / DISCARD)
    │
approved/        ← only cases that pass Gumloop review
    │
    ▼  PM assigns train vs holdout (later — not before approval)
    │
part-a/train/    ← future, after split decision
part-a/test/
```

**Do not** pre-split drafts into train/test folders. The same Gumloop and schema gates apply to every file in `drafts/` until it moves to `approved/`.

## Directories

| Path | Purpose |
|------|---------|
| `drafts/` | Working set — generation output + Gumloop queue (**500 cases**: `case_01`–`case_20` calibration, `case_21`–`case_220` benchmark, `case_221`–`case_420` extension, `case_421`–`case_500` extension-2) |
| `drafts/benchmark-200/` | **Deprecated** — empty; cases were moved to `drafts/` parent |
| `approved/` | Gumloop-approved cases only (flat until train/test split) |

See [dataset_card.md](../dataset_card.md) for schema, provenance, and rebuild commands.

## Generate new cases (default)

Uses the **A+ pipeline** (realistic denial letters + saved references). See [backend/app/case_generator/GENERATION.md](../../backend/app/case_generator/GENERATION.md).

```bash
cd backend && uv run python -m app.case_generator.cli --count 1 --dry-run
cd backend && uv run python scripts/run_manual_case_batch.py --batch 1
```

Legacy scripts are prefixed with `old_` (e.g. `old_run_manual_case_batch.py`).
