---
artifact: feature-spec
status: Approved
constitution: docs/constitution.md@1
title: Part A (aegis-v1) — Cloud Library, Search Planner, Per-Case Discovery
slug: aegis-v1-cloud-corpus-surgical-discovery
sources:
  - docs/adr/ADR-007-gcp-corpus-vertex-discovery.md
  - docs/prd/PRD.md
  - AGENTS.md (controlled-corpus rule)
---

# Feature Spec: Part A (aegis-v1) — Cloud Library + Per-Case Surgical Discovery

## Plain-language overview (for product review)

**What changes for you**

- The appeal **reference library** moves to **Google Cloud** and is searched with **Google’s managed search** when Aegis is deployed (not only files on a laptop).
- For **this one appeal**, if the library search comes back **empty or too thin**, Aegis may do **up to 5** extra lookups on **approved trusted websites** (one trusted source per fetch), add what passes safety checks to the library, re-search after each add, then draft the letter.
- A separate **Library Search Planner** (“librarian”) decides **what to search for** — not the agent that writes the appeal letter (“author”).
- **During this appeal (Phase 3 polish):** if fetch 1–4 still leave the library too thin, a **small AI step** rewrites the **next** search phrase for this case only (still narrow, still allow-listed sites).
- **Between appeals (learning):** when judged runs show bad search outcomes, the **planner instructions** can be promoted to a new version (like drafter v2), with human approval.
- The letter still **only cites items in the library** — never raw web paragraphs.
- **No batch of similar cases** and **no “wait for the Learning Coordinator”** before the first lookup is allowed.

**Author vs librarian (one sentence)**

| Role | Job |
|------|-----|
| **Appeal author (drafter agent)** | Write the letter from library + playbook |
| **Library Search Planner (system)** | Build library search phrases and trusted-web fetch phrases (up to 5) |

**What stays the same**

- No invented statutes, case law, or insurer policy text.
- Discovery is **off until you turn it on** (environment switch), with **budget caps** already agreed in ADR-007.
- The Learning Coordinator may improve **planner** and **drafter** instructions over time; it **does not** block the first search on this appeal.

## How search gets smarter (three layers — PM-approved)

| Layer | When | What changes | Plain name |
|-------|------|----------------|------------|
| **1 — Baseline** | Every appeal | Planner follows a **versioned recipe** from case facts (insurer, denial type, procedure, etc.) | Cheat sheet v1 |
| **2 — Learning** | After **judged** failures (optional, later) | Promote **`search_planner_vN`** or playbook **search hints** per insurer/denial slice | Updated cheat sheet |
| **3 — Live polish** | **During** this appeal, between fetches | If still thin after a fetch, **small AI** proposes the **next** narrow query (fetch 2–5) | Librarian thinks between shelf runs |

Layer 3 is **in scope** for this spec. Layer 2 uses the same promotion/HITL pattern as the drafter; it does **not** require running many similar cases before Layer 1 or 3 run on the current appeal.

## Summary

Part A (aegis-v1) MUST use a cloud-hosted, searchable reference library for deployed runs, MUST route all library and discovery search phrases through a versioned **Library Search Planner** (not the letter-writing agent), MAY perform up to **five** trust-gated literature fetches per appeal when **this case’s** library search is insufficient, and MAY use **live query refinement (Layer 3)** between fetches — without requiring prior learning across many similar cases.

## Problem

Today, aegis-v1 only searches a small **local folder**. If the right guideline or authority is missing, the system flags “missing evidence” but cannot recover in the same run. The library will grow too large to ship inside the repo, and some authorities will always be missing until they are found. The person drafting an appeal needs a **small, bounded** recovery (up to five careful fetches) for **this case**, not a research project across dozens of test runs.

## User Scenarios

### US-1 — Deployed appeal with a thin library (happy path with discovery on)

**Persona:** A person using Aegis on the hosted demo (Track B).

**Scenario:** They submit one synthetic Cigna medical-necessity case. The cloud library has no matching clinical guideline. The **Search Planner** builds the first search phrase; with discovery **enabled**, Aegis fetches trusted sources (up to five), re-searches between fetches, and if fetch 1 still leaves the library thin, **Layer 3** narrows the phrase for fetch 2 (e.g. adds “clinical guideline” + procedure). Each add passes safety checks. The **author** agent then drafts citing only library items. The response shows discovery ran, planner version, and fetch count (no PHI).

### US-5 — Layer 3 polish mid-appeal

**Persona:** Same as US-1; library partially unhelpful after first fetch.

**Scenario:** Fetch 1 ingests a generic page that does not satisfy FR-2. Planner **refines** the query for fetch 2; a more targeted NIH/CMS document is ingested; library is no longer thin; **no fetch 3**. Trace shows two queries and why fetch 2 differed (laundered summary, not teacher answer key).

### US-2 — Deployed appeal with enough in the library (no discovery)

**Persona:** Same person, different case.

**Scenario:** The cloud library already contains usable sources for this denial. Aegis searches, finds enough, drafts immediately. **No** extra web lookup runs. Cost and latency stay low.

### US-3 — Offline / local development (no cloud)

**Persona:** Developer or demo in “no credentials” mode.

**Scenario:** Aegis uses the **local folder** copy of the library (same safety rules). Surgical discovery **does not** run without cloud credentials. Thin library → draft with `missing evidence` / `no_corpus_citations` flags, same as today.

### US-4 — Discovery off (default)

**Persona:** PM running cost-controlled demos.

**Scenario:** Discovery switch is **off**. Even if the library is thin, Aegis **never** fetches from the web; it drafts conservatively and surfaces risk flags. Cloud search over **existing** library content still works when deployed.

## Functional Requirements

- **FR-1 (cloud library):** When aegis-v1 runs in a **deployed, credential-backed** environment, appeal-time source lookup MUST search the **cloud-hosted reference library** (documents in cloud storage, indexed for search). Local-only library search remains available for offline development without cloud credentials.

- **FR-2 (thin-for-this-case):** The system MUST treat library results as **too thin for this appeal** when, after the standard case-driven search for this appeal, there are **zero citable documents** in the controlled library that can support a grounded citation for this denial (insurer + denial type + service/procedure context). **Low-quality or mismatched hits** (wrong insurer, wrong denial type, or otherwise not usable for a grounded citation on this slice) MUST be treated the same as no hits — i.e. FR-2 remains true (PM decision, CL-1 resolved 2026-06-01).

- **FR-3 (per-case surgical discovery):** When FR-2 is true **and** surgical discovery is **enabled**, the system MAY perform trust-gated literature fetches for **this appeal only**, up to the per-appeal cap in **FR-8**. Each fetch MUST use a search phrase produced by the **Library Search Planner (FR-11–FR-13)**. After each successful ingest, the system MUST re-evaluate FR-2; it MUST stop fetching when the library is no longer thin for this case or when FR-8 is reached. The system MUST NOT require prior runs, benchmark batches, or Learning Coordinator approval before the first fetch.

- **FR-11 (Library Search Planner owns queries):** All **cloud library search** phrases and all **trusted-web discovery** phrases for aegis-v1 MUST be produced by a dedicated **Library Search Planner** component. The appeal-writing agent (drafter) MUST NOT supply free-form search text on the deployed cloud + discovery path. Offline local-only mode MAY retain a deterministic default recipe without Layer 3.

- **FR-12 (versioned planner):** The planner MUST be a **versioned, evolvable component** (e.g. `search_planner_v1`) distinct from the drafter prompt. Each run MUST stamp `search_planner_version` in trace metadata. Promotion of a new planner version MUST follow the same human-approval promotion path as other evolvable prompts (constitution C-1.2 on held-out gates).

- **FR-13 (Layer 3 — live query refinement):** For discovery fetch **2 through 5**, when FR-2 is still true after the prior fetch and re-search, the planner MAY invoke a **small, bounded AI refinement step** that outputs only the **next narrow search phrase** for this case. Inputs MUST be firewall-safe: structured case facts, fetch index, prior phrase(s), thin-library signal, counts of hits/ingests/rejects — and MUST NOT include teacher-only judge answer keys, simulator rubric thresholds, or raw appeal letter text. Output MUST be a single phrase (or structured equivalent) suitable for allow-listed discovery — not URLs chosen by the user, not “search the whole web.”

- **FR-14 (Layer 2 — planner learning, deferred implementation detail):** When held-out judged runs show **evidence_completeness** or **grounding** failures attributable to search (thin library after planner-led fetches, or repeated reject/empty ingest), the Learning Coordinator MAY propose mutations to **`search_planner`** or playbook **`discovery_query_hints`** for that insurer/denial slice. This is **between-appeal** improvement (Layer 2); it MUST NOT be a prerequisite for Layer 1 or Layer 3 on the current appeal.

- **FR-4 (trust gate + ingest):** Every candidate from FR-3 MUST pass the same trust and safety pipeline defined in ADR-007: content sanitization, trust-tier allow-list only, provenance recorded, ingest into the cloud library with audit log, and ability to remove ingested items. Candidates that fail any gate MUST be rejected and MUST NOT enter the library.

- **FR-5 (corpus-only citations):** The appeal letter and `AppealPackage` citations MUST reference **only** documents present in the controlled library **after** any successful ingest. Raw web snippets MUST NOT appear as citations or be pasted into the letter body.

- **FR-6 (re-search then draft):** After a successful FR-4 ingest, the system MUST search the library again for this appeal before drafting. If ingest adds nothing usable, drafting proceeds with existing risk flags (no invented sources).

- **FR-7 (discovery default off):** Surgical discovery MUST be **disabled by default**. When disabled, FR-3 through FR-6 MUST NOT run regardless of thin library.

- **FR-8 (caps):** For aegis-v1, surgical discovery MUST NOT exceed **5 trust-gated fetches per appeal** and MUST respect global per-day discovery caps and budget guardrails in ADR-007 ($30/month billing alert, rate limits).

- **FR-9 (transparency):** Each appeal run MUST record in trace metadata: `search_planner_version`, library search phrase(s) used, whether discovery ran, per-fetch discovery phrases (up to 5), `discovery_fetch_count`, ingest/reject counts, whether Layer 3 refinement ran, and standard case metadata (case_id, insurer, denial_type, etc.) — without logging PHI.

- **FR-10 (student tool surface unchanged):** The aegis-v1 agent exposed to the model MUST remain the **six** student tools in the existing order (case parser → corpus retrieval → Phoenix lookup → playbook → drafter → self-check). Surgical discovery and **planner query construction** MUST NOT be separate tools the model can invoke at will; the system supplies retrieval results (and discovery side effects) on the controlled path before or while the author agent runs.

## Non-Functional Requirements

- **NFR-1 (safety):** FR-3 through FR-6 MUST NOT weaken constitution hard gates C-1.2 (AlphaEval safety / hallucination gates on promotion paths) or the project rule “citations only from the controlled corpus.”

- **NFR-2 (cost):** Combined cloud search + discovery + Layer 3 planner refinement calls for Part A MUST stay within ADR-007 hackathon guardrails and PRD API budget ceilings; discovery off by default is the primary cost control. Layer 3 MUST NOT run more than **four** refinement calls per appeal (one per fetch 2–5, only while FR-2 remains true).

- **NFR-3 (observability):** FR-9 fields MUST be visible in Phoenix traces for demo credibility (C-5.1).

- **NFR-4 (latency):** When discovery is off or library is sufficient, p95 appeal latency MUST not regress versus current local-BM25 behavior by more than 20% for the same stubbed/offline path.

- **NFR-5 (privacy):** FR-9 and audit logs MUST NOT contain PHI (C-2.1); synthetic case identifiers only.

## Acceptance Criteria

### AC-FR-1.1
**Given** aegis-v1 deployed with valid cloud credentials and a non-empty cloud library index  
**When** a person submits one synthetic appeal case  
**Then** corpus retrieval for that appeal queries the cloud library (not laptop-only files) and returns hits traceable to library document IDs.

### AC-FR-2.1
**Given** cloud library search for this case returns zero citable documents  
**When** the system evaluates thin-library for this appeal  
**Then** FR-2 is true and the run is eligible for FR-3 (if discovery enabled).

### AC-FR-2.2
**Given** cloud library search returns only hits that mismatch this case’s insurer or denial type (or are otherwise not citable for this slice)  
**When** the system evaluates thin-library for this appeal  
**Then** FR-2 is true (same as zero hits) and the run is eligible for FR-3 (if discovery enabled).

### AC-FR-3.1
**Given** FR-2 true and surgical discovery **enabled**  
**When** this appeal is processed  
**Then** at least one and at most **five** trust-gated fetches may run for this case; each fetch uses a planner-produced phrase (no user-supplied arbitrary URL list), and fetching stops early if FR-2 becomes false before the cap.

### AC-FR-3.2
**Given** FR-2 true and surgical discovery **disabled**  
**When** this appeal is processed  
**Then** zero trust-gated fetches run and the draft includes a thin-library risk flag.

### AC-FR-4.1
**Given** a discovery candidate from a non-allow-listed domain  
**When** the trust gate runs  
**Then** the candidate is rejected, logged in the audit trail, and never ingested.

### AC-FR-4.2
**Given** a discovery candidate containing hidden-content / injection patterns per ADR-007 sanitization rules  
**When** sanitization runs  
**Then** the candidate is rejected and never ingested.

### AC-FR-5.1
**Given** a successful ingest from FR-4  
**When** the appeal letter is produced  
**Then** every citation ID in the package exists in the post-ingest library and `self_check` reports no untraceable citations.

### AC-FR-6.1
**Given** FR-4 ingested at least one accepted document  
**When** drafting begins  
**Then** library search runs again for this appeal and the draft may cite the newly ingested document ID.

### AC-FR-7.1
**Given** a fresh deployment with no discovery override  
**When** any appeal runs  
**Then** surgical discovery is off (FR-3 does not run).

### AC-FR-8.1
**Given** discovery enabled and FR-2 true for an appeal  
**When** that appeal is processed end-to-end  
**Then** at most **five** discovery fetches occur for that appeal even if retrieval is still thin afterward.

### AC-FR-9.1
**Given** any appeal run in Phoenix-instrumented mode  
**When** the trace is viewed  
**Then** metadata includes `discovery_enabled`, `discovery_ran`, and `discovery_ingested_count` (or equivalent boolean/count fields) plus case slice metadata.

### AC-FR-10.1
**Given** the aegis-v1 ADK agent tool list  
**When** inspected  
**Then** exactly six student tools are registered and no `discover` / `web_search` / `search_planner` tool is exposed to the model.

### AC-FR-11.1
**Given** a deployed appeal on the cloud + discovery path  
**When** library search and any discovery fetches run  
**Then** search phrases are attributed to `search_planner_version` in metadata and are not taken from free-form `corpus_retrieval` arguments supplied by the letter-writing agent.

### AC-FR-13.1
**Given** FR-2 still true after discovery fetch 1 and discovery enabled  
**When** fetch 2 is prepared  
**Then** Layer 3 MAY run and the fetch-2 phrase MUST differ from fetch-1 when refinement runs; both phrases appear in trace metadata.

### AC-FR-13.2
**Given** FR-2 becomes false after fetch 2  
**When** the appeal continues  
**Then** no fetch 3 and no further Layer 3 refinement calls occur.

### AC-FR-12.1
**Given** a promoted `search_planner_v2` on a slice  
**When** the next appeal on that slice runs  
**Then** trace metadata reports `search_planner_version` = v2 for that run.

## Edge Cases

- **EC-1 — Discovery on but all candidates rejected:** Library stays thin → draft proceeds with `no_corpus_citations` (or equivalent) and audit shows reject reasons; no invented citations.

- **EC-2 — Cloud index empty (greenfield):** First appeal with discovery on may ingest zero to five documents; system MUST NOT exceed five fetches in the same appeal (FR-8).

- **EC-3 — Cloud credentials missing mid-deploy:** System falls back to local library search; discovery does not run; run completes with degraded flags, no crash.

- **EC-4 — Duplicate ingest:** Same URL/title already in library → skip re-ingest; re-search uses existing document; audit notes duplicate.

- **EC-5 — Simulator / eval path:** Outcome Simulator and eval harness use the same library + discovery rules for this case so scores match interactive appeals (no secret extra sources in eval only).

- **EC-6 — Layer 3 proposes overly broad phrase:** Refinement output is rejected by planner guardrails (max length, banned “search entire web” patterns); system falls back to deterministic recipe for that fetch or skips the fetch; audit logs the rejection.

- **EC-7 — Layer 3 unavailable (offline / no creds):** Fetches 1–5 use Layer 1 recipe only; no refinement calls; appeal completes without crash.

## Out of Scope

- Requiring **multiple similar cases** or Learning Coordinator analysis before allowing FR-3 for this appeal.
- Learning Coordinator **approving** each discovery fetch (HITL per fetch) — may be added later; not in this spec.
- Part B swarm multi-researcher fan-out, per-domain discovery caps >1 per appeal, or weak-v1 prompt experiments.
- Open-web search without trust allow-list; citing search snippets directly in the letter.
- Medicare/Medicaid, live insurer filing, PHI in library or traces.
- Changing the six-tool agent instruction order or adding a seventh model-invokable tool for the author agent.
- Letter-writing agent choosing its own web or library search phrases on the cloud path.
- Full autonomous promotion of `search_planner` without human approval (same as drafter).
- Human medical or legal advice; “this will win” claims.

## Relationship to other work

- **ADR-007** defines trust tiers, ingest pipeline, budget caps, and “discovery feeds the library only.” This spec applies Part A as **per-case discovery with a max of 5 fetches per appeal** (stricter stop-when-sufficient behavior than a blind loop) and **explicitly rejects** coordinator-gated discovery for v1. Part B swarm may keep a lower per-case cap (e.g. 3); v1’s cap is **5** per PM decision.
- **Part B swarm** may keep broader discovery (higher per-case cap, multiple researchers). Shared safety pipeline is desirable but not specified here (implementation plan).

## Constitution Waivers

- **None.** Managed cloud search over a hosted library is consistent with C-4.1 (no self-hosted vector database). ADR-007 already reflects PM approval for paid GCP search/discovery within caps.

## Resolved Clarifications

- **CL-1 (resolved 2026-06-01, PM: yes):** Junk or mismatched library hits count as **too thin** — discovery and Layer 3 refinement MAY proceed the same as for zero hits. “Citable for this denial” requires at least one hit that matches the case slice (insurer + denial type + service/procedure context).

## Needs Clarification

- None.

## Review Checklist

- [x] Plain-language overview for non-technical readers
- [x] Every FR has ≥1 AC
- [x] Coordinator / batch-case trigger explicitly out of scope
- [x] Measurable caps (5 per appeal, off by default)
- [x] Constitution referenced; no waivers
- [x] Layer 3 live polish in scope (PM 2026-06-01)
- [x] Library Search Planner FR-11–FR-14
- [x] CL-1 resolved (PM yes, 2026-06-01)
- [x] Out of Scope non-empty
