# Product Soul: Aegis
Version: 1.1 | Date: 2026-05-27 | Status: Hackathon Context

## The User
**Primary user:** A patient or their family member who has just received a health insurance denial letter. They are stressed, exhausted, and likely dealing with a medical condition simultaneously. They do not have legal training or US healthcare system expertise.
**Current behaviour:** Giving up. 99% of denied claims are never appealed because the process is opaque, requires reading a thirty-page policy document, and fighting an AI-mediated denial engine.
**Their words:** "I just need this covered, I don't have the energy to fight them right now."

## The Business
**Model:** Open-source hackathon project (Google Cloud Rapid Agent Hackathon — Arize partner track). No commercial monetization plan.
**Year 1 must-be-true:** Win the Arize hackathon track ($5k prize) by demonstrating a self-improving agent swarm where Phoenix MCP is structurally load-bearing.
**Biggest risk:** Agent self-improvement loop fails to produce measurable quality lift on the benchmark, or the multi-agent orchestration collapses under its own weight before the deadline.

## The Strategy
**Alternatives:** Counterforce Health (static prompt), Sheer Health (paid/freemium full service), ignoring the denial.
**Moat:** 
1. *Self-improvement from outcomes:* Aegis gets measurably better at the job over time by learning from its own Phoenix traces and evals.
2. *Consumer-grade UX:* It feels calm and dignified (like Headspace or Maven), not like a raw AI chat utility.
3. *Transparent autonomy:* It earns trust by visibly showing its work, citations, and confidence levels.
**Strategic bet:** A multi-agent swarm that demonstrably learns from its own failures will overwhelmingly beat static-prompt agents in both hackathon judging and real-world efficacy.

## Positioning & Vibe
**"Feels like" statement:** The mechanical precision and speed of Linear crossed with the empathetic, dignified calm of Headspace.
**Anti-positioning (What we are NOT):**
- We are NOT a generic ChatGPT wrapper.
- We are NOT a legal representation service (we only provide draft assistance).
- We are NOT an aggressive, polarizing "fight the system" tool (tone must remain constructive and factual).
- We are NOT building for hospitals or billing departments (strictly B2C patient focus).

## Values Hierarchy (Tradeoffs)
When faced with a decision, we trade off in this order:
1. **Safety over Autonomy:** We will always interrupt the learning loop for a safety failure. Hard gates are absolute.
2. **Polish over Scope:** We will cut the number of supported denial types or insurers before we ship a janky UI.
3. **Transparency over "Magic":** We will always show exactly which internal document a claim came from, rather than hiding it behind smooth generative text.

## Product-Market Fit
**Status:** Pre-PMF (Hackathon prototype phase).
**Signal we're watching:** Does the agent visibly improve its benchmark score on held-out cases (e.g., from ~0.40 to ~0.75)?
**PMF signal threshold:** Hackathon judges (Arize) reward the submission with a top-3 placement based on the self-improvement loop and strong UX.
**Not-PMF signal:** If disabling Phoenix MCP does not noticeably degrade the agent's output quality, the core thesis has failed.

## GTM Distribution
**First user finds us via:** Devpost hackathon gallery, GitHub trending, or Arize AI promotional channels.
**Wedge channel:** The 3-minute hackathon demo video.
**Acquisition → Activation → Retention loop:** Watch demo video (Acquisition) → Read GitHub README and clone repo (Activation) → Run the benchmark and see the self-improvement loop (Retention/Aha moment).

## Open Hypotheses (must be resolved)
- [ ] Will the Phoenix MCP integration provide enough actionable signal for the Learning Coordinator to actually improve the prompts?
- [ ] Can a solo PM build a 12-agent swarm in 20 days without the orchestration collapsing?
- [ ] Can we achieve a measurable quality lift (0.40 → 0.75) within a strict $200 LLM API budget?
- [ ] Will the 3-minute demo format provide enough time to adequately show both the polished consumer UI and the technical Phoenix backend loop?
- [ ] Can the LLM judge reliably grade "case-specificity" and "persuasive coherence" without drifting over 200 iterations?
