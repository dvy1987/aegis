# Heuristics research corpus

Controlled, citable knowledge base for the appeal agents. **Citations come only
from documents in this corpus** (root `AGENTS.md`). No invented statutes, case
law, or insurer policy text.

## Layout (domain subdirectories)

| Subdir | Researcher | Content |
|---|---|---|
| `clinical/` | Medical Necessity | medical-necessity evidence standards, guideline summaries |
| `legal/` | Legal Researcher | ERISA, MHPAEA, No Surprises Act, federal/state appeal law |
| `insurer/` | Insurer Intelligence + Policy Detective | insurer appeal expectations, plan/policy criteria |
| `precedent/` | Precedent Miner | external-review / IRO precedent references |

Part A retrieves over the union of all subdirs (BM25, `aegis_v1/tools._load_corpus`).
Part B retrieves per-domain through `aegis_swarm/corpus_store.LocalCorpusStore`.

## Provenance

Every document is recorded in [`provenance.json`](provenance.json) with a
`source_tier` and `ingest_mode`:
- `seed` - hand-curated factual summary of a public authority; vetted; no
  verbatim proprietary text.
- `discovery` - added by the `LiteratureDiscovery` pipeline (ADR-007): sourced
  from a **trust-allow-listed** origin (`.gov`/eCFR/CMS, state DOI/IRO,
  PubMed/NIH, specialty societies, ProPublica), sanitized (`secure-*`),
  trust-tier filtered, provenance-stamped, ingested with an audit log, and
  one-click removable.

## Adding documents

Seed docs: add the `.md` to the right subdir and append an entry to
`provenance.json`. Never paste verbatim proprietary policy text or fabricate
citations/case numbers. The live corpus is GCS-hosted + Vertex AI Search
indexed; this directory is the offline `LocalCorpusStore` source of truth.
