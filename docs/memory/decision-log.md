# Decision Log — Aegis

Append-only log of project decisions. Newest at the bottom. Each entry: date, decision, rationale, alternatives considered, status, revisit triggers.

---

## 2026-05-25 — Frontend framework: Next.js + Python ADK backend (NOT Streamlit)

**Decision.** Build the user-facing product as a Next.js (App Router) frontend backed by a Python FastAPI service that hosts the Google ADK agent. Two services on Google Cloud Run. Frontend uses Tailwind CSS + shadcn/ui (copied + customized, not imported) + framer-motion + Lucide React (custom-tuned subset + ~6–10 bespoke icons).

**Rationale.** Aegis serves a stressed, scared user (patient navigating an insurance denial). UX quality is one of three co-equal product pillars alongside (1) self-improvement loop quality and (2) visible Phoenix MCP + tracing integration — per Arize judging rubric and PM portfolio criteria. Streamlit cannot deliver consumer-grade UX, mobile responsiveness, or motion control at the level required. Pre-mortem identified Cause M (UX too dev-toolish) at impact×blindness score 25 — tied for top concern. PM 2026-05-25: "UX is a first class citizen of this product."

**Alternatives considered.**
- **(A) Streamlit + heavy theming + static landing page** — rejected. Streamlit ceiling is real; visitors who go deeper than the landing page feel the seam. Mobile experience is weak.
- **(C) Hybrid landing page (Astro) + Streamlit workflow** — rejected as safer but lower-ceiling. PM prefers higher upside.

**Status.** Accepted.

**Revisit triggers.**
- If Day 7 MVP is more than 3 days behind because frontend complexity is the bottleneck, escalate to PM with options (per `Code-Wall Escalation Protocol` to be written into AGENTS.md). Do NOT unilaterally fall back to Streamlit.
- If a third-party Next.js deployment issue on Cloud Run becomes a sustained blocker (>2 days), reopen.

**Implications.**
- Updates AGENTS.md: existing rule *"Streamlit frontend. Do not switch to Next.js / React"* must be removed in the next AGENTS.md rewrite (project-setup interview).
- Adds 3–5 build days vs Streamlit baseline. Build plan must absorb.
- Two-service Cloud Run deployment adds slight operational complexity (CORS, env propagation).

**Artifacts produced.** [docs/design-brief.md](../design-brief.md)

---

## 2026-05-25 — UX is a first-class product pillar (not supporting actor)

**Decision.** UX/Design is now formally one of three co-equal must-nail product pillars:
1. Phoenix tracing + MCP integration visibly load-bearing in the demo
2. Self-improvement loop produces a demonstrable, compelling lift
3. **UX is a calm, human, premium consumer-health product**

Any time a design choice trades polish for speed, the default is *polish*. Push schedule, not quality.

**Rationale.** Hackathon Design criterion is 1 of 4 hackathon-wide judging categories. Aegis is also serving PM's portfolio — "this will be a part of my PM portfolio and I don't want shoddy UX to be there" (PM 2026-05-25). User-trust framing: insurance denials are emotionally charged; AI-feeling copy will destroy trust on the first screen.

**Alternatives.** (A) Treat UX as supporting actor (the original AGENTS.md framing) — REJECTED by PM directive. (B) Outsource design — not feasible for solo PM in hackathon window.

**Status.** Accepted.

**Revisit triggers.** None expected — this is a fundamental product-positioning decision.

**Implications.**
- All future scope decisions weigh "does this serve UX quality?" alongside "does this serve the demo?" and "does this serve the loop?"
- Copy and tone discipline are now formalized in [docs/design-brief.md](../design-brief.md) — non-negotiable.
- Frontend framework decision (above) flows directly from this.

---

## 2026-05-25 — Tone of voice: human, plain, dignified; "person" not "human"; no AI marketing language

**Decision.** Adopt the copy rules captured in [docs/design-brief.md §4](../design-brief.md). Specifically: no "AI assistant" framing in user-facing copy; no exclamation marks; no chatbot enthusiasm; no insurance jargon without translation; use "person" instead of "human" when referring to a reader/reviewer; no guarantees about appeal outcomes.

**Rationale.** Patients in denial-appeal moments are stressed. AI-feeling copy makes them distrust the product. Consumer health products that earn trust (Headspace, Maven, One Medical) all use restrained, dignified human voice. PM directive 2026-05-25.

**Status.** Accepted.

**Revisit triggers.** None.

---

## 2026-05-25 — No unilateral scope reduction; PM-gated escalation

**Decision.** When the build hits a wall (technical, schedule, scope), the agent must **escalate to PM with options** rather than unilaterally cut scope. Specifically reverses the pre-mortem prevention B as I had initially drafted it ("Day 9 automatic emergency simplification") — PM must explicitly approve any scope reduction.

**Rationale.** PM directive 2026-05-25: "Do not enforce scope reduction without first talking to me. I am actually more worried about training this model and demonstrating that it is successful at its job." Scope choices have product-quality implications the agent should not make alone.

**Status.** Accepted.

**Revisit triggers.** None.

**Implications.** AGENTS.md must include a "Code-Wall Escalation Protocol" section in the next rewrite — capturing: every coding session ends with a working commit + "what's stuck" note; pair stuck >4h on same issue ⇒ escalate (oracle, librarian, switch tactic) — don't dig; if MVP timeline slips materially, present PM with options, don't decide.

---

## 2026-05-25 — Day 1–10 build sequence revised: 5 critical assumptions get minimum tests before pitch numbers commit

**Decision.** The PRD currently promises specific demo numbers (v1=0.31, v8=0.78, "+151%", "disable Phoenix → 0.42") with zero engineering evidence. Before committing further, the build plan is revised so the first 10 days run five minimum-cost tests on the five critical assumptions identified in [docs/research/assumption-map.md](../research/assumption-map.md):

- **Day 1–2:** Phoenix MCP + ADK integration spike (A4) AND Phoenix UI demo-viability study (A2). Both run in parallel with frontend setup.
- **Day 2–3:** Synthetic case credibility test (A3) — composite 3 cases, show to 2 outside readers.
- **Day 3–5:** Eval signal test (A1) — hand-tune v1/v2 on 3 cases, measure lift + judge stability.
- **Day 8–10:** Learning Coordinator autonomy go/no-go (A5) — run 5 iterations on Cigna med-necessity, measure hit rate.

If any of these fail, the pitch is updated downward BEFORE we commit further to that beat. Specifically:
- A4 false → demote MCP-as-load-bearing thesis; fall back to Phoenix SDK; soften demo counterfactual.
- A1 false → rebuild eval rubric (already queued per Phase 1 of original TODO).
- A3 false → re-source cases from richer public material.
- A5 false → demote Full Plan to manual-with-human-approval learning loop; update demo script.

**Rationale.** The most expensive failure mode is building all 12 agents and discovering on Day 18 that the eval signal is too noisy or the autonomous loop doesn't produce real lifts. Five disciplined tests in the first 10 days bound that risk.

**Status.** Accepted. To be reflected in the implementation plan when produced (Phase 5 TODO #17).

**Revisit triggers.** None.

**Implications.** Day 1 plan now starts with parallel work streams (frontend setup + Phoenix spike + UI study), not single-track "set up everything then build agent". Updates to PRD §14 (20-Day Build Plan) and the implementation plan when written.

---

## 2026-05-25 — Impact statistics sourced and documented

**Decision.** Aegis's Potential Impact narrative is now grounded in [docs/research/impact-stats.md](../research/impact-stats.md) — verified primary sources (KFF, CMS, Commonwealth Fund, JAMA, Health Affairs, Senate report, Stanford).

**Rationale.** Pre-mortem Cause N (Potential Impact under-articulated) was scoring 16; needed a credible factual base. Hackathon-wide Potential Impact criterion is 1 of 4. Also feeds copy/landing page hero, demo voiceover, and Devpost form.

**Status.** Accepted; the file is the source of truth — quotes from it should preserve citations.

**Revisit triggers.**
- If a KFF / Commonwealth Fund update publishes during build window with materially different numbers, update.
- If a competitor (Counterforce Health, Sheer Health) ships an obviously better positioning we should respond to, update §6 (Competitive landscape).

**Implications.**
- PRD §1 (Vision) and §2 (Problem) need updating with the impact paragraph and competitive-landscape acknowledgment. **PRD update queued — not yet done.**
- Demo script (PRD §16) should incorporate the compressed pitch line.
- Devpost submission form will draw from §7.
