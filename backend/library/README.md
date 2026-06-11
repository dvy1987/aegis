# Heuristics cloud library (seed catalog)

Curated, **redistributable-safe** sources for the Vertex AI Search corpus. Not stored in git as document blobs — only this catalog and tooling.

| File | Purpose |
|------|---------|
| `seed_catalog.json` | Generated list of URLs + metadata (run `generate_seed_catalog.py`) |
| `controlled_vocab.json` | Allowed enums for facets |
| `generate_seed_catalog.py` | Source of truth for catalog entries |

**Docs:** [docs/library/metadata-schema.md](../../docs/library/metadata-schema.md) · [runbook](../../docs/library/runbook.md) · [ADR-008](../../docs/adr/ADR-008-library-corpus-information-architecture.md)

**Ingest:** `backend/scripts/ingest_library_seed.py` (local staging; `--upload` only on demo day)
