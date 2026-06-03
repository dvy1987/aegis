# Aegis Cloud Library — Metadata Schema

**Status:** Active (2026-06-02)  
**Audience:** Engineers indexing GCS → Vertex AI Search; PM review of corpus coverage  
**Related:** [ADR-008](../adr/ADR-008-library-corpus-information-architecture.md), [ADR-007](../adr/ADR-007-gcp-corpus-vertex-discovery.md)

## Purpose

Every document in the cloud library carries structured metadata so researchers, the v1 Search Planner, and Vertex AI Search filters can return **relevant, citable** hits for Aetna / Cigna / UHC appeals (medical necessity + prior authorization) without relying on runtime discovery.

## GCS object layout (no blobs in git)

```
gs://{AEGIS_LIBRARY_BUCKET}/library/v1/
  manifest/
    catalog.json          # full seed catalog (this repo: backend/library/seed_catalog.json)
    provenance.json       # post-ingest audit (generated)
    ingest_report.json    # last run stats (generated)
  legal/
    {doc_id}.md
  clinical/
    {doc_id}.md
  insurer/
    {doc_id}.md
  precedent/
    {doc_id}.md
```

PDFs are stored as `{doc_id}.pdf` in the same folder when the source is PDF-native; Vertex layout parser ingests PDF at index time.

## Required document fields (Vertex `struct_data`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `doc_id` | string | yes | Stable id, e.g. `legal/ecfr-45-cfr-147-136.md` |
| `corpus_doc_id` | string | yes | Same as filename for citation trace-back |
| `domain` | enum | yes | `clinical` \| `legal` \| `insurer` \| `precedent` (`policy` → `insurer`) |
| `title` | string | yes | Human-readable title |
| `trust_tier` | enum | yes | See controlled vocab |
| `license` | enum | yes | Redistribution class (see below) |
| `source_url` | string | yes | Canonical URL fetched from |
| `source_org` | string | no | CMS, DOL, Cigna, PMC, etc. |
| `retrieved_at` | string | yes | ISO date of ingest |
| `ingest_mode` | string | yes | `seed` (curated batch) or `discovery` |
| `insurers` | string[] | no | `Aetna`, `Cigna`, `UHC` when insurer-specific |
| `denial_types` | string[] | no | `Medical Necessity`, `Prior Authorization` |
| `topics` | string[] | no | Controlled topic tags for faceting |
| `content` | string | yes | Normalized markdown body (index field) |
| `uri` | string | yes | `gs://...` object URI |

## Controlled vocabularies

Canonical values live in [`backend/library/controlled_vocab.json`](../../backend/library/controlled_vocab.json).

### `trust_tier` (aligns with `corpus_store.TRUST_TIERS`)

- `gov_regulatory` — federal/state regulatory text (.gov, eCFR, CMS, DOL)
- `state_doi_iro` — state insurance department / IRO consumer guides
- `peer_reviewed` — PubMed Central / NIH open access
- `specialty_society` — AMA, APA, etc. (public PDFs only)
- `journalism` — ProPublica (investigative, not legal authority)
- `insurer_public` — insurer-published appeal instructions / forms (not proprietary CPB verbatim)

### `license` (redistribution gate — **ingest rejects if missing or `unknown`**)

| Value | Meaning |
|-------|---------|
| `us_gov_public_domain` | US government work |
| `cc_by_4` | Creative Commons Attribution 4.0 |
| `cc_by_nc_4` | CC BY-NC 4.0 (stored; flagged for commercial reuse review) |
| `insurer_public_terms` | Insurer-hosted public PDF/page; factual appeal-process extraction only |
| `journalism_fair_use_summary` | Factual summary + link; no full article paste |

### `topics` (benchmark-aligned)

Core topics mapped to the 500-case denial patterns:

- `appeals_rights`, `external_review`, `erisa_claims`, `mhpaea_parity`, `prior_authorization`, `medical_necessity`, `utilization_management`, `behavioral_health`, `step_therapy`, `experimental_investigational`, `claim_file_request`, `iro_precedent`, `evicore_um`, `documentation_deadlines`

Clinical subtopics (examples): `tms_ocd`, `migraine_preventive`, `adhd_treatment`, `ptsd_therapy`, `substance_use`, `orthopedic_surgery`, `bariatric`, `endocrine`

## Thin-library coverage targets

For **500 draft cases** (≈175 Cigna / 167 Aetna / 158 UHC; 247 mednec / 253 prior auth), the seed corpus MUST include at minimum:

| Layer | Target docs | Role |
|-------|-------------|------|
| Federal legal | 25+ | ERISA 503, ACA 2719 / 45 CFR 147.136, MHPAEA, NSA, claim-file rights |
| Insurer process | 30+ | Official appeal forms + disputes pages per insurer |
| State precedent | 15+ | DOI appeal guides (WA, CA, NY, TX) |
| Clinical OA | 60+ | PMC CC BY for top treatment/diagnosis clusters in cases |
| Journalism / context | 5+ | ProPublica EviCore (pattern: algo / UM vendor) |
| Society / PA burden | 5+ | AMA prior-auth surveys |

**Goal:** ≥3 relevant hits per standard Search Planner query on a representative case **without** discovery. Discovery remains a safety net, not the primary path.

## Indexing notes (Vertex AI Search)

- Enable **layout parsing** for PDFs.
- Chunk size: default managed (≈500 tokens); legal/regulatory docs benefit from larger context — tune in GCP console at demo setup.
- Filter expression example: `domain: ANY("legal") AND topics: ANY("mhpaea_parity")`
- `DiscoveryEngineVertexBackend` reads `domain` from struct data (see `vertex_search.py`).

## Safety

- No verbatim proprietary insurer CPB / NCCN text.
- No invented statutes or case numbers.
- Catalog entries without `license` or with `license: unknown` are **skipped** at ingest.
