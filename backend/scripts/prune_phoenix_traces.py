#!/usr/bin/env -S uv run python
"""Manually run Phoenix on-demand trace retention (same logic as the live hook)."""

from __future__ import annotations

import argparse
import os
import sys

from app.aegis_v1.phoenix_retention import prune_phoenix_spans_if_needed


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune oldest Phoenix traces when over threshold.")
    parser.add_argument("--project", default=os.environ.get("PHOENIX_PROJECT_NAME", "default"))
    parser.add_argument("--threshold", type=int, default=None)
    parser.add_argument("--batch", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("AEGIS_PHOENIX_PRUNE_ENABLED", "1")
    if args.dry_run:
        os.environ["AEGIS_PHOENIX_PRUNE_DRY_RUN"] = "1"

    result = prune_phoenix_spans_if_needed(
        project_name=args.project,
        threshold=args.threshold,
        batch=args.batch,
        dry_run=args.dry_run,
    )
    print(result)
    return 0 if result.reason != "client_init_failed" else 1


if __name__ == "__main__":
    sys.exit(main())
