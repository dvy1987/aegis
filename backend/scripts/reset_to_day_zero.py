#!/usr/bin/env python3
"""Restore Heuristics v1 day-zero prompts + playbooks to their blank slate.

This copies the read-only snapshot in ``backend/baseline_day_zero/`` back over the
live files the learning loop writes to:

- ``backend/app/aegis_v1/prompts/drafter_v1.md``
- ``backend/app/aegis_v1/prompts/question_agent_v1.md``
- ``backend/app/aegis_v1/prompts/search_planner_v1.md``
- ``backend/app/aegis_v1/prompts/active_drafter_prompt.txt``
- ``backend/app/aegis_v1/prompts/active_question_agent_prompt.txt``
- repo-root ``playbooks/<insurer>__<denial>.json`` (six day-zero playbooks)

Before overwriting, it saves a timestamped backup of the current live state under
``backend/baseline_day_zero/.pre_reset_backups/<timestamp>/`` so a reset is itself
reversible.

It does NOT touch Phoenix — delete Phoenix traces manually if you want a full
restart of the learning memory.

Usage (from backend/):
    uv run python scripts/reset_to_day_zero.py            # confirm then reset
    uv run python scripts/reset_to_day_zero.py --yes      # no prompt
    uv run python scripts/reset_to_day_zero.py --dry-run  # show plan only
"""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
SNAPSHOT = BACKEND_ROOT / "baseline_day_zero"

LIVE_PROMPT_DIR = BACKEND_ROOT / "app" / "aegis_v1" / "prompts"
LIVE_PLAYBOOK_DIR = REPO_ROOT / "playbooks"

PROMPT_V1_FILES = [
    "drafter_v1.md",
    "question_agent_v1.md",
    "search_planner_v1.md",
]

ACTIVE_PROMPT_POINTERS = [
    "active_drafter_prompt.txt",
    "active_question_agent_prompt.txt",
]

PLAYBOOK_FILES = [
    "aetna__medical_necessity.json",
    "aetna__prior_authorization.json",
    "cigna__medical_necessity.json",
    "cigna__prior_authorization.json",
    "unitedhealthcare__medical_necessity.json",
    "unitedhealthcare__prior_authorization.json",
]


def _planned_copies() -> list[tuple[Path, Path]]:
    """(source in snapshot, destination live) pairs."""
    pairs: list[tuple[Path, Path]] = [
        (SNAPSHOT / "prompts" / name, LIVE_PROMPT_DIR / name) for name in PROMPT_V1_FILES
    ]
    pairs.extend(
        (SNAPSHOT / name, LIVE_PROMPT_DIR / name) for name in ACTIVE_PROMPT_POINTERS
    )
    for name in PLAYBOOK_FILES:
        pairs.append((SNAPSHOT / "playbooks" / name, LIVE_PLAYBOOK_DIR / name))
    return pairs


def _verify_snapshot(pairs: list[tuple[Path, Path]]) -> None:
    missing = [str(src) for src, _ in pairs if not src.exists()]
    if missing:
        raise SystemExit(
            "Snapshot is incomplete; refusing to reset. Missing:\n  "
            + "\n  ".join(missing)
        )


def _backup_live(pairs: list[tuple[Path, Path]]) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_dir = SNAPSHOT / ".pre_reset_backups" / stamp
    for _, dest in pairs:
        if dest.exists():
            rel = dest.name
            target = backup_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, target)
    return backup_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset Heuristics v1 learning to day zero.")
    parser.add_argument("--yes", action="store_true", help="skip confirmation prompt")
    parser.add_argument("--dry-run", action="store_true", help="show plan, change nothing")
    args = parser.parse_args()

    pairs = _planned_copies()
    _verify_snapshot(pairs)

    print("Reset Heuristics v1 to day-zero blank slate")
    print(f"  Snapshot : {SNAPSHOT}")
    print("  Will restore:")
    for src, dest in pairs:
        print(f"    {dest}  <-  {src}")
    print("  Phoenix traces are NOT touched (delete them manually if needed).")

    if args.dry_run:
        print("\nDry run — nothing changed.")
        return

    if not args.yes:
        ans = input("\nProceed? [y/N] ").strip().lower()
        if ans not in {"y", "yes"}:
            print("Cancelled.")
            return

    backup_dir = _backup_live(pairs)
    for src, dest in pairs:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    print(f"\nDone. Previous live state backed up to:\n  {backup_dir}")
    print("Active prompts reset to: drafter_v1, question_agent_v1")
    print("Search planner reset to: search_planner_v1")
    print("Remember to delete Phoenix traces manually for a full restart.")


if __name__ == "__main__":
    main()
