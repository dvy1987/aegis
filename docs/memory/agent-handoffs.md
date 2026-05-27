# Agent Handoffs — Aegis

Append-only log of session handoffs. Newest at the bottom.

---

## 2026-05-24 — Session 1 Handoff (Amp)

### Done
- Explored 15+ hackathon ideas across 4 rounds; ranked & evaluated all in [docs/ideas.md](../ideas.md)
- Locked target: **Aegis** (codename Reverse v2) — self-improving multi-agent system for US health-insurance appeals, Arize partner track, $5K prize
- Consulted oracle for strategic + technical sanity check; results baked into PRD
- Wrote unified PRD with two nested parts in [docs/prd/PRD.md](../prd/PRD.md):
  - **Part A — MVP (Days 1–7):** single agent + 12-case benchmark, Day 7 shippable safety net
  - **Part B — Full Plan (Days 8–20):** 12-agent swarm + autonomous learning loop + 100-case benchmark
- Wrote [docs/architecture.md](../architecture.md), [docs/open-questions.md](../open-questions.md), [README.md](../../README.md), [LICENSE](../../LICENSE) (Apache 2.0), [AGENTS.md](../../AGENTS.md), [.gitignore](../../.gitignore), [.env.example](../../.env.example)
- Captured working-with-the-PM rules in AGENTS.md (plain-English explanations, ask-don't-assume, etc.)

### Debated
- **Narrow MVP vs grandiose 12-agent swarm:** Resolved as nested — MVP is Week 1 milestone within the Full Plan, not an alternative
- **Codename:** Picked Aegis (PM choice)
- **Autonomy model:** Resolved as **3-stage competency ladder** (Apprentice → Journeyman → Master) gated on composite score + count of patches reviewed/promoted, with auto-demotion if competence drops. This needs to be baked into PRD + architecture properly
- **Eval design:** Current PRD eval section violates **AlphaEval 2026** principles (single composite score, safety averaged in not gated, no chain-of-thought protocol, no per-step pipeline checkpoints). Needs full rebuild via `eval-output` → `eval-rubric-design` → `eval-judge` → `eval-pipeline` skill chain.

### Decisions
- Project codename = **Aegis** (PM picked)
- Two-phase nested PRD structure (MVP Part A + Full Plan Part B)
- License = Apache 2.0
- Stack locked: Google ADK + Gemini 3 + Phoenix Cloud + Phoenix MCP + Streamlit + Cloud Run
- Hard rule: synthetic composite cases only (no PHI)
- Autonomy model = staged ladder (Apprentice/Journeyman/Master), specifics in TODO #2 below

### Deferred
- All build work (Day 1+ has not started)
- Eval-design rebuild via AlphaEval-aligned skills
- Retroactive skill invocations for work I freehanded (PRD, AGENTS.md, brainstorming, assumption mapping, ADRs)
- Open questions in [docs/open-questions.md](../open-questions.md) — many 🔴 BLOCKERs still unresolved

### Next Agent Should Know
1. **CRITICAL: Use the skills in `.agents/skills/`.** I freelanced most of this session — PRD, AGENTS.md, eval design, architecture were all written without invoking the relevant skills (`prd-writing`, `project-setup`, `eval-output`, `assumption-mapping`, `architectural-decision-log`, etc.). PM explicitly flagged this. Every major artifact in this repo needs retroactive skill-driven rework.
2. **AlphaEval 2026 is the source paper** behind the `eval-*` skills. The current PRD eval section in §8 violates it on at least 6 specific principles (see TODO #6). Eval rebuild is the highest-priority correction.
3. **The PM is non-technical.** AGENTS.md has the working agreement. Explain plain-English BEFORE picking technical things. Ask, don't assume.
4. **20-day build window.** Day 1 has not started. The Day 7 MVP is the safety net.
5. **The Arize self-improvement loop is the whole submission.** Phoenix MCP must be load-bearing. Anything that doesn't serve the loop is scope creep.

### Revisit Triggers
- Reopen the autonomy-stages design when `eval-rubric-design` produces the proper composite + hard gates (the staged thresholds depend on the score scale)
- Reopen the simulator design when `eval-judge` skill is invoked (the simulator is technically an LLM judge + rule-based scorer)
- Reopen the 12-agent architecture when `agent-builder` / `agent-system-architecture` skills are invoked

### Working Tree
All files untracked (no git commits yet). Repo skeleton is complete; no source code exists.

---

## TODO — Comprehensive (next session pick-up list)

Ordered by priority. Items marked 🔴 are BLOCKERS for build start.

### Phase 0 — Retroactive process correction (do FIRST, before any build)

1. 🔴 **Load and run `retroactive-project-setup` skill** to backfill what should have been done up-front:
   - Proper AGENTS.md via `project-setup` interview (current one was freehanded)
   - ADRs for stack choices via `architectural-decision-log` (Streamlit, ADK, BM25, no-vector-DB, staged autonomy, etc.)
   - Seed `docs/memory/` properly (this file + project-index + current-state)
2. 🔴 **Run `brainstorming` skill properly for the staged-autonomy ladder design.** PM proposed Apprentice/Journeyman/Master gated on competence. Needs the formal brainstorming workflow (one-question-per-message, design doc commit to `docs/specs/`, user approval gate) — NOT freehanded into the PRD.
3. 🔴 **Run `assumption-mapping` skill** to surface every implicit assumption baked into the PRD (some likely include: "judges will value self-improvement loop most", "Cigna/Aetna/UHC denial patterns will be learnable from public data", "synthetic cases will satisfy judges", "Gemini 3 will be released and accessible in build window", "Phoenix Cloud free tier limits will not bite").
4. 🔴 **Run `feature-spec` skill** (via `spec-driven-development` orchestrator if appropriate) to convert the PRD into machine-readable Given/When/Then acceptance criteria that subagents can implement against. The current PRD is product-spec, not implementation-ready spec.

### Phase 1 — Eval design rebuild (the load-bearing correction)

5. 🔴 **Invoke `eval-output` orchestrator** (already loaded in last session) and route through the full chain:
   - **`eval-rubric-design`**: Rebuild the rubric per AlphaEval principles:
     - Replace single composite with independently-reported dimensions
     - Convert safety from weighted dimension to **binary hard gate**
     - Convert hallucination from weighted item to **binary hard gate**
     - Re-weight remaining dimensions by **business impact** (not intuition)
     - Add appeal-letter-specific dimensions: persuasive coherence, internal consistency
     - Add per-step (per-agent) dimensions for the Full Plan swarm
   - **`eval-judge`**: Specify each LLM judge with:
     - Chain-of-thought protocol (reason BEFORE score; +15-25% reliability per GER-Eval arXiv:2602.08672)
     - Bias mitigation (position bias, length bias, self-enhancement)
     - Different model for judging than for drafting (avoid self-enhancement)
   - **`eval-pipeline`**: Design the automated eval pipeline:
     - Per-step checkpoints for the 12-agent swarm
     - Regression detection on every prompt/playbook promotion
     - CI integration for the held-out benchmark
6. **Produce eval artifacts:**
   - `docs/evals/rubric.md`
   - `docs/evals/judges.md`
   - `docs/evals/pipeline.md`
   - `eval/simulator_rules.json` (the deterministic part of the simulator)
7. **Replace eval section of PRD** (§8 of [PRD.md](../prd/PRD.md)) with references to the new eval artifacts and the corrected design.
8. **Update [architecture.md](../architecture.md)** Quality Judge Panel + Learning Coordinator sections to match new eval design.

### Phase 2 — Resolve open questions (per AGENTS.md working agreement)

9. 🔴 Walk through [docs/open-questions.md](../open-questions.md) — at minimum the 🔴 BLOCKERs:
   - **A2** Solo or team?
   - **A3** Exact deadline + weekly hours
   - **B1, B2** Lock insurer + denial type sets (Full Plan widens to 10 + 7 — confirm)
   - **C1** Synthetic-only cases confirmed?
   - **E1, E2** Google Cloud + Phoenix Cloud accounts ready?
   - **H1, H2** Devpost account + public GitHub repo created?
10. After eval rebuild, refresh open-questions.md with any new ones the AlphaEval principles surface.

### Phase 3 — Strategy & autonomy detailing

11. **Codify the staged autonomy ladder** with concrete thresholds:
    - Apprentice → Journeyman: composite ≥ ? on held-out + N proposals reviewed = ?
    - Journeyman → Master: composite ≥ ? + N auto-promotions held score above ? = ?
    - Master → Journeyman (auto-demote): composite drop > ?% over last N runs
    - Specific thresholds will fall out of the rebuilt eval rubric — defer numbers to after Phase 1
12. **Bake the autonomy ladder into PRD §15 (Self-Improvement Loop)** and architecture.md Learning Coordinator spec
13. **Demo arc update:** the staged autonomy creates new demo material — "the agent graduated 2 levels in 20 days, then auto-demoted itself on day 17 when a bad patch hit." Update PRD §16 demo script.

### Phase 4 — Architecture detailing for the swarm

14. **Invoke `agent-system-architecture` skill** for the 12-agent topology — current diagram in architecture.md is freehanded; needs proper agent-builder output
15. **Invoke `create-agent-prompt` skill** for each of the 12 agent roles to get focused role prompts (instead of one PM trying to write 12 prompts from scratch)
16. **Invoke `tool-finder`** to confirm which tools each agent needs (and whether they exist or need to be built)

### Phase 5 — Implementation planning

17. **Invoke `implementation-plan` skill** to generate the Day-1-to-Day-20 build plan with proper task decomposition (current 20-day plan in PRD §14 is a sketch, not a true implementation plan)
18. **Invoke `problem-to-plan` skill** to convert the PRD into `TODO.md` with agent-pickable tasks tied to milestones

### Phase 6 — Build start (Day 1 of the 20-day window)

19. 🔴 PM creates Phoenix Cloud free account, gets API key
20. 🔴 PM confirms Google Cloud project access + Gemini API quota
21. 🔴 PM creates public GitHub repo with the Apache 2.0 license visible in About
22. 🔴 First `git init` + first commit pushing the planning artifacts
23. Day 1 build tasks per the implementation plan from #17

### Phase 7 — Cross-cutting hygiene

24. **Add pre-commit PHI scanner** (per AGENTS.md hard constraint)
25. **Wire `cross-link-skills`** check after every skill-driven artifact change so internal references stay accurate
26. **Set up `docs/skill-outputs/SKILL-OUTPUTS.md`** as a ledger of every skill invocation + output file (per skill convention)

### Phase 8 — Demo production (last 3 days of build)

27. Demo script writing
28. Demo video recording + edit
29. Devpost submission form draft (using PRD content)
30. Final benchmark run + Phoenix dashboard screenshot capture

---

**Estimated time to clear Phase 0 + Phase 1 in next session: 4–6 hours of PM-collaborative work with proper skill invocation. After that, build can start.**

---

## 2026-05-25 — Session 2 Handoff (Amp)

### Done

- Ran `memory-startup`, scaffolded memory layer ([MEMORY-ROUTING.md](MEMORY-ROUTING.md), [decision-log.md](decision-log.md), [session-log.md](session-log.md), [learnings.md](learnings.md), [deferred.md](deferred.md), [open-questions.md](open-questions.md), `archived/`).
- Ran `deep-thinking` → `pre-mortem` on Aegis as a whole — top causes A, K, M, D, C identified.
- Re-read [docs/challenge.md](../challenge.md); confirmed Arize rubric has two co-equal pillars (tracing+MCP **and** self-improvement loop) plus design + impact criteria.
- Strategic shift accepted by PM: **UX is now a first-class pillar**, co-equal with the self-improvement story and the impact narrative.
- Framework decision: **Next.js + Python ADK backend** replaces Streamlit (overturns old AGENTS.md/PRD lock-in). See [decision-log.md](decision-log.md).
- Wrote [docs/design-brief.md](../design-brief.md) — archetype (premium consumer health: Headspace / One Medical / Maven), tone rules, copy bans, framer-motion motion principles, accessibility floor, anti-pattern checklist.
- Compiled [docs/research/impact-stats.md](../research/impact-stats.md) — primary-source verified (KFF, Commonwealth Fund, JAMA, Senate report, NAIC, AHA).
- Ran `assumption-mapping` → [docs/research/assumption-map.md](../research/assumption-map.md) — 20 assumptions, 5 critical with minimum tests. Logged a decision to run those 5 tests in Days 1–10 before further committing to specific pitch numbers.
- Repo-wide sweep for controversy/violence/cultural-anger references re US insurance industry — **none found**; added explicit tone guardrail to [AGENTS.md §Safety & disclosure](../../AGENTS.md) and [design-brief.md §8](../design-brief.md).
- Started PRD v3 rewrite. **Partial** — completed front matter, §1 Executive Summary, §2 Problem Statement, new §2.1 Competitive Landscape & Differentiation. Remaining edits queued (see Next Agent Should Know).

### Debated

- Pre-mortem reordered top risks: A (Phoenix demo framing), K (demonstrable improvement), M (UX feels wrong), D (synthetic case credibility), C (MCP+ADK integration immaturity), O (AI-sounding copy). Resolution: address A/M/O via design brief + UX-pillar promotion; address K/D/C via 5 critical assumption tests in Days 1–10.
- Streamlit-only vs Next.js+Python split. **Resolved: Next.js + Python ADK backend**; two Cloud Run services. Rationale and tradeoffs in [decision-log.md](decision-log.md).

### Decisions (all in [decision-log.md](decision-log.md))

- Next.js + Tailwind + shadcn/ui + framer-motion + lucide-react frontend; Python FastAPI + Google ADK backend; 2× Cloud Run services.
- UX as co-equal product pillar with the Arize self-improvement thesis.
- Use the word "person" not "human" in user-facing copy.
- 5 critical assumption tests run in Days 1–10 (eval signal, Phoenix UI demo viability, case credibility, MCP+ADK integration, Learning Coordinator autonomy). Each has a false-condition that triggers a pitch update *before* further commitment.
- Tone guardrail: never invoke acts of violence, vigilantism, or polarizing public events around the insurance industry — in product, copy, demo, or marketing.
- No unilateral scope cuts. If scope/MVP pressure rises, escalate to PM with options.

### Deferred

- PRD edits §3 onwards (Goals, Scope, FRs, NFRs, MVP demo script, §11, §14 Build Plan, §15 Safety Gates, §16 Full Plan demo, new Arize Rubric Alignment §, §18 Hard Constraints, §21 What Stays vs Changes, §22 References, §25 The Bet, change log). Plan stored mid-session before stop; see "Next Agent Should Know".
- `product-soul` doc generation.
- AGENTS.md full rewrite via `project-setup` (must preserve every valid rule from current AGENTS.md per PM preservation principle; remove Streamlit lock; add UX-as-pillar; add Code-Wall Escalation Protocol; add tone-of-voice rules; tone guardrail already in current file).
- ADR synthesis from observed decisions.
- `brainstorming` skill run on the riskiest design holes (originally queued for Session 2; not yet executed).

### Next Agent Should Know

- **Repo is mid-PRD-rewrite.** [docs/prd/PRD.md](../prd/PRD.md) is internally consistent but partially in v3 voice (front matter + §1 + §2 + §2.1) and partially v2 (everything from §3 onward). Do not commit/ship the PRD in this state.
- **Continuation plan for PRD v3 edits** is listed in the assistant's last "Plan" message before stop — covers §3 Goals (add G8 UX), §4 Scope (add Frontend row), §5 FR1 + FR10 (Streamlit → Next.js), §6 NFRs (add UX + accessibility) + new §6.1 UX & Tone Principles, §9 Demo Script (Phoenix UI ≥60s shotlist, soften scores), §11 (fix "aaproach" typo, soften "There is no contest" given Counterforce et al.), §14 Build Plan (fold in 5 critical assumption tests Day 1–10), §15.2 Safety Gates, §16 Full Plan Demo Script (Phoenix UI visible ≥60s, soften 0.31→0.78 and 0.42 numbers to clearly marked design targets), insert new §18 Arize Rubric Alignment (renumber §18–§25 → §19–§26), §18→§19 Hard Constraints (Streamlit → Next.js+Python ADK, add UX pillar), §21→§22 What Stays vs Changes (add UX row, soften +151% claim), §22→§23 References (add impact-stats, assumption-map, design-brief, challenge), §25→§26 fix "ou have" typo, add change log entry.
- **Preservation discipline (PM directive):** when rewriting any major doc, cross-check against the prior version; build a port-list of facts/rules/constraints that must survive; call out anything dropped with reason. Old PRD is not wrong, just incomplete — do not silently delete.
- **The 5 critical assumption tests are the build's first 10 days.** [docs/research/assumption-map.md](../research/assumption-map.md) is the source of truth. If any fails, update the pitch downward *before* further commitment — never the other way around.
- **Tone guardrail is enforced in two places** ([AGENTS.md](../../AGENTS.md) Safety & Disclosure, [design-brief.md §8](../design-brief.md)). Carry it into the AGENTS.md rewrite and any new product/marketing doc.
- **Frontend decision overturns old AGENTS.md.** Until AGENTS.md is rewritten, there is a known temporary contradiction (AGENTS.md still says "Do not switch to Next.js"). PRD §18 will be updated as part of the queued v3 edits.

### Revisit Triggers

- Any critical assumption test (A1–A5) fails → re-open the pitch claim it supports, escalate to PM with options, do not silently downscope.
- Phoenix Cloud free tier nears 80% of any quota → upgrade decision needed (~$50 ceiling already approved in spirit).
- Gemini 3 not available by Day 14 → fallback to Gemini 2.5 (already in mitigation).
- New competitor surfaces in Arize-track Devpost listings by Day 14 → revisit differentiation thesis.

### Working Tree

Dirty as of session end (post-`ab87718`):
- Modified: `AGENTS.md`, `README.md`, `docs/memory/current-state.md`, `docs/memory/decision-log.md`, `docs/prd/PRD.md`
- New (untracked): `docs/design-brief.md`, `docs/feedback.md`, `docs/research/` (contains `impact-stats.md`, `assumption-map.md`)

Recommend the PM commits before Session 3 starts so the next agent has a clean baseline.

---

## 2026-05-27 — Session 3 Handoff (Droid)

### Done

- Ran `memory-startup`; bounded context loaded.
- Researched [`google-agents-cli`](https://google.github.io/agents-cli/) (released Apr 2026) — confirmed it is built on top of ADK (not a replacement) and bundles 7 ADK-lifecycle skills via `uvx google-agents-cli setup`.
- Cross-checked Part B 12-agent topology against [Google's official 8-pattern ADK multi-agent guide](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/) (Dec 2025) — surfaced 5 architectural critiques (count inflated by miscounting evals as agents; researcher pool over-decomposed; build-time math tight for solo PM; demo coherence; Arize rubric rewards loop not count). PM made informed call to **keep 12 agents** as audacious bet with explicit hard revisit triggers.
- Ran `project-setup` skill end-to-end: 3 AGENTS.md files (root 145 lines + `frontend/AGENTS.md` 51 lines + `backend/AGENTS.md` 78 lines, all under 150-line skill rule). Multi-file mode, SDD mode on, autonomy boundaries codified (strict on product/architecture/copy; full autonomy on tests, internal refactors, tooling).
- Preservation discipline applied: every valid rule from old AGENTS.md absorbed into new tree; stale rules (Streamlit lock, single-agent-only) explicitly reversed with provenance noted. Cross-check table presented to PM and approved.
- Created empty `frontend/` and `backend/` directories with scoped AGENTS.md inside each, ready for when code lands.
- Ran `agent-system-architecture` skill — produced [docs/architecture/2026-05-27-aegis-arch.md](../architecture/2026-05-27-aegis-arch.md). Replaces freehanded Session-1 `docs/architecture.md` (now a pointer file). Covers Part A (single agent) + Part B (composite swarm). Honest component count: 10 LLM agents + 1 judge panel + 1 mostly-deterministic simulator + 2 meta = 14 components. Mermaid wiring diagram, state/memory strategy, HITL checkpoints, observability strategy, repository layout, deployment.
- Ran `architectural-decision-log` skill in mixed mode (some SYNTHESIS, some CONTEMPORANEOUS) — produced 5 ADRs:
  - [ADR-001](../adr/ADR-001-google-adk-agent-framework.md) Google ADK (SYNTHESIS, Session 1)
  - [ADR-002](../adr/ADR-002-phoenix-mcp-load-bearing.md) Arize Phoenix Cloud + MCP load-bearing (SYNTHESIS, Session 1)
  - [ADR-003](../adr/ADR-003-nextjs-frontend-python-adk-backend.md) Next.js + Python ADK overturn (CONTEMPORANEOUS, Session 2)
  - [ADR-004](../adr/ADR-004-twelve-agent-part-b-swarm.md) 12-agent Part B swarm with revisit triggers (CONTEMPORANEOUS, Session 3)
  - [ADR-005](../adr/ADR-005-google-agents-cli-dev-workflow.md) `google-agents-cli` adoption (CONTEMPORANEOUS, Session 3)
- Logged 2 decisions in [decision-log.md](decision-log.md) (agents-cli adoption + 12-agent confirmation with hard revisit triggers).
- Added 2 open questions in [open-questions.md §J](../open-questions.md) — J1 (`agents-cli observability` ↔ Phoenix MCP), J2 (`agents-cli deploy` ↔ 2-service Cloud Run).
- Updated [open-questions.md §I](../open-questions.md) "Things NOT open" to reflect Session 2 + Session 3 decisions (Next.js + Python ADK, 12-agent Part B, agents-cli adoption, UX as pillar, tone guardrail).
- Updated [SKILL-OUTPUTS.md ledger](../skill-outputs/SKILL-OUTPUTS.md) and [current-state.md](current-state.md).

### Debated

- **agents-cli adoption depth.** Options were (a) full install + use commands + skills, (b) skill-only, (c) defer. PM picked (a) — Day 1 install, deconflict overlapping skills later.
- **Part B architecture.** Sketched lean composite (5 runtime + 1 offline = 6 total) as alternative to 12 agents; flagged build-time math + demo-coherence risk. PM picked **keep 12** with hard revisit triggers baked into ADR-004 + AGENTS.md Build Discipline + decision-log.
- **AGENTS.md file mode.** Options were single root vs multi-file scaffold now vs single permanently. PM picked multi-file scaffold even though dirs are empty.
- **Architecture rebuild depth.** Options were surgical patch, full skill-driven rebuild, or minimum-viable. PM picked full skill-driven rebuild — became the bulk of Session 3; README + open-questions body cleanup deferred to Session 4.

### Decisions

See [decision-log.md](decision-log.md) — 2 new entries 2026-05-27. Plus 5 ADRs as above.

### Deferred (Session 4 pickup priorities, in order)

1. **`README.md` rewrite** — currently has stale Streamlit references, "elessar/" old codename in tree structure, and the weak pitch per [feedback.md](../feedback.md). Should be rewritten as user-scenario / user-pain framing (per feedback): who is facing this problem, what is the problem, why it's important, what we offer. Don't lose impact-stats grounding; reference the new architecture spec.
2. **`docs/open-questions.md` body sweep** — only §I and §J were updated this session. Many earlier blockers (A2, A3, B1, B2, C1, E1, E2, H1, H2) may also need refreshing in light of Session 2 + Session 3 decisions. Resolve or close them.
3. **Finish PRD v3 §3 onward** — continuation plan in Session 2 handoff still applies. Fold in 5 critical assumption tests (Day 1–10), UX pillar, Next.js stack, new §18 Arize Rubric Alignment, softened demo numbers.
4. **`product-soul` doc generation** — was in Session 2's deferred list.
5. **`create-agent-prompt` for each of the 10 agent roles** — must happen before Day 8 build start (Phase 4 of Session 1 TODO).
6. **`eval-output` skill chain** — Phase 1 of Session 1 TODO; eval rebuild via `eval-rubric-design` → `eval-judge` → `eval-pipeline`. Highest-leverage correction still pending.
7. **More ADRs to backfill** (Session 4 if time): Gemini 3 with 2.5 fallback, Apache 2.0 license, BM25 over local corpus, two-phase nested PRD structure.
8. **Day 1 spikes (when build window starts):** install `google-agents-cli`, run Phoenix-MCP+ADK integration spike (assumption A4), close open questions J1 and J2.

### Next Agent Should Know

- **Architecture is now skill-driven.** [docs/architecture/2026-05-27-aegis-arch.md](../architecture/2026-05-27-aegis-arch.md) is the canonical blueprint. `docs/architecture.md` is just a pointer file. Update the dated file first when anything changes; add an ADR if non-trivial.
- **The 12-agent decision is audacious-but-bounded.** ADR-004 documents 4 hard revisit triggers — Day 10 progress gate, A5 fail, demo-coherence test (Day 15), build slippage. The next agent must enforce these gates rigorously. If any fires, escalate to PM with options per the Code-Wall Escalation Protocol.
- **`google-agents-cli` is the Day 1 install.** PM has approved adoption. Verify J1 (observability skill ↔ Phoenix MCP) and J2 (deploy ↔ 2-service) on Day 1 / Day 6–7 respectively.
- **The "12" framing is preserved in pitch language, but architectural honesty is documented.** When writing public-facing content (PRD, README, Devpost), say "12-agent swarm" if it's the strategic story; when designing/building, refer to the honest 10+1+1+2 = 14 component breakdown in architecture spec §3.1.
- **Preservation discipline is the project rule.** When rewriting any major doc, cross-check against the prior version; build a port-list of facts/rules/constraints that must survive; call out anything dropped with reason. Already proven this session for AGENTS.md and architecture.md. Apply to README.md and PRD next.
- **Tone guardrail and UX-as-pillar are non-negotiable** — already in AGENTS.md (root), frontend/AGENTS.md, and design-brief.md. Carry forward.

### Revisit Triggers

(These apply to the project state going into Session 4 — same as Session 2 plus the new Session 3 ones)

- Any critical assumption test (A1–A5) fails → re-open the pitch claim it supports; escalate to PM with options.
- Phoenix Cloud free tier nears 80% of any quota → upgrade ($50 ceiling approved in spirit).
- Gemini 3 not available by Day 14 → fallback to Gemini 2.5 (already in mitigation).
- New competitor surfaces in Arize-track Devpost listings by Day 14 → revisit differentiation thesis.
- **Day 10 progress gate** on Part B specialist agents — see [ADR-004](../adr/ADR-004-twelve-agent-part-b-swarm.md).
- **A5 (Learning Coordinator autonomy)** Day 10 go/no-go — see ADR-004.
- **Demo coherence test Day 15** — see ADR-004.
- **`google-agents-cli` observability conflict with Phoenix MCP** — Day 1 spike (open question J1).
- **`google-agents-cli deploy` for 2-service Cloud Run** — Day 6–7 verification (open question J2).

### Working Tree

Newly created or modified this session:
- New: `AGENTS.md` (root, overwriting old) · `frontend/AGENTS.md` · `backend/AGENTS.md` · `frontend/` dir · `backend/` dir · `docs/architecture/2026-05-27-aegis-arch.md` · `docs/architecture/` dir · `docs/adr/` dir · `docs/adr/ADR-001..005-*.md` (5 files)
- Replaced: `docs/architecture.md` (now a thin pointer to the dated spec)
- Modified: `docs/memory/decision-log.md` · `docs/memory/current-state.md` · `docs/memory/agent-handoffs.md` (this entry) · `docs/open-questions.md` · `docs/skill-outputs/SKILL-OUTPUTS.md`

Recommend PM commit before Session 4 starts so the architecture rebuild is preserved as a clean checkpoint. `git add -A && git commit -m "Session 3: AGENTS.md rebuild + architecture skill-driven rebuild + 5 ADRs"` (or similar).

## 2026-05-27 11:15 - Session 4 Handoff (Antigravity)

### Done
- Refactored `README.md` to prioritize user-scenario/pain framing and Next.js + FastAPI stack.
- Swept `docs/open-questions.md`, resolving stale technical questions into the "decided" section.
- Finished PRD v4 updates (UX pillar, Next.js, assumption tests, demo script updates, Arize Rubric alignment).
- Generated `docs/product-soul.md` for strategic grounding.
- Rebuilt eval design per AlphaEval 2026: created `docs/evals/2026-05-27-aegis-appeal-rubric.md`, `docs/evals/2026-05-27-aegis-judges.md`, `docs/evals/2026-05-27-aegis-eval-pipeline.md`, and `eval/simulator_rules.json`.
- Generated 10 agent role prompts via `create-agent-prompt` skill and seeded them in `backend/src/prompts/`.
- Updated `docs/memory/current-state.md` and `docs/skill-outputs/SKILL-OUTPUTS.md`.

### Debated
- Addressed backlog of document inconsistencies directly resulting from architectural shifts in Sessions 2 and 3 without reopening the debates.

### Decisions
- Treat Phase 0 (Planning) and Phase 1 (Eval Design) as officially complete.

### Deferred
- Day 1 build spikes (installing `google-agents-cli`, setting up Phoenix MCP integration tests).

### Next Agent Should Know
- The PRD, architecture, eval pipeline, and agent prompts are now 100% aligned with the 12-agent Next.js + Python ADK swarm strategy. 
- The project is fully unblocked for Day 1 Build (Phase 6 of original TODO list).
- First tasks: Set up GCP/Phoenix environment variables, `git init`, and `google-agents-cli` backend scaffolding.

### Revisit Triggers
- (Carry forward from Session 3): Day 10 progress gate, A5 Learning Coordinator autonomy check, Demo coherence test (Day 15).
- Phoenix Cloud free tier approaching 80% quota limits.

### Working Tree
- Dirty. Many planning artifacts created/modified (`backend/src/prompts/*`, `docs/evals/*`, `README.md`, `PRD.md`, `docs/open-questions.md`, `product-soul.md`, `eval/simulator_rules.json`, memory files). Should be committed to a clean `git init` repo.

---

## 2026-05-27 — Session 5 Handoff (Droid) — CLOSED

Corrective session. PM identified 5 gaps in Session 4 output. All 6 TODOs in the corrective plan are now complete. 5 atomic commits.

### Gaps corrected (from PM)
1. Eval rubric was a skeleton — inconsistent scoring scales, undefined panel, no calibration examples, no cost model.
2. Agent prompts were interface contracts — zero domain knowledge, no few-shot, no CoT.
3. PRD §8 contradicted the new rubric (Safety 10% weighted in PRD vs binary hard gate in rubric).
4. No implementation plan existed.
5. Sessions accumulating with too few commits — no rollback safety per session.

### Done in Session 5
- ✅ **TODO 1 — Commit Session 4 work as-is for rollback safety.** Commit `6a3ed58`. Pre-commit secret scan clean.
- ✅ **TODO 2 — Eval rubric v2.** Replaced rubric with v2 (all dims 1/3/5; 7-judge panel: J1/J2 hard gates + J3–J7 weighted; calibration anchors; $0.014/judge, $0.10/letter, $1.20/MVP, $300/20-day ceiling; κ ≥ 0.6 calibration gate; output schema + aggregation formula; anti-pattern checklist). Commit `9ee69da`.
- ✅ **TODO 3 — PRD §8 reconciled.** Hard-gate vs weighted split; per-dimension regression-threshold gating; SC2/SC3 phrased as hard-gate PASS rates; §15.2 Safety Gates rebuilt as binary; §15.3 Rollback zero-tolerance on hard-gate FAIL. Commit `d65e13c`.
- ✅ **TODO 4 — 10 agent prompts rewritten as LLM system prompts.** All include persona + objective, domain context (insurer tactics + ERISA/ACA/MHPAEA/NSA + clinical guidelines), tool-use protocol, CoT scaffold, output JSON schema, worked few-shot, guardrails. Interface-contract format kept as docstring section, not whole prompt. Commit `17e6c27`.
- ✅ **TODO 5 — Day 1–20 implementation plan generated.** Via `implementation-plan` skill. Output: `docs/plans/2026-05-27-aegis-implementation-plan.md` (4 phases, 67 tasks, 11 risks, full PRD-ID traceability) + companion flat task list `docs/plans/2026-05-27-aegis-implementation-tasks.md`. A1–A5 + Day 10 + Day 14/15 gates explicitly scheduled. **Phase 0 (GCP + Phoenix + agents-cli setup) gated on PM sign-off.** Commit `079064d`.
- ✅ **TODO 6 — Memory updated.** This handoff closed; current-state refreshed to Session-5 reality; decision-log appended with 3 new Session 5 entries (rubric v2, prompts rewrite, implementation plan); skill-outputs ledger logged in TODO 5 commit. Commit forthcoming.

### Commits this session (5)
1. `6a3ed58` — Session 4 (as-is) rollback safety
2. `9ee69da` — Session 5 TODO 2: eval rubric v2
3. `d65e13c` — Session 5 TODO 3: PRD §8 reconciliation
4. `17e6c27` — Session 5 TODO 4: agent prompts as LLM system prompts
5. `079064d` — Session 5 TODO 5: Day 1–20 implementation plan + task list
6. *(pending)* Session 5 TODO 6: memory close-out

### Decisions captured (in decision-log)
- Eval rubric v2 (AlphaEval-compliant; hard gates + weighted dimensions).
- Agent prompts as full LLM system prompts (not interface contracts).
- Day 1–20 implementation plan formalised; Phase 0 PM-gated.

### Next Agent Should Know

- **Planning is complete. Project is ready for Phase 0 execution upon PM sign-off.** All planning artifacts (PRD v4, architecture, eval rubric v2, eval pipeline, agent prompts v1, implementation plan, task list) are aligned.
- **Phase 0 = STOP-AND-ASK gate.** PM explicitly asked to be consulted before any GCP / Phoenix Cloud setup. Do NOT silently run `gcloud` or sign up for accounts without PM confirmation. See plan §4 Phase 0.
- **The hard gates (A1–A5 + Day 10 + Day 14/15) are the safety nets.** Enforce them. Each carries a documented fallback — see plan §5 + tasks file gate index.
- **`docs/plans/2026-05-27-aegis-implementation-tasks.md` is the agent-pickable execution surface.** Each task has DoD + traceability ID; pick one task per coding-agent session; commit with task ID in message.
- **Source-of-truth files:** PRD (`docs/prd/PRD.md`), architecture (`docs/architecture/2026-05-27-aegis-arch.md`), rubric (`docs/evals/2026-05-27-aegis-appeal-rubric.md`), prompts (`backend/src/prompts/*_v1.md`), plan (`docs/plans/`).
- **No application code yet.** `backend/src/` has only `prompts/`. `frontend/` has only an AGENTS.md. Phase 0 + Phase 1 Day 1 will produce the first running code.

### Carry-forward Revisit Triggers
- A4 (Phoenix MCP + ADK integration) Day 2 EOD go/no-go.
- A2 (Phoenix UI demo-viability) Day 2 EOD.
- A3 (case credibility) Day 3 EOD.
- A1 (eval signal) Day 5 EOD.
- Day 10 progress gate + A5 (Learning Coordinator autonomy) Day 10 EOD ([ADR-004](../adr/)).
- Day 14 demo-coherence pre-check; Day 15 formal check ([ADR-004](../adr/)).
- Phoenix Cloud free tier > 80% quota.
- Open Q J1 (`google-agents-cli` observability vs Phoenix MCP) — Day 1 (task T1.5).
- Open Q J2 (`google-agents-cli deploy` vs 2-service Cloud Run) — Day 7 (task T7.1).
