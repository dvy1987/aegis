# Project Index — Aegis

Quick navigation for agents picking up this project.

---

## Read order on session start

0. **[docs/memory/orientation-map.md](orientation-map.md)** — fastest cold-start orientation: what's *built* vs *only designed*, plus the real gaps (derived 2026-05-30 via `/graphify`). A queryable graph of the whole repo lives in `graphify-out/`.
1. **[docs/memory/current-state.md](current-state.md)** — what's the project state right now?
2. **[docs/memory/agent-handoffs.md](agent-handoffs.md)** — latest handoff + comprehensive TODO list
3. **[AGENTS.md](../../AGENTS.md)** — rules for working in this repo + working-with-PM agreement
4. **[docs/prd/PRD.md](../prd/PRD.md)** — what we're building (MVP Part A + Full Plan Part B)
5. **[docs/open-questions.md](../open-questions.md)** — what's still unresolved
6. **[docs/architecture.md](../architecture.md)** — technical blueprint (currently freehanded; needs skill-driven rebuild)

## Key context (one-line summaries)

- **What:** Aegis — a self-improving multi-agent system for US health-insurance appeals
- **For:** Google Cloud Rapid Agent Hackathon, Arize partner track, $5K prize
- **By:** Solo PM (non-technical) vibe-coding with Amp over 20 days
- **Why this wins:** Self-improvement loop via Phoenix MCP is the *core mechanic*, not bolted-on
- **Two-phase strategy:** Day 7 MVP = safety net, Day 20 Full Plan = win condition
- **Reality check (2026-05-31, post-Session-23):** Part A v1 + case generator + Part A judge panel are built. **Plan 1 substrate (F1–F7) done** (drafter LLM-driven; Outcome Simulator out of the 6-tool Student; `run_evaluated_case()` writes a firewall-safe *laundered* signal to a `PhoenixRecorder`). **The Outcome Simulator is now the two-step transparent form** (Session 23): LLM `assess` does critique-first fuzzy 1/3/5 feature judgment, a deterministic `score_outcome` over published `eval/simulator_rules.json` produces APPROVE/DENY (weighted sum + must-have veto + 0.70 threshold); the `threshold=10` hack is deleted. Still unbuilt: the **Learning Coordinator (Plan 2)**, live Phoenix MCP *reads* (`phoenix_mcp_lookup` still a stub), and the Part B swarm. See [current-state.md](current-state.md) Session 23 + [learnings.md](learnings.md) Session 22 + [orientation-map.md](orientation-map.md)

## Handoff log

| Date | Session | Handoff file |
|---|---|---|
| 2026-05-28 | Session 12 (aegis_v1 ADK agent) | [agent-handoffs.md](agent-handoffs.md#2026-05-28-0755---handoff) |
| 2026-05-24 | Session 1 (Amp) | [agent-handoffs.md](agent-handoffs.md#2026-05-24--session-1-handoff-amp) |
| 2026-05-25 | Session 2 (Amp) | [agent-handoffs.md](agent-handoffs.md#2026-05-25--session-2-handoff-amp) |

| 2026-05-27 | Session (Agent) | [agent-handoffs.md](agent-handoffs.md#2026-05-27-1408---handoff) |
| 2026-05-27 | Session 7 (Droid — frontend design system + scaffold) | [agent-handoffs.md](agent-handoffs.md#2026-05-27---session-7-handoff-droid) |
| 2026-05-27 | Session 8 (Droid — dev scripts + Vertex AI config) | [agent-handoffs.md](agent-handoffs.md#2026-05-27-1530---session-8-handoff-droid) |
| 2026-05-28 | Session 13 (Realistic Imperfection & AlphaEval Gap Fixes) | [agent-handoffs.md](agent-handoffs.md#2026-05-28---session-13-handoff-antigravity) |
| 2026-05-28 | Session 14 (User/Manual updates) | [agent-handoffs.md](agent-handoffs.md#2026-05-28---session-14-handoff-usermanual) |
| 2026-05-28 | Session 15 (Generation Pipeline P5) | [agent-handoffs.md](agent-handoffs.md#2026-05-28---session-15-handoff) |
| 2026-05-28 | Session 16 (Documentation Sweep) | [agent-handoffs.md](agent-handoffs.md#2026-05-28-1416---session-16-handoff-antigravity) |
| 2026-05-28 | Session 17 (SkillOpt & Multi-Service Topology) | [agent-handoffs.md](agent-handoffs.md#2026-05-28-1448---session-17-handoff-antigravity) |
| 2026-05-29 | Session 19 (Part A Judge Panel) | [agent-handoffs.md](agent-handoffs.md#2026-05-29-0907---session-19-handoff-codex) |
| 2026-05-29 | Session 20 (Gumloop prompt overhaul) | [agent-handoffs.md](agent-handoffs.md#2026-05-29--session-20-handoff-antigravity) |
| 2026-05-30 | Session 21 (Orientation + Learning Coordinator design + plan) | [agent-handoffs.md](agent-handoffs.md#2026-05-30--session-21-handoff-claude--orientation--learning-coordinator-design) |
| 2026-05-30 | Session 22 (✅ **executed Plan 1 substrate F1–F7**, subagent-driven; 26 tests green offline; commits 2a5e9c3..ab1bcd2) | [session-22-execution-handoff.md](session-22-execution-handoff.md) |
| 2026-05-31 | Session 22 cont. (✅ per-appeal Outcome Simulator re-wired; ✅ core docs reconciled; **spec + plan for two-step transparent simulator**) | [session-23-execution-handoff.md](session-23-execution-handoff.md) |
| 2026-05-31 | Session 23 (✅ **executed the two-step transparent Outcome Simulator** plan, subagent-driven; LLM fuzzy `assess` → deterministic `score_outcome`; `threshold=10` hack deleted; 48 offline tests green; commits `b380469..89f737f`) | [session-23-execution-handoff.md](session-23-execution-handoff.md) |
| 2026-05-31 | Session 23 cont. (✅ fixed live-agent drafter↔ADK forward-ref bug `7dec151`; **Learning Coordinator v2 GEPA spec + offline build plan** `c56a9cc`/`02c273c` → next: build + assistant-orchestrated prompt optimization) | [session-24-execution-handoff.md](session-24-execution-handoff.md) |
| 2026-05-31 | Session 24 (✅ **executed Phase 1 — built the offline Learning Coordinator** `backend/app/learning/`, subagent-driven, 12 TDD tasks; GEPA mechanics + Phoenix-grounded store + firewalled signal + efficacy harness; caught+fixed a real firewall plan bug; learning 35 / full unit **86 passed** offline; commits `9f048f7..53f1eaf` → next: Phase 2 assistant-orchestrated prompt optimization) | [session-24-execution-handoff.md](session-24-execution-handoff.md) |
| 2026-05-31 | Session 24 cont. (✅ **Phase 2 — real efficacy measured**: Claude session as drafter/judge/reflection intelligence over real cases; optimized `appeal_vector_capture` → **held-out 0.73→0.88, +20.5%**, firewall intact; promoted `drafter_v2`; run captured + replay regression test; full unit **90 passed**; commit `2c21d33`) | [docs/evals/2026-05-31-coordinator-efficacy-run.md](../evals/2026-05-31-coordinator-efficacy-run.md) |
| 2026-05-31 | Session 24 cont. (✅ **wrote Tier 2 + Tier 1 plans + Session-25 handoff**: Tier 2 = offline efficacy continuation (`efficacy_io` + round 2 full split + reflection meta-prompt A/B); Tier 1 = live GCP/Phoenix companion (live `phoenix_mcp_lookup` T4.1, `LivePhoenixLearningStore`, MCP-off counterfactual, κ calibration) → next: execute Tier 2 then Tier 1) | [session-25-execution-handoff.md](session-25-execution-handoff.md) |
| 2026-06-01 | Session 25 (✅ **executed Tier 2 offline**, subagent-driven: `efficacy_io` extracted+tested; round 2 on **full 11-case train split → offline ceiling reached, no promotion** (honest null, `drafter_v2` retained); reflection meta-prompt A/B → **base wins** (critique_plus under-captured); full unit **97 passed**; commits `1ae716e..ef04cda` → next: **Tier 1 (live GCP/Phoenix)**) | [docs/evals/2026-06-01-coordinator-efficacy-run2.md](../evals/2026-06-01-coordinator-efficacy-run2.md) |

## Skill-output log

See [docs/skill-outputs/SKILL-OUTPUTS.md](../skill-outputs/SKILL-OUTPUTS.md).
