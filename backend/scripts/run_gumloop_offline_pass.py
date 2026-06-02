#!/usr/bin/env python3
"""Offline Gumloop-style eval+fix pass over draft cases.

This runs a deterministic, no-LLM approximation of the Gumloop swarm defined in
`/gumloop/architecture.md` and `/gumloop/prompts/*.txt`.

It does NOT move drafts to `approved/`. It optionally applies safe auto-fixes in
place under `eval/cases/drafts/` and writes a JSONL report of critic outputs.

Usage:
  cd backend && uv run python scripts/run_gumloop_offline_pass.py
  cd backend && uv run python scripts/run_gumloop_offline_pass.py --no-fix
  cd backend && uv run python scripts/run_gumloop_offline_pass.py --max-fix-iters 0
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.evals.gumloop.runner import run_pass_on_drafts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-fix", action="store_true", help="Do not modify drafts; evaluate only.")
    parser.add_argument("--max-fix-iters", type=int, default=2)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[2]
    drafts_dir = repo / "eval" / "cases" / "drafts"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    out_report = repo / "eval" / "gumloop_runs" / ts / "offline_swarm_report.jsonl"

    summary = run_pass_on_drafts(
        drafts_dir=drafts_dir,
        out_report_path=out_report,
        apply_fixes=not args.no_fix,
        max_fix_iters=args.max_fix_iters,
    )
    print(json.dumps({"report": str(out_report), "summary": summary}, indent=2))
    return 1 if summary["schema_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

