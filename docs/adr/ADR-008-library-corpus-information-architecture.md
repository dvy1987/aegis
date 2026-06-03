# ADR-008: Cloud library information architecture (seed corpus for 500-case benchmark)

**Date:** 2026-06-02  
**Status:** Accepted  
**Deciders:** PM (corpus policy), engineering (ingest + index contract)

## Context

Part A v1 uses a **cloud-only** library (`UnavailableCorpusStore` when Vertex is unset). The 500-case eval corpus spans **Aetna, Cigna, UHC** × **medical necessity / prior authorization**, with denial patterns referencing ERISA, MHPAEA, external review, EviCore/UM vendors, and diverse clinical services.

Runtime discovery (≤5 fetches/case) is allowed but costs GCP credits and adds latency. The PM directed: **stock the library so discovery is rarely needed** for benchmark runs, while **not spending GCP credits until the demo window**.

## Decision

1. **Single catalog of record** in git: `backend/library/seed_catalog.json` (~150+ curated entries at launch; expandable to ~500 over time).
2. **Redistribution-safe only** at ingest: US gov, CC BY (PMC), insurer-public process docs, journalism via factual summaries where needed.
3. **Ingest pipeline** (`backend/scripts/ingest_library_seed.py`): download → temp normalize → manifest; **`--upload` off by default** (no GCS spend until PM runs demo setup).
4. **Metadata schema** documented in `docs/library/metadata-schema.md`; controlled vocab in `backend/library/controlled_vocab.json`.
5. **Spot-check queries** generated from `eval/cases/drafts/` → `eval/library/spot_check_queries.json` for post-index retrieval QA.

## GCS layout

See `docs/library/metadata-schema.md`. Bucket name via env `AEGIS_LIBRARY_BUCKET` (not created by agents without PM approval).

## Consequences

- Agents can develop and review the full corpus **offline** (catalog + dry-run ingest) with zero Vertex cost.
- Demo day: enable APIs, create bucket + data store once, run `ingest_library_seed.py --upload`, import/index, set `VERTEX_SEARCH_*`.
- Catalog maintenance is a **product task** (add URL + metadata), not ad-hoc downloads.

## Alternatives considered

- **Store corpus in git** — rejected (repo size, PM laptop storage).
- **Discovery-only library** — rejected (latency, cost, weaker grounding guarantees).
- **Scrape insurer CPBs** — rejected (copyright; violates controlled-corpus rule).

## References

- [ADR-007](ADR-007-gcp-corpus-vertex-discovery.md)
- [metadata-schema.md](../library/metadata-schema.md)
- [seed_catalog.json](../../backend/library/seed_catalog.json)
