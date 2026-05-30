# Playbooks

Per-slice learned tactics, consumed by `backend/app/aegis_v1/tools.py:playbook_loader`.

- Filename (current/promoted): `<slug_insurer>__<denial_type>.json`
  e.g. `cigna__medical_necessity.json`. `playbook_loader` reads this file as the
  active version; the `version` field inside tracks the promoted version string.
- Archived versions: `archive/<slug_insurer>__<denial_type>__vN.json` (written by
  the Learning Coordinator on each promotion; git history is the audit trail).
- Cold start: when no current file exists, the loader returns a marked
  `status: "missing"` cold-start playbook — this is intentional for the weak v1.

Schema (matches `Playbook` in `aegis_v1/schemas.py`, plus optional learning fields):
{ "insurer", "denial_type", "version", "tactics": [], "required_evidence": [],
  "risk_flags": [], "dimension_targets": { "<tactic>": "<rubric_dimension>" },
  "provenance": { "experiment_id", "promoted_at", "approved_by" } }
