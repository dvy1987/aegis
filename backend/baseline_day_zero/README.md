# Day-Zero Blank Slate (Aegis v1)

This folder is a **read-only backup** of the starter (pre-learning) state of the
Aegis v1 drafter prompt and the six insurer × denial-type playbooks. It exists so
you can **restart learning from a clean slate** if a learning run goes wrong.

It is deliberately kept **outside** the paths the learning loop writes to:

- The loop writes evolved drafter prompts into `app/aegis_v1/prompts/` and updates
  `app/aegis_v1/prompts/active_drafter_prompt.txt`.
- The loop writes promoted playbooks into the repo-root `playbooks/`.

Because this snapshot lives in `backend/baseline_day_zero/`, the loop never
touches it.

## What's in here

- `prompts/drafter_v1.md` — the starter (weak baseline) drafter prompt
- `playbooks/*.json` — the six day-zero playbooks (one harmless tactic each)
- `active_drafter_prompt.txt` — points the active prompt back to `drafter_v1`
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
