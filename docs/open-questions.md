# Open Questions — Aegis

These must be answered (or consciously deferred) before code begins. Items marked **🔴 BLOCKER** prevent any build work.

---

## A. Strategic & Scoping

### A4. Strategic narrative line — final wording
**Question:** Approve the one-sentence pitch: *"Phoenix isn't just monitoring Aegis — it's how Aegis improves."*
Or: *"An agent that learns insurer-specific appeal tactics from its own Phoenix traces."*
**Default if not answered:** First option (more memorable).

### A5. Builder-bio framing
**Question:** Are you comfortable putting your face on camera and stating "I'm a PM in India, not a US healthcare expert"?
**Why it matters:** The "non-domain-expert builds domain-expert agent" angle is the strongest emotional hook in the demo. If you'd prefer to stay off camera, we'll lose this and need to compensate with chart-heavier demo.

---

## B. Scope & Product

### B3. Are mental-health parity denials in scope?
**Question:** UHC's PXDX algorithm (ProPublica 2023 exposé) auto-denies mental-health codes — including this slice would be a powerful "the agent learned something a generalist wouldn't catch" demo moment. But it widens scope.
**Default:** Include as 1 of the 6 calibration cases (Cigna or UHC); not as a separate denial type.

### B4. Output format priority
**Question:** Of the appeal package outputs (letter, citations, evidence checklist, missing-info flags, risk flags), which is most important for the demo to spotlight?
**Default:** Letter + citations (most legible in video).

---

## C. Data & Evals

### C2. Calibration vs held-out split
**Question:** Confirm 6 + 6 split for MVP. Or prefer 8 + 4 (more learning data, less held-out signal)?
**Default:** 6 + 6 (balanced, lets us claim improvement on enough cases to be statistically interesting for the demo).

### C3. Held-out improvement target
**Question:** What composite-score lift v1 → v3 is "enough" to count as a win?
**Default:** +20% (e.g., 0.55 → 0.75). If we hit only +10%, we should pivot framing or extend learning iterations.

### C4. Are real anonymized denial PDFs allowed for demo, even if not for evals?
**Question:** Some users have access to their own denial letters and could donate one (with names/IDs redacted) for the hero-case demo. This makes the demo more visceral than a synthetic case.
**Default:** No — synthetic-only across the board for clean provenance.

---

## D. Simulator & Honesty

### D2. Should the simulator be tunable per insurer?
**Question:** Oracle suggests per-insurer feature weights (Cigna weights plan-language quotes higher; UHC weights clinical rationale higher). Adds rigor but more files to maintain.
**Default:** Yes, per-insurer weights — but only ship 3 sets (one per benchmark insurer).

### D3. How is the simulator framed in the demo?
**Question:** Exact framing line for the demo video to avoid overclaiming.
**Default:** *"The simulator is a transparent rule-based proxy — not a prediction of real insurer behaviour. Rules are published in the repo."*

---

## E. Technical

### E3. Python version & package manager
**Question:** Python 3.11 (ADK requirement). uv or poetry for deps?
**Default:** Python 3.11 + uv (faster, simpler).

### E7. Retrieval method for corpus
**Question:** BM25 (via `rank_bm25`) vs naive keyword vs minimal vector embed (Gemini embeddings)?
**Default:** BM25 — sufficient at our corpus size (~10–30 markdown files), no infra overhead.

### E8. Where do learned playbooks live in production?
**Question:** Git-tracked JSON in `playbooks/` (versioned, auditable, simple) vs GCS bucket vs Firestore?
**Default:** Git-tracked JSON.

---

## F. Demo Production

### F1. Recording tool
**Question:** Loom, OBS, ScreenFlow, or other?
**Default:** Loom for ease; OBS for higher production value.

### F2. Voiceover style
**Question:** Live voiceover during screen capture, or scripted + edited?
**Default:** Scripted + edited (more polish in the time available).

### F3. Hero case selection
**Question:** Which of the 12 benchmark cases is the "hero" the demo flows through? (Should be Cigna or UHC for name recognition + a denial reason that has rich learnable patterns.)
**Default:** Defer until benchmark cases are written.

### F4. End-card content
**Question:** What appears in the final 10 seconds? GitHub URL + Devpost URL minimum; add team/PM credit?
**Default:** GitHub + Devpost; add credit if solo so judges can attribute.

---

## G. Risk & Safety

### G1. Legal-review check
**Question:** Is anyone in your network willing to spend 30 minutes reviewing the disclaimer language and the "draft assistance only" framing before submission?
**Default:** Strongly recommended. A US-based legal-adjacent friend, even non-attorney, helps.

### G2. Expert sanity-check
**Question:** Oracle recommends one quick review by a US benefits navigator / healthcare ops person. Is that feasible in your network?
**Default:** Try; if no, proceed with public-source-citation defense.

---

## J. Tooling & Stack

### J1. ~~`google-agents-cli` observability ↔ Phoenix MCP compatibility~~ — **RESOLVED**
**Resolution (2026-05-27):** They coexist cleanly. Phoenix is primary via `openinference-instrumentation-google-adk` + `arize-phoenix-otel`; `otel_to_cloud=False` disables ADK's Cloud Trace. The `google-agents-cli-observability` skill is skipped. Decision logged.

### J2. `google-agents-cli` deploy skill ↔ 2-service Cloud Run topology
**Question:** Their `deploy` skill assumes Agent Runtime / single-service patterns. We deploy two services (frontend + backend) on Cloud Run. Does their deploy command handle two services cleanly, or do we need a custom deploy script?
**When it must resolve:** Day 6–7 (before MVP deploy).
**Default if not resolved:** Use `agents-cli deploy` for the backend only; write a separate Cloud Run deploy script for the Next.js frontend.

---

## I. Things explicitly NOT open questions (decided)

For clarity, these are **locked**:

- ✅ **Part A:** Single ADK agent + one offline learning job. **Part B:** 12-agent swarm + Learning Coordinator + Pattern Synthesizer (per [decision-log.md 2026-05-27](memory/decision-log.md)).
- ✅ **Next.js (App Router) frontend + Python ADK backend** — 2 Cloud Run services (per [decision-log.md 2026-05-25](memory/decision-log.md)). Reverses the earlier Streamlit-only lock.
- ✅ `google-agents-cli` adopted Day 1 for backend lifecycle (scaffold, eval, deploy, observability) — see [decision-log.md 2026-05-27](memory/decision-log.md).
- ✅ No vector DB.
- ✅ Internal appeals only (NOT external/IRO in scope; templates only for Part B).
- ✅ Commercial plans only (NOT Medicare/Medicaid).
- ✅ **Part A:** human approval required for prompt/playbook promotion. **Part B:** autonomous promotion allowed with hard safety gates + one-click rollback (PRD §15.2).
- ✅ Synthetic composite cases (NOT real PHI).
- ✅ Apache 2.0 license.
- ✅ UX is a co-equal product pillar (per [decision-log.md 2026-05-25](memory/decision-log.md)).
- ✅ Narrative is "learns insurer-specific tactics from outcomes" (NOT "learns US healthcare law").
- ✅ Tone guardrail: no violence, vigilantism, or polarizing public events around the insurance industry in any artifact (per [AGENTS.md](../AGENTS.md) and [design-brief.md §8](design-brief.md)).
- ✅ **Builder:** Solo PM (non-technical) using Amp + skills (Resolved A2)
- ✅ **Time budget:** 20 days (Resolved A3)
- ✅ **Insurer set & Denial types:** 10 insurers, 7 denial types for Full Plan. 3 insurers, 2 types for MVP. (Resolved B1, B2)
- ✅ **Eval cases:** Synthetic composite cases only (Resolved C1)
- ✅ **Simulator transparency:** Two-step transparent simulator (Resolved D1)
- ✅ **Infrastructure:** Google Cloud account, Phoenix Cloud, GitHub, Devpost accounts are assumed ready or will be created on Day 1 (Resolved E1, E2, H1, H2)
- ✅ **Phoenix MCP:** Installed via npx, backend container has Node.js (Resolved E6)
- ✅ **Pre-commit PHI scanner:** Implemented as cheap insurance (Resolved G3)

---

## Resolution Process

For each open question:
1. PM provides a one-line answer (or "use default")
2. I update the PRD / architecture / AGENTS.md as needed
3. Question moves to a "Resolved" section at the bottom (with date + decision)
4. Once all 🔴 BLOCKER items resolved → code begins
