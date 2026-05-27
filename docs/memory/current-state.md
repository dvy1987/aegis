# Current State — Aegis

**Updated:** 2026-05-27 (Session 3)
**Phase:** Pre-build planning. AGENTS.md rewritten via `project-setup` with full preservation discipline + Session 2 decisions integrated. Tooling decision landed (`google-agents-cli`). Part B 12-agent architecture confirmed as the audacious bet with explicit revisit triggers. **No application code exists yet.**

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

## Session 3 progress (2026-05-27)

- ✅ `memory-startup` ran; bounded context loaded
- ✅ Researched `google-agents-cli` (released April 2026) — confirmed it's complementary to ADK, not a replacement; bundles 7 ADK-lifecycle skills via `uvx google-agents-cli setup`
- ✅ Cross-checked Part B 12-agent topology against Google's official [8-pattern ADK multi-agent guide](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/) — surfaced 5 architectural critiques; PM made informed call to keep 12 agents as audacious bet with revisit triggers
- ✅ `project-setup` skill ran: 3 AGENTS.md files written (root 145 lines, frontend 51 lines, backend 78 lines — all under 150-line skill rule)
- ✅ Preservation discipline applied: every valid rule from old AGENTS.md absorbed; stale rules (Streamlit lock, single-agent-only) explicitly reversed with provenance noted
- ✅ Multi-file mode with `frontend/` and `backend/` dirs scaffolded (empty for now, AGENTS.md inside each ready for when code lands)
- ✅ SDD mode on: Orchestration Map includes the full `spec-driven-development` chain + spec-first rule for behaviour changes
- ✅ Autonomy boundaries codified: strict ask-first on product/architecture/copy; full autonomy on tests, internal refactors, tooling
- ✅ Two decisions logged in [decision-log.md](decision-log.md): adopt `google-agents-cli` Day 1; keep 12-agent Part B with hard revisit triggers (Day 10 progress gate, A5 fail, demo-coherence test, build-time slippage)
- ✅ Two new open questions added in [open-questions.md §J](../open-questions.md): agents-cli observability vs Phoenix MCP compatibility (Day 1); agents-cli deploy vs 2-service Cloud Run (Day 6–7)
- ✅ [open-questions.md §I](../open-questions.md) "Things explicitly NOT open" rewritten to reflect Session 2 + Session 3 decisions (Next.js + Python ADK, 12-agent Part B, agents-cli adoption, UX as pillar, tone guardrail)
- ✅ Stale-doc cleanup pass 1 complete: `docs/architecture.md` replaced by skill-driven rebuild at [docs/architecture/2026-05-27-aegis-arch.md](../architecture/2026-05-27-aegis-arch.md) via `agent-system-architecture` skill. Old freehanded version retained as pointer. Honest component count documented (14 total: 10 LLM agents + 1 judge panel + 1 simulator + 2 meta). Mermaid wiring + state strategy + HITL + observability all captured.
- ✅ ADRs backfilled (Session 3) via `architectural-decision-log` skill: ADR-001 (Google ADK), ADR-002 (Phoenix Cloud + MCP load-bearing), ADR-003 (Next.js + Python ADK overturn), ADR-004 (12-agent Part B swarm with revisit triggers), ADR-005 (`google-agents-cli` adoption). ADR-001 and ADR-002 are SYNTHESIS (retrospective from observed Session 1 decisions); ADR-003/004/005 are CONTEMPORANEOUS.
- 🟡 Stale-doc cleanup deferred to Session 4 (per PM direction): `README.md` (Streamlit refs, "elessar/" tree in repo structure, weak pitch per [feedback.md](../feedback.md)), `docs/open-questions.md` body sweep beyond §I (only §I + §J edited this session).
- 🟡 PRD edits §3 onward also deferred (still partial v3 / partial v2; Session 2 continuation plan applies).
- 🟡 Eval design rebuild via `eval-output` chain still pending (Phase 1 of Session 1 TODO).
- 🟡 `product-soul` doc generation still pending.
- 🟡 `create-agent-prompt` for the 10 agent roles still pending — must happen before Day 8 build start.

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
