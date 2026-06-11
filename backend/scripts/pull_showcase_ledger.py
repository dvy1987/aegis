#!/usr/bin/env python3
"""Pull showcase session JSON from GCS into backend/data/showcase_ledger (read-only)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.aegis_v1.showcase_ledger import (  # noqa: E402
    GcsLedgerStore,
    LocalLedgerStore,
    default_ledger_dir,
    parse_gcs_uri,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gcs-uri",
        default=os.environ.get("AEGIS_SHOWCASE_LEDGER_GCS_URI", "").strip(),
        help="GCS prefix (default: AEGIS_SHOWCASE_LEDGER_GCS_URI)",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=default_ledger_dir(),
        help="Local destination directory",
    )
    args = parser.parse_args()
    if not args.gcs_uri:
        print(
            "Set AEGIS_SHOWCASE_LEDGER_GCS_URI or pass --gcs-uri "
            "(e.g. gs://your-bucket/aegis-showcase-ledger)",
            file=sys.stderr,
        )
        return 1

    bucket, prefix = parse_gcs_uri(args.gcs_uri)
    source = GcsLedgerStore(bucket, prefix)
    dest = LocalLedgerStore(args.dest)
    dest.ensure_ready()

    keys = source.list_keys()
    if not keys:
        print(f"No objects under {args.gcs_uri}")
        return 0

    for key in keys:
        dest.write_text(key, source.read_text(key))
        print(f"pulled {key}")

    print(f"Synced {len(keys)} file(s) to {args.dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
