# Open Questions — Reverse

These must be answered (or consciously deferred) before code begins. Items marked **🔴 BLOCKER** prevent any build work.

---

## A. Strategic & Scoping

### A1. 🔴 BLOCKER — Final track lock-in
**Question:** Confirm Arize as the target track. We've been planning for it; this question is just to lock it in.
**Default if not answered:** Arize.

### A2. 🔴 BLOCKER — Solo build or team?
**Question:** Are you building alone, or is there a co-builder for demo polish / video production / writing?
**Why it matters:** A 3-minute demo video is half the submission. Solo builders should budget 8–12 hours for video production alone.

### A3. 🔴 BLOCKER — Time budget
**Question:** What is the hackathon submission deadline, and how many focused hours per week can you commit between now and then?
**Why it matters:** Reverse is ~30–50 hours of focused work for a non-developer using Amp/Cursor. If you have <20 hours total, we should pre-emptively cut the learning job and ship only the v1 + simulated v3 prompts.

### A4. Strategic narrative line — final wording
**Question:** Approve the one-sentence pitch: *"Phoenix isn't just monitoring Reverse — it's how Reverse improves."*
Or: *"An agent that learns insurer-specific appeal tactics from its own Phoenix traces."*
**Default if not answered:** First option (more memorable).

### A5. Builder-bio framing
**Question:** Are you comfortable putting your face on camera and stating "I'm a PM in India, not a US healthcare expert"?
**Why it matters:** The "non-domain-expert builds domain-expert agent" angle is the strongest emotional hook in the demo. If you'd prefer to stay off camera, we'll lose this and need to compensate with chart-heavier demo.

---

## B. Scope & Product

### B1. 🔴 BLOCKER — Insurer set lock-in
**Question:** Confirm benchmark insurer set as **Aetna, Cigna, UnitedHealthcare**. Or swap one (e.g., BCBS, Anthem, Humana)?
**Default:** Aetna, Cigna, UHC (most public reporting available; most judge-recognizable).

### B2. 🔴 BLOCKER — Denial-type lock-in
**Question:** Confirm benchmark denial types as **medical necessity** + **prior authorization / missing pre-auth**. Or swap one?
**Default:** As stated.

### B3. Are mental-health parity denials in scope?
**Question:** UHC's PXDX algorithm (ProPublica 2023 exposé) auto-denies mental-health codes — including this slice would be a powerful "the agent learned something a generalist wouldn't catch" demo moment. But it widens scope.
**Default:** Include as 1 of the 6 calibration cases (Cigna or UHC); not as a separate denial type.

### B4. Output format priority
**Question:** Of the appeal package outputs (letter, citations, evidence checklist, missing-info flags, risk flags), which is most important for the demo to spotlight?
**Default:** Letter + citations (most legible in video).

### B5. Single-user demo only — confirm
**Question:** Confirm no user accounts, no auth, no multi-tenant. Just a public Cloud Run URL with the demo benchmark cases.
**Default:** Confirmed.

---

## C. Data & Evals

### C1. 🔴 BLOCKER — Eval case construction approach
**Question:** Synthetic composite cases (oracle's recommendation, lower risk) vs lightly anonymized real cases from r/HealthInsurance (richer, higher provenance risk)?
**Default:** Synthetic composite. PRD assumes this. If you want real anonymized cases, flag now and we'll need additional ethics framing.

### C2. Calibration vs held-out split
**Question:** Confirm 6 + 6 split. Or prefer 8 + 4 (more learning data, less held-out signal)?
**Default:** 6 + 6 (balanced, lets us claim improvement on enough cases to be statistically interesting for the demo).

### C3. Held-out improvement target
**Question:** What composite-score lift v1 → v3 is "enough" to count as a win?
**Default:** +20% (e.g., 0.55 → 0.75). If we hit only +10%, we should pivot framing or extend learning iterations.

### C4. Are real anonymized denial PDFs allowed for demo, even if not for evals?
**Question:** Some users have access to their own denial letters and could donate one (with names/IDs redacted) for the hero-case demo. This makes the demo more visceral than a synthetic case.
**Default:** No — synthetic-only across the board for clean provenance.

---

## D. Simulator & Honesty

### D1. 🔴 BLOCKER — Simulator transparency level
**Question:** Confirm the two-step transparent simulator (LLM feature extraction → deterministic rules) per PRD §9.3. Or simpler/more-complex alternative?
**Default:** As specified.

### D2. Should the simulator be tunable per insurer?
**Question:** Oracle suggests per-insurer feature weights (Cigna weights plan-language quotes higher; UHC weights clinical rationale higher). Adds rigor but more files to maintain.
**Default:** Yes, per-insurer weights — but only ship 3 sets (one per benchmark insurer).

### D3. How is the simulator framed in the demo?
**Question:** Exact framing line for the demo video to avoid overclaiming.
**Default:** *"The simulator is a transparent rule-based proxy — not a prediction of real insurer behaviour. Rules are published in the repo."*

---

## E. Technical

### E1. 🔴 BLOCKER — Cloud account ready?
**Question:** Do you have an active Google Cloud account with billing enabled, Cloud Run access, and Gemini API quota?
**Default:** Assume yes; verify before build start. Free tier is sufficient.

### E2. 🔴 BLOCKER — Phoenix Cloud account ready?
**Question:** Free Phoenix Cloud account created? API key in hand?
**Default:** Sign up at https://app.phoenix.arize.com — takes 2 minutes.

### E3. Python version & package manager
**Question:** Python 3.11 (ADK requirement). uv or poetry for deps?
**Default:** Python 3.11 + uv (faster, simpler).

### E4. Streamlit confirmed over alternatives?
**Question:** Confirm Streamlit. Gradio and FastAPI+HTMX are alternatives.
**Default:** Streamlit (fastest for a demo; oracle agrees).

### E5. ADK vs raw `google-genai`
**Question:** Hackathon spec requires ADK / Agent Platform SDK / Cloud Run for the Arize track. Confirm ADK.
**Default:** ADK (closest match to "code-owned agent runtime" + best instrumentor support).

### E6. Phoenix MCP — npx or Docker?
**Question:** `@arizeai/phoenix-mcp` runs via npx. Acceptable to require Node.js in the Cloud Run container, or prefer Docker-installed?
**Default:** npx — simpler.

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

### G3. Pre-commit PHI scanner
**Question:** Implement pre-commit hook to scan for SSN/MRN/date-of-birth patterns?
**Default:** Yes. Cheap insurance.

---

## H. Submission Logistics

### H1. 🔴 BLOCKER — Devpost account
**Question:** Devpost account created and joined to the hackathon?
**Default:** Sign up at https://rapid-agent.devpost.com if not.

### H2. 🔴 BLOCKER — Public GitHub repo
**Question:** Create public GitHub repo with Apache 2.0 license now (before any code). License must be detectable in repo About section.
**Default:** Yes — do it before writing any code.

### H3. Submission narrative copy
**Question:** Devpost form asks for project description, "inspiration," "what it does," "how it's built," "what's next." Write these in advance from the PRD or wait until the project ships?
**Default:** Write after agent works end-to-end; reuse PRD content liberally.

---

## I. Things explicitly NOT open questions (decided)

For clarity, these are **locked** per the oracle's recommendation:

- ✅ Single ADK agent + one offline learning job (NOT multi-agent swarm)
- ✅ Streamlit (NOT Next.js / React)
- ✅ No vector DB
- ✅ Internal appeals only (NOT external/IRO)
- ✅ Commercial plans only (NOT Medicare/Medicaid)
- ✅ Human approval required for prompt/playbook promotion (NOT autonomous mutation)
- ✅ Synthetic composite cases (NOT real PHI)
- ✅ Apache 2.0 license
- ✅ Narrative is "learns insurer-specific tactics" (NOT "learns US healthcare law")

---

## Resolution Process

For each open question:
1. PM provides a one-line answer (or "use default")
2. I (Amp) update the PRD / architecture / AGENTS.md as needed
3. Question moves to a "Resolved" section at the bottom (with date + decision)
4. Once all 🔴 BLOCKER items resolved → code begins

---

## Resolved

*(empty — populate as questions close)*
