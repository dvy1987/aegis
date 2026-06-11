# Guinea pig GEPA run — case_127_aetna_priorauth

- **Status:** failed
- **Auto-approved:** False
- **GEPA rounds:** 1 (drafter + question agent + insurer playbook + US geo)
- **Phoenix project:** default
- **Phoenix trace ids:** f240b2fd0bb8f5b3, 21d75c2d38914046
- **Estimated Gemini cost:** $0.1271 (110785 tokens, 40 tracked calls)
- **Post-promote holdout measure:** skipped (run `run_guinea_pig_measure.py` next)

- Judge composite: 0.670 → 0.830
- Vetoes: ['diff_too_large']

## Artifacts

- `session.json` — full showcase session state
- `proposal.json` — GEPA promotion proposal
- `promotion_preview.json` — human-readable diff preview
- `measurement_pre.json` / `measurement_training_pre.json` / `measurement_training_post.json`
- `cost_summary.json` — token + USD estimate (partial; ADK not tracked)
- `promoted/` — candidate component snapshots

Not legal or medical advice. Draft assistance only.
