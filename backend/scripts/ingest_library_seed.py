#!/usr/bin/env python3
"""Ingest curated library seed catalog into local staging (and optionally GCS).

No GCP spend unless --upload is passed with AEGIS_LIBRARY_BUCKET set.

Examples:
  cd backend && uv run python scripts/ingest_library_seed.py --dry-run
  cd backend && uv run python scripts/ingest_library_seed.py --max 20
  cd backend && uv run python scripts/ingest_library_seed.py --priority 1
  cd backend && uv run python scripts/ingest_library_seed.py --upload  # demo day only
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure backend root on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.library.ingest import (  # noqa: E402
    clear_staging,
    load_seed_catalog,
    run_ingest,
    upload_to_gcs,
    validate_catalog,
)

_LOG = logging.getLogger("ingest_library_seed")
DEFAULT_STAGING = Path("/tmp/aegis-library-staging")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest Aegis library seed catalog")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "library" / "seed_catalog.json",
    )
    parser.add_argument("--staging", type=Path, default=DEFAULT_STAGING)
    parser.add_argument("--dry-run", action="store_true", help="Validate catalog only")
    parser.add_argument("--max", type=int, default=None, help="Max entries to download")
    parser.add_argument(
        "--priority",
        type=int,
        default=2,
        help="Include entries with priority <= N (1=must-have)",
    )
    parser.add_argument("--fresh", action="store_true", help="Clear staging dir first")
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload staging to GCS (requires AEGIS_LIBRARY_BUCKET)",
    )
    parser.add_argument("--bucket", default=None, help="GCS bucket (or AEGIS_LIBRARY_BUCKET)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    catalog = load_seed_catalog(args.catalog)
    errors = validate_catalog(catalog)
    if errors:
        _LOG.error("Catalog validation failed (%d issues):", len(errors))
        for e in errors[:20]:
            _LOG.error("  %s", e)
        return 1

    summary = {
        "catalog_version": catalog.version,
        "entry_count": len(catalog.entries),
        "priority_1": sum(1 for e in catalog.entries if e.priority == 1),
        "by_domain": {},
    }
    for e in catalog.entries:
        summary["by_domain"][e.domain] = summary["by_domain"].get(e.domain, 0) + 1

    print(json.dumps(summary, indent=2))

    if args.dry_run:
        _LOG.info("Dry run OK — no downloads")
        return 0

    if args.fresh:
        clear_staging(args.staging)

    report = run_ingest(
        catalog,
        args.staging,
        max_entries=args.max,
        priority_max=args.priority,
    )
    print(json.dumps(report, indent=2))

    if args.upload:
        import os

        bucket = args.bucket or os.environ.get("AEGIS_LIBRARY_BUCKET", "")
        if not bucket:
            _LOG.error("Set --bucket or AEGIS_LIBRARY_BUCKET for upload")
            return 1
        _LOG.info("Uploading to gs://%s/library/v1/ ...", bucket)
        n = upload_to_gcs(args.staging, bucket)
        _LOG.info("Uploaded %d files", n)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
