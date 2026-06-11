# Product Soul: Heuristics
Version: 1.2 | Date: 2026-06-10 | Status: Hackathon submission (Part A shipped; Part B swarm deferred)

## The User
**Primary user:** A patient or their family member who has just received a health insurance denial letter. They are stressed, exhausted, and likely dealing with a medical condition simultaneously. They do not have legal training or US healthcare system expertise.
**Current behaviour:** Giving up. 99% of denied claims are never appealed because the process is opaque, requires reading a thirty-page policy document, and fighting an AI-mediated denial engine.
**Their words:** "I just need this covered, I don't have the energy to fight them right now."

## The Business
**Model:** Open-source hackathon project (Google Cloud Rapid Agent Hackathon — Arize partner track). No commercial monetization plan.
**Year 1 must-be-true:** Win the Arize hackathon track ($5k prize) by demonstrating a **self-improving appeal system** where Phoenix is structurally load-bearing — visible GEPA learning on showcase runs, human-approved promotion, and held-out measurement lift.
**Biggest risk:** The learning loop fails to show measurable quality lift on held-out cases, or GEPA cost outweighs the lift (see Open Hypotheses below).

## The Strategy
**Alternatives:** Counterforce Health (static prompt), Sheer Health (paid/freemium full service), ignoring the denial.
**Moat (hackathon submission):**
1. *Self-improvement from outcomes:* Drafter prompt + insurer slice playbooks + US-playbook evolve from Phoenix traces and judge signal — with full diff shown before promote.
2. *Consumer-grade UX:* Calm, dignified showcase and appeal flows (not a raw chat utility).
3. *Transparent learning:* Apprentice mode only — every promotion is human-approved; Phoenix UI is on screen for the demo arc.

**Moat (post-hackathon, if pursued):** Multi-agent swarm (`aegis_swarm/`) — **deferred** until v1 economics and library-quality questions are answered.

**Strategic bet (revised June 2026):** A **single v1 Student** with a credible GEPA learning loop and premium UX beats a rushed 12-agent swarm for hackathon judging. Phoenix-driven improvement on real benchmark cohorts is the differentiator — not agent count.

## Positioning & Vibe
**"Feels like" statement:** The mechanical precision and speed of Linear crossed with the empathetic, dignified calm of Headspace.
**Anti-positioning (What we are NOT):**
- We are NOT a generic ChatGPT wrapper.
- We are NOT a legal representation service (we only provide draft assistance).
- We are NOT an aggressive, polarizing "fight the system" tool (tone must remain constructive and factual).
- We are NOT shipping a 12-agent swarm for the hackathon deadline (swarm code exists as research scaffold only).

## Values Hierarchy (Tradeoffs)
When faced with a decision, we trade off in this order:
1. **Safety over Autonomy:** Hard judge gates and human approval for every promotion in the hackathon build.
2. **Polish over Scope:** Cut swarm and insurer breadth before shipping a janky UI.
3. **Transparency over "Magic":** Show playbook diffs, citations, and promotion proposals — not silent self-modification.

## Product-Market Fit
**Status:** Pre-PMF (Hackathon prototype phase).
**Signal we're watching:** Showcase held-out simulator lift after an approved GEPA promotion (preview 5+2, production 50+20 cohorts).
**PMF signal threshold:** Arize judges see Phoenix as load-bearing and a visible before/after improvement on held-out measurement.
**Not-PMF signal:** Disabling Phoenix memory or skipping learning produces the same held-out scores; or GEPA cost per point of lift is unsustainable.

## GTM Distribution
**First user finds us via:** Devpost hackathon gallery, GitHub, or Arize promotional channels.
**Wedge channel:** The ~3-minute demo video (showcase run + Phoenix + promotion modal).
**Acquisition → Activation → Retention loop:** Watch demo → clone repo / try hosted Cloud Run → run showcase or appeal on a synthetic case.

## Open Hypotheses (must be resolved)

### Hackathon (active)
- [ ] Does Phoenix MCP + training traces provide enough signal for GEPA to lift held-out composite on the showcase cohorts?
- [ ] Does the 3-minute demo communicate both consumer UX and Phoenix learning without swarm complexity?

### Post-hackathon (priority order)
- [ ] **Library online search:** If the library agent retrieves from **broader online sources** (not only the controlled corpus), what is the measurable quality delta on held-out cases — and does it justify added latency, grounding risk, and API cost?
- [ ] **GEPA economics:** What is the **cost per promotion cycle** (training seed + GEPA rounds + post-candidate eval + measurement) vs **simulator/judge lift** at preview (7 cases) and production (70 cases) scale? Is continuous learning worth it without a cheaper signal path?
- [ ] **Swarm vs v1:** Does the deferred 12-agent swarm outperform an improved v1 Student enough to justify orchestration complexity? (Deferred until v1 economics are clear.)

## What we shipped vs what we deferred

| Shipped (hackathon) | Deferred (post-hackathon) |
|---|---|
| v1 ADK Student workflow | 12-agent Heuristics swarm runtime |
| Question agent (pre-draft interview) | Autonomous Journeyman / Master promotion |
| Slice playbooks + US-playbook | 7 denial types × 10 insurers |
| Showcase GEPA + approval modal | ~200 autonomous learning iterations |
| Preview + production showcase cohorts | Full 100-case learning matrix |
