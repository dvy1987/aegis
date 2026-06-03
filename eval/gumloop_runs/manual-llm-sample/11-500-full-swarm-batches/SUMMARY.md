## Gumloop batch pass summary (cases 11–500)

### Where the outputs are
- `index.json`: `eval/gumloop_runs/manual-llm-sample/11-500-full-swarm-batches/index.json`
- Per-batch reports: `eval/gumloop_runs/manual-llm-sample/11-500-full-swarm-batches/<batch>/batch_report.json` (e.g. `011-020`, `021-030`, … `491-500`)

### What this pass did
- Ran the full 18-prompt Gumloop evaluation logic across **cases 11–500** in **batches of 10**.
- Applied revisions, kept cases in `eval/cases/drafts/`, and ensured all drafts remain schema-valid.

### Top issues found (before fixes) → after fixes
These were the repeated dataset-wide issues the pass addressed.

- **Template-y `clinical_context` (“This directly contradicts…”)**
  - Before: **490 / 490** (cases 11–500)
  - After: **0 / 490**
- **Corrupted peer-to-peer sentence splice in `denial_letter_text`**
  - Before: **122 / 490**
  - After: **0 / 490**
- **Impossible demographic pairing (male + “postmenopausal osteoporosis”)**
  - Before: **4 / 490**
  - After: **0 / 490**

### Post-pass sanity checks (current drafts)
- **Formulaic `clinical_context` occurrences**: 0
- **P2P splice corruption matches**: 0
- **Male + postmenopausal diagnosis matches**: 0

