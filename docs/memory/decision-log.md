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

## 2026-05-27 — Adopt `google-agents-cli` for backend dev workflow

**Decision.** Install `uvx google-agents-cli setup` on Day 1 of build. Use its `create` / `playground` / `eval` / `deploy` commands and its bundled 7 skills for the full ADK lifecycle (scaffold → develop → evaluate → deploy → observe). Keep ADK as the agent framework — agents-cli is the lifecycle tool around ADK, not a replacement.

**Rationale.** `google-agents-cli` was released April 2026 by Google as the unified ADK development backbone. It compresses Day 1 setup, ships skills that fill gaps our library doesn't cover (ADK Python API, project scaffolding, eval harnesses, Cloud Run deployment, observability), and is officially built on top of ADK. For a non-technical PM working in a 20-day window, the leverage is real.

**Alternatives considered.**
- Skill-only install (`npx skills add google/agents-cli`) — less leverage, doesn't get the CLI commands.
- Defer to Day 1 review — rejected; Day 1 time is already precious per the assumption-map test plan.
- Don't adopt; build scaffolding/deploy manually — rejected; reinvents wheels.

**Status.** Accepted.

**Revisit triggers.**
- If `google-agents-cli-observability` skill conflicts with our Phoenix MCP instrumentation, fall back to manual workflow for observability — keep Phoenix as primary.
- If their Cloud Trace dependency complicates the Phoenix setup, isolate it (skip the observability skill).
- If their `deploy` skill assumes Agent Runtime patterns that conflict with our 2-service Cloud Run topology, drop the deploy skill and write a custom deploy script.

**Implications.**
- Update tech stack: AGENTS.md + backend/AGENTS.md now reference `google-agents-cli`.
- Orchestration map gains a new "Backend lifecycle (ADK)" row listing the 7 agents-cli skills.
- Skill routing rule added in AGENTS.md: ADK-specific work → `google-agents-cli-*` skills; framework-agnostic process work → existing skill library.
- Open question added to [docs/open-questions.md](../open-questions.md) on Phoenix MCP + agents-cli observability compatibility (must resolve Day 1).

**Sources.**
- [agents-cli getting started](https://google.github.io/agents-cli/guide/getting-started/)
- [Google announcement, Apr 2026](https://developers.googleblog.com/agents-cli-in-agent-platform-create-to-production-in-one-cli/)
- [agents-cli GitHub](https://github.com/google/agents-cli)

---

## 2026-05-27 — Part B architecture stays at 12 agents (NOT compressed to lean composite)

**Decision.** Part B architecture remains as specified in PRD §12 — 12-agent swarm + Learning Coordinator + Pattern Synthesizer. Do not compress to the lean 5-runtime + 1-offline composite that was sketched in this session.

**Rationale.** PM judgment: the audacious-bet framing is the strategic point of Part B. Agent count is part of the differentiation thesis vs every other Arize submission. The risk is accepted explicitly.

**Alternatives considered.**
- **Lean composite (5 runtime + 1 offline):** the architecture critique surfaced in this session against Google's [official 8-pattern multi-agent guide](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/) showed several rough edges in the 12-agent design: (1) the "12" count includes evals miscounted as agents (Quality Judge Panel is 7 LLM judges, not 1 agent; Outcome Simulator is a rule engine + 1 LLM call); (2) the 5-agent researcher pool is over-decomposed — they all do "retrieve grounding evidence from corpus X", which is a tool concern, not an agent concern; (3) <1 day per agent for a non-technical PM in Days 8–14 is unrealistic for prompt quality; (4) the demo can only credibly show 3–4 agents in 3 minutes so the cost of 12 doesn't pay off in pitch; (5) the Arize rubric rewards loop quality, not agent count. **REJECTED by PM** — the audacity is the bet.
- **Defer count entirely until `agent-system-architecture` runs:** REJECTED — PM wants the 12-agent framing committed.

**Status.** Accepted with hard revisit triggers.

**Revisit triggers (CRITICAL — these are the safety nets on the audacious bet).**
- **Day 10 progress gate:** if <50% of the 9 specialist agents (beyond the single MVP agent) have credible role prompts and pass basic integration tests by EOD Day 10, escalate to PM with options (compress to lean composite, ship 5 agents instead of 12).
- **Assumption A5 fails:** if Learning Coordinator's autonomous loop fails its Day 10 go/no-go (hit rate < 1-in-10 OR > 30% absurd-edit rate), the 12-agent thesis is hollow — reopen architecture entirely.
- **Demo coherence test:** by Day 15, if the demo can't credibly walk through ≥3 specialist agents on screen without overwhelming viewers, compress the demo-visible subset to 3–4 of the 12. Keep all 12 in repo, demo 5.
- **Build-time slippage:** if Day 14 milestone (9-agent swarm shippable) slips by >2 days, escalate per Code-Wall Escalation Protocol — do NOT silently downscope.

**Implications.**
- PRD §12, §14 build plan, §16 demo script stay as currently specified.
- AGENTS.md → "Build Discipline" includes the Part B revisit triggers explicitly.
- Before Day 8 starts, run `agent-system-architecture` skill on the 12-agent topology to formalize roles + interfaces, and `create-agent-prompt` for each of the 12 roles. This is *Phase 4* in the original Session 1 TODO and remains a hard prerequisite for Day 8 work.

**Sources.**
- PRD §12 — current 12-agent topology
- [Google's developer guide to multi-agent patterns in ADK, Dec 2025](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/)
- Pre-mortem (Cause M — UX feels dev-toolish) and Assumption Map (R6 — 12 agents looks like overkill to judges) both flagged this risk; both stand as "monitor + revisit".

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
