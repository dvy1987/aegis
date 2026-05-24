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
