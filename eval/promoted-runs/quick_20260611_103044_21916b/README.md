# Promoted run — preview quick session

Pulled from Cloud Run session `quick_20260611_103044_21916b` after PM approval (2026-06-11).

| Field | Value |
|-------|--------|
| Candidate | `c3` |
| Train composite | 0.84 → 0.9067 |
| Approved by | `pm` |
| Changed | drafter `drafter_v1+1`, US geo `cold-start+1` |
| Unchanged | question agent `v1`, Cigna slice playbook `day_zero` |

Active copies synced into:

- `backend/app/aegis_v1/prompts/drafter_v1_1.md` (+ `active_drafter_prompt.txt` → `drafter_v1_1`)
- `geo_playbooks/us_playbook.json`

Source: `GET /v1/showcase/runs/quick_20260611_103044_21916b` proposal payload.
