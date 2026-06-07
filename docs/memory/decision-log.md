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

---

## 2026-05-27 — Eval rubric v2 (AlphaEval 2026 compliant) + PRD §8 reconciled

**Decision.** Replace the v1 rubric skeleton with v2 in [docs/evals/2026-05-27-aegis-appeal-rubric.md](../evals/2026-05-27-aegis-appeal-rubric.md). All weighted dimensions normalised to 1/3/5; **Safety (J1) and Hallucination & Internal Consistency (J2) are binary hard gates** — never weighted, never averaged in. Weighted dimensions (J3–J7) sum to 100% (Grounding 35%, Case Specificity 25%, Evidence Completeness 15%, Insurer Tactic 15%, Persuasive Coherence 10%). 7-judge panel concretely defined. Calibration anchors per dimension. Cost model: $0.014/judge call, $0.10/letter, $1.20/MVP benchmark, $300/20-day ceiling. Cohen's κ ≥ 0.6 calibration gate before any judge counts for promotion. PRD §7, §8, §15.2, §15.3 reconciled to match (hard-gate FAIL = zero-tolerance auto-rollback; promotion uses per-dimension regression thresholds, not single-composite).

**Rationale.** Session 1 PRD eval section violated AlphaEval 2026 on 6 specific principles (single composite, safety averaged, no chain-of-thought protocol, no per-step gates, etc.). Session 4 generated a skeleton but with inconsistent scales and an undefined panel. Session 5 PM gap-call flagged it. This corrects all of it.

**Status.** Accepted. Source of truth = `docs/evals/2026-05-27-aegis-appeal-rubric.md`.

**Revisit triggers.**
- If any judge fails κ ≥ 0.6 calibration on Day 5, that judge becomes advisory (not promotion-gating) until re-tuned.
- If cost model overruns 1.5× at Day 7 MVP benchmark, drop weighted-judge sampling rate on live inferences from 30% → 15%.

**Artifacts produced.** `docs/evals/2026-05-27-aegis-appeal-rubric.md` (v2), updated PRD §7 §8 §15.2 §15.3. Commits `9ee69da`, `d65e13c`.

---

## 2026-05-27 — Agent prompts rewritten as full LLM system prompts (not interface contracts)

**Decision.** All 10 v1 agent prompts in `backend/src/prompts/` are now full LLM system prompts containing: persona + objective, domain context (US health-insurance appeals, insurer-specific tactics, ERISA/ACA/MHPAEA/NSA legal frame, clinical-guideline anchors), tool-use protocol, chain-of-thought scaffold, output JSON schema, ≥1 worked few-shot example, and guardrails (no PHI, no invented citations, no "will win" language). The previous interface-contract format (ROLE/RESPONSIBILITIES/INPUT/OUTPUT/HANDOFF) is retained as the **docstring section** within each prompt — not the whole prompt.

**Rationale.** Session 4 generated prompts that were topology specs, not prompts an LLM would execute well. PM gap-call in Session 5. Drafter, Strategist, Adversarial Reviewer in particular need explicit CoT scaffolding + few-shot anchors to produce judge-passing output.

**Status.** Accepted. All 10 prompts at `backend/src/prompts/*_v1.md`. Commit `17e6c27`.

**Revisit triggers.**
- After Day 5 A1 eval-signal gate: if v1 prompts can't even hit baseline composite, the prompts are too weak — escalate.
- On every promoted version, prompts are version-bumped in Phoenix Prompts (immutable history).

---

## 2026-05-27 — Day 1–20 implementation plan produced (skill-driven, gates woven in)

**Decision.** The Day-by-Day build plan is now formalised in [`docs/plans/2026-05-27-aegis-implementation-plan.md`](../plans/2026-05-27-aegis-implementation-plan.md) + companion flat task list. 4 phases (Phase 0 setup + Phase 1 MVP + Phase 2 Swarm + Phase 3 Learning/Polish), 67 tasks, 11 risks, full PRD-ID traceability matrix. Assumption gates A1–A5 + Day 10 progress gate + Day 14/15 demo-coherence gates explicitly scheduled as hard escalation points.

**Rationale.** PRD §14 contained single-bullet days ("Day 3: Build single ADK agent with 7 tools") that were unworkable for execution. Session 5 PM gap-call. Plan now expands each day into 3–6 concrete tasks with DoD, satisfying `implementation-plan` skill output schema.

**Status.** Accepted. **Phase 0 execution (GCP + Phoenix + agents-cli setup) is gated on PM sign-off per session instruction.**

**Revisit triggers.**
- If any A1–A5 gate fails → plan re-traces accordingly (fallbacks documented inline in plan §5 + tasks gate-index).
- If Day 10 progress gate fires → ADR-004 fallback (lean topology) updates the plan from Day 11 forward.
- If a `feature-spec` is later written for a Part B agent, the plan re-traces against that spec (currently traces against PRD FR/NFR/G/SC IDs).

**Artifacts produced.** `docs/plans/2026-05-27-aegis-implementation-plan.md`, `docs/plans/2026-05-27-aegis-implementation-tasks.md`. Commit `079064d`.

---

## 2026-05-27 — Autonomy Ladder Thresholds & Mechanics

**Decision.** The 3-stage competency ladder (Apprentice → Journeyman → Master) is defined with the "Moderate Scale + Aggressive Master" configuration.
- **Apprentice:** 0-10 proposals. Every patch requires PM approval. Playbook updates only.
- **Journeyman:** Unlocks at 10 approved proposals AND composite ≥ 0.60. Fully autonomous, limited to 5/day, hard gates (lift ≥ +3%, no safety regressions). Playbook updates only.
- **Master:** Unlocks at 25 auto-promotions AND composite ≥ 0.75. Fully autonomous, 20/day, relaxed gates (lift ≥ +1%). **Broader patches permitted:** Can rewrite the Strategist agent's system prompt.

**Rationale.** Balances safety and credibility with the need to demonstrate the autonomous loop in a 100-case hackathon benchmark. Giving the Master stage the ability to rewrite core instructions rapidly (Option C) creates a compelling demo story of an AI that rewrites itself, bounded by a strict circuit breaker.

**Status.** Accepted. Design spec at `docs/specs/2026-05-27-autonomy-ladder-design.md`.

**Revisit triggers.**
- **CRITICAL:** The Master stage's aggressive privileges (Option C) carry a high risk of reward hacking / overfitting. If the system's overall composite score drops by >10% over any 10-run rolling window, the auto-demotion circuit breaker fires, instantly demoting the system to Journeyman.
- If the system is unstable in Master (repeated demotions), we will revert to Option A (keep playbook-only updates, disable system prompt rewriting).

**Artifacts produced.** `docs/specs/2026-05-27-autonomy-ladder-design.md`.

---

## 2026-05-27 — J1: agents-cli observability vs Phoenix MCP — Phoenix is primary, agents-cli observability skipped

**Decision (Updated 2026-05-27).** Use **both** Phoenix Cloud and Google Cloud Trace. Set `otel_to_cloud=True` in the ADK FastAPI app, while keeping `arize-phoenix-otel` enabled. **Phoenix remains the primary load-bearing destination** for the demo and the self-improvement loop. Cloud Trace acts purely as a durable cold-storage backup.

**Rationale.** The PM explicitly requested to keep both on as a backup in case Phoenix free-tier storage limits require aggressively deleting older traces. The minor network overhead is accepted.

**Alternatives considered.**
- **(A) Dual export (Phoenix primary + Cloud Trace secondary)** — **ACCEPTED.** Both exporters are attached.
- **(B) Cloud Trace primary, Phoenix secondary** — contradicts the demo requirement; Phoenix UI must be on-screen.
- **(C) Phoenix solely** — originally chosen, but overturned for backup safety.

**Status.** Accepted. Resolved Open-Q J1.

**Revisit triggers.**
- If `agents-cli deploy` requires Cloud Trace OTel export to work, revisit with option A.
- If Phoenix free-tier limits force a secondary sink, add Cloud Trace as fallback.


---

## 2026-05-27 — A4 Go/No-Go: Phoenix MCP latency and reliability passed

**Decision.** Proceed with Phoenix MCP as a load-bearing dependency for the Day 7 MVP and Full Plan. The test of 20 queries demonstrated 100% success rate with p50 latency of 1.24s and p95 latency of 2.52s.

**Rationale.** Assumption A4 tested if `@arizeai/phoenix-mcp` is stable and fast enough to be a critical dependency (p95 < 10s and 0 failures). The spike results were 0/20 failures and p95 of 2.52s, firmly inside the threshold. This validates the "agent learns from its own traces via MCP" architectural pattern.

**Status.** Accepted. Resolved A4 Day 2 EOD go/no-go gate.

**Revisit triggers.**
- If MCP starts taking >10s in the cloud environment once deployed, we may need to investigate network configuration or fall back to native REST SDKs.

**Artifacts produced.** `backend/spike_mcp_latency.py` (one-off test).

---

## 2026-05-27 — Synthetic-case generator: AlphaEval per-stage critics, Vertex Python pipeline (Session 10)

**Decision.** Build the synthetic case generator as a Python swarm at `backend/app/case_generator/` with 4 producers (ScenarioPlanner → DenialDrafter → ClinicalContextWriter → AdversarialDiversifier) and 19 per-stage independent critics (16 LLM + 3 deterministic). All critics follow AlphaEval rules: forced 1/3/5 anchors on weighted dims, binary PASS/FAIL hard gates that short-circuit, CoT-before-score, single-dimension scope. Critics absorb all 7 Gumloop dimensions (clinical, tone, LLM-tell, financial, legal, contradiction, demographic) plus added coverage for PHI, scope guard, date sanity, citation traceability. Configs externalised to `eval/diversity_matrix.json`, `eval/banned_topics.json`, `eval/case_schema.json`. Banned-topic full list (suicide, self-harm, child abuse, IPV, EOL, gender-affirming minors, anti-insurer violence, Medicare/Medicaid). Provenance is per-case structured (model id, run id, matrix cell, all 21 prompt versions, full critic_verdicts panel). Gumloop swarm remains the independent second-opinion evaluator — cases promote `drafts/ → approved/` only on Gumloop `APPROVE`. No Phoenix tracing for the generator (offline tool).

**Rationale.** PM correctly pushed back on my initial proposal of one critic-in-loop at the end — that was the AlphaEval mega-prompt anti-pattern. Per-stage independent critics catch issues at the artifact that produced them and prevent dimension bleed. PM said "operate as if Gumloop/ChatGPT/Perplexity curators do not exist" → swarm must be self-sufficient → absorbed Gumloop's 7 dimensions and added 4 gap-coverage critics. Weighted random sampling (PM choice) over force-cover for the diversity matrix. Full structured provenance for auditability.

**Alternatives considered.**
- One-shot drafter with no in-loop critic, relying on Gumloop only — rejected; downstream discards would be wasteful.
- One critic-in-loop at the end (initial proposal) — rejected as AlphaEval mega-prompt anti-pattern.
- Gumloop-only flow with no code — rejected; PM picked ADK swarm in Python for autonomy + reuse of Vertex/Gemini infra.

**Known weakness.** Drafter and critic are both `gemini-3.1-pro-preview` at session-close time, differentiated only by temperature. AlphaEval and backend AGENTS.md prefer different model families. Mitigation plan filed at `docs/plans/2026-05-28-case-generator-harness-claude-plan.md` — wire Claude (Opus or Sonnet) on Vertex AI Model Garden as the critic backend next session.

**Status.** Accepted. Working pipeline. First successful case at `eval/cases/drafts/part-a/test/case_01_aetna_priorauth.json`.

**Revisit triggers.**
- After G1 from the next-session plan is shipped (Claude critic on Vertex), update this decision with the new architecture.
- If discard rate > 25%, tighten ScenarioPlanner prompt or relax overly-strict critics.
- If new insurers / denial types are added to MVP scope, extend `eval/diversity_matrix.json`.

**Artifacts produced.**
- `backend/app/case_generator/{__init__,config,models,safety,validator,agents,pipeline,cli}.py`
- `backend/app/case_generator/prompts/*.txt` (21 templates + envelope)
- `eval/{diversity_matrix,banned_topics,case_schema}.json`
- `eval/cases/drafts/part-a/test/case_01_aetna_priorauth.json` (smoke test output)
- `docs/plans/2026-05-28-case-generator-harness-claude-plan.md` (next-session plan)
- Updated: `eval/dataset_card.md`, `backend/pyproject.toml` (jsonschema dep)

---

## 2026-05-28 — Separate Realism and Appeal Difficulty + Analysis-First Evaluators (Session 13)

**Decision.** The generation pipeline and Gumloop swarm will explicitly inject "authentic shoddiness" to mimic real-world insurer flaws (using `eval/denial_patterns.json`). The evaluators are split into separate `Realism` and `Appeal Difficulty` dimensions. The `Appeal Difficulty` score will be hidden from Phoenix traces and the appeal agent. Furthermore, all evaluators (both generator-side and Gumloop-side) are refactored to follow an `Analysis-First` structure (critical evaluation must be written *before* the score is given) to prevent anchoring bias.

**Rationale.** A core thesis of Aegis is that real-world insurance denials are shoddy and illogical. "Foolproof" synthetic denials are unrealistic. The generator must mimic these real flaws. To properly score them, evaluators must separate realism (does it look like a real shoddy letter?) from difficulty (how hard is it to appeal?). Hiding the difficulty score prevents the appealing agent from cheating. The analysis-first rule enforces AlphaEval compliance for LLM-as-a-judge.

**Status.** Accepted. Implemented in Gumloop prompts and `gumloop/architecture.md`.

**Revisit triggers.**
- If generation yields too many cases that are realistic but unsalvageable, adjust the severity of the flaw injector.
- If the case difficulty distribution (Easy/Medium/Hard) skews too heavily in one direction.

**Artifacts produced.**
- `eval/denial_patterns.json`
- `gumloop/architecture.md` (rewritten)
- `gumloop/prompts/*`
- `backend/app/case_generator/prompts/*`

---

## 2026-05-28 — SkillOpt Alignment & Anti-Cheating Firewall (Session 13)

**Decision.** Formalise the Learning Coordinator as an implementation of "SkillOpt-style Textual Gradient Descent" (optimising prompt/playbook text rather than model weights). Enforce a strict "Anti-Cheating Firewall" where the Appeal Agent (Student) and Learning Coordinator (Learner) are strictly blind to the benchmark ground truth (`eval/` files, `intended_flaw_types`, `appeal_difficulty`). Only the Quality Judge Panel and Outcome Simulator (Teachers) receive the full `synthetic_provenance` answer key to grade the exam.

**Rationale.** Aligning with Microsoft Research's SkillOpt framework validates our core architectural thesis (trace-based reflection + shadow-tested bounded edits on frozen models). The Anti-Cheating Firewall is mandatory to ensure the system is genuinely learning to appeal flawed cases rather than just memorising the answer key during eval runs. A judge needs the answer key to grade; a student must not have it to take the test.

**Status.** Accepted. Architecture and PRD updated to reflect the firewall.

**Revisit triggers.**
- If instrumentation inadvertently leaks `synthetic_provenance` onto the trace payload passed to the Orchestrator, break the build until plugged.

**Artifacts produced.**
- Updated `docs/architecture/2026-05-27-aegis-arch.md`
- Updated `docs/prd/PRD.md`

---

## 2026-05-28 — Multi-Service Backend Topology & GCP Generation Job

**Decision.** Run the offline case generator as a headless Cloud Run Job (or local script) to leverage Google Cloud ADC, bypassing the need for raw API keys for Vertex Gemini and Vertex Claude. Keep a single Python backend repository but launch it as two isolated logical services: `aegis-v1-api` (Port 8001, Phoenix project `aegis-baseline`) and `aegis-swarm-api` (Port 8002, Phoenix project `aegis-swarm`). 

**Rationale.** Using ADC for offline generation solves the API key constraint natively. Splitting the runtime into two logical services enforces physical separation between the safety-net MVP (v1) and the complex Full Plan (swarm). Crucially, this split allows emitting traces to completely isolated Phoenix projects, creating a clean "Before vs After" narrative for the 3-minute hackathon demo without needing manual trace filtering.

**Status.** Accepted.

**Revisit triggers.** 
- If managing 3 dev processes locally (frontend + v1 + swarm) causes significant resource strain on the PM's machine, revert to sequential testing or consolidate for local dev while deploying separately.

**Artifacts produced.** `docs/adr/ADR-006-multi-service-backend-topology.md`.

---

## 2026-06-06 — Reversible decision: v1 drafter sees sanitized Phoenix trace summaries in all drafting phases

**Decision.** Keep sanitized Phoenix memory visible to the v1 drafter in normal/live drafting, clean measurement drafting, and optimizer candidate drafting. Phoenix remains load-bearing both as runtime memory and as the learner's trace/annotation store.

**Rationale.** PM preference after discussion: the drafter may benefit from sanitized prior-trace patterns during the live demo, while the learner still uses Phoenix traces and judge annotations to propose prompt/playbook changes. This makes Phoenix visibly useful in the draft itself and in the learning loop.

**Boundaries.**
- Drafter may see only sanitized Phoenix summaries (`failure_patterns`, `success_traits`, risk flags).
- Drafter and learner must still never see raw answer-key fields such as injected flaws, `synthetic_provenance`, or exploitable weaknesses.
- Judges may see the curated teacher packet, including injected flaws, denial patterns, and relevant denial-letter references.

**Status.** Accepted as a reversible demo decision.

**Revisit triggers.**
- If judges or PM decide Phoenix runtime hints blur the "learned prompt/playbook improvement" story, flip normal/measurement drafting back to Phoenix-off while preserving learner access to Phoenix traces.
- If any firewall test shows teacher-only metadata reaching drafter or learner inputs, revert immediately and repair before demo.

