# Current State — Aegis

**Updated:** 2026-05-25 (Session 2)
**Phase:** Pre-build planning, deep-thinking + strategic refinement underway. **No application code exists yet.**

---

## What's done
- Strategic ideation (15+ ideas explored, 1 chosen)
- Unified PRD with MVP (Part A) + Full Plan (Part B) — [docs/prd/PRD.md](../prd/PRD.md)
- Architecture sketch — [docs/architecture.md](../architecture.md)
- Open questions catalogued — [docs/open-questions.md](../open-questions.md)
- Project skeleton: AGENTS.md, README.md, LICENSE (Apache 2.0), .gitignore, .env.example
- Working-with-PM rules captured in AGENTS.md
- Oracle consulted for strategy + architecture sanity check

## What's blocked
- **All build work** — Phase 0 + Phase 1 in TODO must clear first
- Eval design needs rebuild via `eval-rubric-design` + `eval-judge` + `eval-pipeline` (AlphaEval-compliant)
- Most artifacts in repo were freehanded by Amp without invoking the matching skills — needs retroactive correction
- Multiple 🔴 BLOCKER open questions unresolved (deadline, accounts, repo creation, scope confirmations)

## Active decisions
- Codename: **Aegis**
- Stack: Google ADK + Gemini 3 + Phoenix Cloud + Phoenix MCP + Streamlit + Cloud Run
- License: Apache 2.0
- Autonomy model: 3-stage competency ladder (Apprentice → Journeyman → Master) with auto-demotion — thresholds TBD post eval rebuild
- Phase strategy: MVP Day 7 = safety net; Full Plan Day 20 = win condition

## Active risks
- Eval design currently violates AlphaEval principles → could undermine entire Arize submission credibility
- Skills not being used → every artifact is below skill-driven quality
- No git history yet → no rollback safety
- Time pressure: 20-day window has not started; planning phase is consuming Day 0

## Source of truth files
| Artifact | File |
|---|---|
| Product spec | [docs/prd/PRD.md](../prd/PRD.md) |
| Architecture | [docs/architecture.md](../architecture.md) |
| Open questions | [docs/open-questions.md](../open-questions.md) |
| TODO + handoff | [docs/memory/agent-handoffs.md](agent-handoffs.md) |
| Agent rules | [AGENTS.md](../../AGENTS.md) |
| Idea history | [docs/ideas.md](../ideas.md) |
| Hackathon brief | [docs/challenge.md](../challenge.md) |

## Session 2 progress (2026-05-25)

- ✅ Memory skeleton completed (MEMORY-ROUTING.md + 5 stub files + archived/)
- ✅ Pre-mortem run on Aegis as a whole — see session-log; surfaced causes A, K, M, D, C as top risks
- ✅ Arize hackathon rubric re-read and aligned — see [docs/challenge.md](../challenge.md); confirmed two co-equal Arize pillars (tracing+MCP + self-improvement loop)
- ✅ Strategic shift: **UX is a first-class product pillar** (was: supporting actor) — PM directive
- ✅ Framework decision: **Next.js + Python ADK backend** (was: Streamlit-only) — see [decision-log.md](decision-log.md)
- ✅ Design brief produced: [docs/design-brief.md](../design-brief.md) — archetype, tone, copy rules, motion, accessibility floor
- ✅ Impact research compiled: [docs/research/impact-stats.md](../research/impact-stats.md) — verified primary sources (KFF, Commonwealth Fund, JAMA, Senate report)
- ✅ Decisions logged: [decision-log.md](decision-log.md) (5 entries)
- ✅ Assumption mapping complete: [docs/research/assumption-map.md](../research/assumption-map.md) — 20 assumptions surfaced, 5 critical with minimum tests defined (A1 eval signal, A2 Phoenix UI demo viability, A3 case credibility, A4 MCP+ADK integration, A5 Learning Coordinator autonomy)
- ✅ Tone guardrail added to [AGENTS.md](../../AGENTS.md) and [design-brief.md §8](../design-brief.md) — no violence/vigilantism/polarizing-event references in any artifact
- 🟡 **PRD v3 rewrite started but PARTIAL** — front matter, §1, §2, new §2.1 updated; §3 onward still in v2 voice. Do not ship in current state. Continuation plan captured in [agent-handoffs.md (Session 2)](agent-handoffs.md#2026-05-25--session-2-handoff-amp)
- ⏳ **Next session:** Finish PRD v3 edits → product-soul → AGENTS.md full rewrite via `project-setup` → ADR synthesis

## Queued PRD / AGENTS.md updates (do these after assumption-mapping)

1. **PRD §1 Vision + §2 Problem** — fold in impact paragraph from [impact-stats.md §7](../research/impact-stats.md#7-the-aegis-impact-paragraph-drop-into-prd-1-vision-and-devpost-form)
2. **PRD §5 Differentiation** — add competitive landscape acknowledgment (Counterforce Health, Sheer Health, etc.) and Aegis's 4-point differentiation thesis
3. **PRD §16 Demo Script** — rewrite so Phoenix Cloud UI is visibly on-screen ≥60s of 180s; compressed pitch line in voiceover
4. **PRD §17 (new) Arize Rubric Alignment** — map every PRD section to the 4 hackathon-wide + 4 Arize-track criteria + bonus
5. **AGENTS.md (full rewrite)** — via `project-setup` interview; remove Streamlit lock; add UX-as-pillar rule; add Code-Wall Escalation Protocol; add tone-of-voice rules; preserve all info from current AGENTS.md per PM preservation principle

## Next recommended action

Move into **assumption-mapping** on pre-mortem causes A (Phoenix demo framing), K (demonstrable improvement), and D (synthetic case credibility). Then do PRD updates and AGENTS.md rewrite.
