# Cloud library — ingest runbook

**Cost rule:** Do not create GCP resources or upload until the demo window. All prep work runs locally at $0.

## Prerequisites

- Python 3.11 + `uv` (backend)
- Network access for downloading public sources
- For upload (demo day only): `gcloud` auth + `AEGIS_LIBRARY_BUCKET` + Vertex data store configured

## 1. Regenerate catalog (after editing entries)

```bash
cd backend && uv run python library/generate_seed_catalog.py
```

## 2. Validate catalog (no network)

```bash
cd backend && uv run python scripts/ingest_library_seed.py --dry-run
```

## 3. Stage documents locally (temp disk only)

```bash
cd backend && uv run python scripts/ingest_library_seed.py --priority 1 --fresh
# Or full catalog:
cd backend && uv run python scripts/ingest_library_seed.py --fresh
```

Output: `/tmp/aegis-library-staging/` + `manifest/provenance.json`

## 4. Generate spot-check queries (from 500 cases)

```bash
cd backend && uv run python scripts/generate_library_spot_checks.py
```

Output: `eval/library/spot_check_queries.json`

## 5. Demo day — upload to GCS (spends credits)

Only when ready to index:

```bash
export AEGIS_LIBRARY_BUCKET=your-bucket-name
cd backend && uv run python scripts/ingest_library_seed.py --fresh --upload
```

Then in GCP Console: trigger Vertex AI Search import on `gs://$AEGIS_LIBRARY_BUCKET/library/v1/**`

Set backend env:

```
VERTEX_SEARCH_DATA_STORE_ID=...
VERTEX_SEARCH_PROJECT=...
VERTEX_SEARCH_LOCATION=global
```

## 6. Post-index QA

Run representative queries from `eval/library/spot_check_queries.json` against Vertex (or local BM25 on staged markdown for rough check).

**Pass:** ≥1 hit per priority-1 query for each insurer × denial slice; clinical queries return PMC/guideline content for top treatments.

## Expanding toward ~500 documents

The seed catalog starts ~60–80 **high-trust** sources. Expand by:

1. Adding PMC CC BY articles per diagnosis cluster (see case treatment histogram in spot-check output).
2. Adding state DOI appeal guides for states appearing in synthetic cases.
3. **Not** scraping insurer CPBs or NCCN.

Each new row needs: `license`, `trust_tier`, `domain`, `topics`, `source_url`.
