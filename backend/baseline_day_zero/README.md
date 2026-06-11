# Day-Zero Blank Slate (Heuristics v1)

This folder is a **read-only backup** of the starter (pre-learning) state of the
Heuristics v1 prompts and the six insurer × denial-type playbooks. It exists so you can
**restart learning from a clean slate** if a learning run goes wrong.

It is deliberately kept **outside** the paths the learning loop writes to:

- The loop writes evolved drafter/question-agent prompts into `app/aegis_v1/prompts/`
  and updates `active_drafter_prompt.txt` / `active_question_agent_prompt.txt`.
- The loop writes promoted playbooks into the repo-root `playbooks/`.

Because this snapshot lives in `backend/baseline_day_zero/`, the loop never
touches it.

## What's in here

- `prompts/drafter_v1.md` — starter (weak baseline) drafter prompt
- `prompts/question_agent_v1.md` — starter question-agent prompt
- `prompts/search_planner_v1.md` — starter library search-planner prompt
- `playbooks/*.json` — the six day-zero playbooks (one harmless tactic each)
- `active_drafter_prompt.txt` — active drafter pointer (`drafter_v1`)
- `active_question_agent_prompt.txt` — active question-agent pointer (`question_agent_v1`)
- `MANIFEST.json` — what this snapshot is and how to restore it

## How to restart learning from a blank slate

1. **Restore the files** (prompt + playbooks + active pointer):

   ```bash
   cd backend
   uv run python scripts/reset_to_day_zero.py            # asks for confirmation
   uv run python scripts/reset_to_day_zero.py --yes      # non-interactive
   uv run python scripts/reset_to_day_zero.py --dry-run  # preview, change nothing
   ```

   By default the script makes a timestamped backup of whatever is currently live
   (under `backend/baseline_day_zero/.pre_reset_backups/`) before overwriting, so a
   reset is itself reversible.

2. **Delete the Phoenix traces manually** (you do this yourself, as planned). The
   reset script does NOT touch Phoenix — it only resets local prompt/playbook state.

3. Start a fresh quick run from the `/showcase` UI.

## Safety notes

- Treat this folder as read-only. Do not let any automated job write into it.
- If you ever intentionally change what "day zero" means, re-capture this snapshot
  and bump `captured_at` in `MANIFEST.json`.
