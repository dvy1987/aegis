# ADR-007: GCP-hosted, self-growing, trust-gated research corpus (Vertex AI Search + grounded discovery)

**Date:** 2026-06-01 (Session 27)
**Status:** Accepted with budget cap + safety gates
**Mode:** CONTEMPORANEOUS to Session 27 (Part B swarm build).

## Context

Part B's 5 specialist researchers retrieve grounding evidence to build their briefs. As of Session 26 the corpus is **4 flat markdown files** in `backend/corpus/` retrieved via local BM25 (`corpus_retrieval` in `aegis_v1/tools.py`). Two problems surfaced while planning the swarm:

1. **The corpus will become heavy.** Clinical + legal + precedent + insurer authorities across 10 insurers x 7 denial types is far larger than a handful of local files; local BM25 over a growing on-disk corpus does not scale and bloats the repo.
2. **Even a seeded corpus falls short.** A researcher may need an authority (a specific guideline, IRO decision, or statute) that is not yet in the corpus. The PM asked: can the system find relevant, trustworthy literature in real time and keep it?

This collides with a hard project rule (root `AGENTS.md`): *"No invented statutes, case law, or insurer policy text. Citations come only from the controlled local corpus."* The grounding + hallucination judge hard gates depend on every citation tracing to a vetted corpus document.

## Decision

Adopt a **GCP-hosted, self-growing, trust-gated corpus**, behind a `CorpusStore` seam so offline development is unaffected:

1. **Hosting.** Corpus documents live in a **Google Cloud Storage bucket**, indexed by **Vertex AI Search** for retrieval. A `CorpusStore` Protocol has two backends: `LocalCorpusStore` (BM25 over local files; offline default) and `VertexSearchCorpusStore` (GCS + Vertex AI Search; live, credential-gated).
2. **Discovery.** When a researcher's retrieval is thin, a **Vertex grounded search restricted to a trust allow-list** discovers candidate literature. Results pass a mandatory pipeline before they can ever be cited: **sanitize (`secure-*`) -> trust-tier filter -> provenance capture -> ingest into the GCS corpus with a full audit log + one-click removal.** Ingest mode is **autonomous-with-audit** (per PM, Session 27), trust-tier filtered, reversible.
3. **Safety invariant (unchanged).** Discovery only ever **feeds the corpus**; the **corpus remains the sole citation source.** A discovered document cannot be cited until it has entered the corpus through the gate. This preserves the "controlled corpus / no invented law" rule and the grounding/hallucination gates.

### Trust allow-list (initial tiers)

`.gov` / eCFR / CMS, state Department of Insurance IRO decisions, PubMed / NIH, recognised specialty societies (AMA, APA, ACOG, etc.), ProPublica. Sources outside the allow-list are rejected at the trust-tier filter.

## Cost & budget cap

New paid GCP service (PM-approved with a cap). Hackathon-scale estimate: index storage **free** (<10 GiB free tier; a text corpus is tiny), search queries **~$0-15/mo** (10k/mo free, then ~$1.50/1k), grounded discovery **~$0** (within Vertex's ~1,500/day free grounding tier; overage ~$35/1k Vertex / ~$14/1k Gemini 3 API). PM has **$100 of free credits**.

**Guardrails:** GCP **billing alert at $30/month**; discovery is **rate-limited** (per-day + per-case caps) and **off by default** (`CORPUS_DISCOVERY_ENABLED`). Well within PRD NFR2's $200 ceiling.

## Alternatives considered

- **GCS only, keep BM25, no managed index.** Cheaper/simpler but doesn't solve heavy-corpus retrieval at scale and offers no discovery path. Rejected as the target, retained as the offline `LocalCorpusStore`.
- **Open-web real-time research (no gate).** Rejected — breaks the controlled-corpus safety rule, weakens grounding/hallucination guarantees, and opens a prompt-injection surface.
- **Human-approved ingest only.** Safer, but the PM chose autonomous-with-audit + trust-tier + one-click removal for a stronger self-improvement story; mitigations make the residual citation-integrity risk acceptable.
- **Vector DB (self-hosted).** Against `AGENTS.md` ("no vector DB unless forced"); Vertex AI Search is managed and avoids running our own.

## Consequences

- The corpus becomes a **second learning surface** alongside agent prompts: the Learning Coordinator's credit-assignment can route an `evidence_completeness` failure to a **corpus gap** (auto-served by discovery) rather than only an agent prompt.
- Offline-first preserved: all discovery *logic* (allow-list, sanitize, trust-tier, provenance, audit, one-click removal) is TDD'd against a fake search client; the real Vertex/GCS backends switch on with credentials.
- New ongoing safety obligation: `secure-*` sanitization is mandatory before any discovered content enters agent context or the corpus.
- Residual risk: an autonomously-ingested source could be wrong/outdated. Mitigated by trust-tier filter + provenance + `self_check` citation-traceability + grounding judge gate + one-click removal + audit log.

## References

- Root `AGENTS.md` (controlled-corpus rule) - [AGENTS.md](../../AGENTS.md)
- Architecture spec section 5.3/5.4 (corpus + retrieval) - [docs/architecture/2026-05-27-aegis-arch.md](../architecture/2026-05-27-aegis-arch.md)
- Part B feature spec - [docs/specs/2026-05-27-aegis-part-b-swarm-feature-spec.md](../specs/2026-05-27-aegis-part-b-swarm-feature-spec.md)
- Plan: aegis swarm runtime (Session 27)
- `secure-skill-*` skills (sanitization pipeline)
