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
| 2026-06-09 | Session end (Cursor — simulator hard gates + drafter) | [agent-handoffs.md](agent-handoffs.md#2026-06-09--handoff-cursor--simulator-hard-gates--drafter-inputs) |
| 2026-06-09 | Session end (Cursor — GEPA judges + faithfulness) | [agent-handoffs.md](agent-handoffs.md#2026-06-09--handoff-cursor--gepa-judges--faithfulness-rubric) |
| 2026-06-09 | Session end (Cursor — showcase copy rejig) | [agent-handoffs.md](agent-handoffs.md#2026-06-09--handoff-cursor--showcase-copy-rejig) |
| 2026-06-09 | Session end (Cursor — showcase cinematic + polish) | [agent-handoffs.md](agent-handoffs.md#2026-06-09--handoff-cursor--showcase-cinematic--polish) |
| 2026-06-07 | Session end (Cursor — ADK Phase 0 + Workflow D24) | [agent-handoffs.md](agent-handoffs.md#2026-06-07--session-end-cursor--adk-phase-0--workflow-decision) |
| 2026-06-07 | Session (Cursor — ADK plan v2 finalized) | [agent-handoffs.md](agent-handoffs.md#2026-06-07--session-end-cursor--adk-plan-v2-finalized) |
| 2026-06-07 | Session (Cursor — showcase learning-loop robustness + day-zero reset) | [agent-handoffs.md](agent-handoffs.md#2026-06-07--handoff-cursor--showcase-learning-loop-robustness--day-zero-reset) |
| 2026-06-06 | Session (Codex — showcase workflow controls + 6-box matrix) | [agent-handoffs.md](agent-handoffs.md#2026-06-06---handoff-codex---showcase-workflow-controls--6-box-matrix) |
| 2026-06-06 | Session (Codex — showcase redesign backend implementation pass) | [agent-handoffs.md](agent-handoffs.md#2026-06-06---handoff-codex---showcase-redesign-backend-implementation-pass) |
| 2026-06-06 | Session (Droid — showcase baseline reset + redesign plan) | [agent-handoffs.md](agent-handoffs.md#2026-06-06-1750---handoff-droid---showcase-reset-to-day-zero-baseline) |
| 2026-06-06 | Session (Codex — v1 showcase GEPA quick/serious plan) | [agent-handoffs.md](agent-handoffs.md#2026-06-06--handoff-codex--v1-showcase-gepa-quickserious-plan) |
| 2026-06-03 | Session (Cloud library + Vertex index live) | [agent-handoffs.md](agent-handoffs.md#2026-06-03--session-end-handoff-cursor--cloud-library-built--vertex-index-live) |
| 2026-06-05 | Session (Codex — live showcase planning drafts) | [agent-handoffs.md](agent-handoffs.md#2026-06-05-2054---handoff-codex--live-showcase-planning-drafts) |
| 2026-06-02 | Session (Gumloop prompt-pass cases 01–500) | [agent-handoffs.md](agent-handoffs.md#2026-06-02-1759--session-end-handoff-cursor--gumloop-prompt-pass-on-drafts-cases-01500) |
| 2026-06-02 | Session (Nav connected dot + v1 model/location consistency) | [agent-handoffs.md](agent-handoffs.md#2026-06-02-1641--session-end-handoff-cursor--nav-connected-green-dot--v1-modellocation-consistency) |
| 2026-06-02 | Session (cloud-only library + explicit discovery error) | [agent-handoffs.md](agent-handoffs.md#2026-06-02-1310--session-end-handoff-cursor--cloud-only-library--explicit-discovery-error-no-silent-toggles) |
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
| 2026-06-01 | Session 25 cont. (✅ **built Tier 1 credential-free offline cores** TDD: `PanelJudgeAdapter` (T1), MCP-off `counterfactual` harness (T5), Cohen's κ `calibration` (T6); full unit **103 passed**; commits `8a35860`,`5720eaf`. **Held T2/T3** (parse real Phoenix payloads → need T0 fixtures) and all live/gated work → **needs GCP ADC + `PHOENIX_API_KEY` + Phoenix MCP-auth fix (T0)**) | [current-state.md](current-state.md) |
| 2026-06-01 | Session 26 (✅ **reimagined the frontend** via brainstorming→spec→plan→subagent/inline build: two surfaces in one locked design language — `/appeal` calm consumer flow + `/showcase` "How Aegis learns"; one `DataSource` seam, **demo default** (real 10-case fixtures, offline) ↔ live `/v1/appeal`; frontend firewall test (no answer-key leak); **17 tests green, 4 routes build**; branch `feat/frontend-two-surface` `d287666..fcdedfd` — **actually merged + pushed to `origin/main` shortly after** through `daf5f6a`; prior handoff text saying "not merged" is stale) | [spec](../superpowers/specs/2026-06-01-aegis-frontend-design.md) · [plan](../superpowers/plans/2026-06-01-aegis-frontend.md) |
| 2026-06-01 | Session 27 (✅ **Cloud Run deploy scripts written** — `backend/deploy-v1.sh` (v1 only, Secret-Manager + IAM via `--bootstrap`), `frontend/deploy.sh` (demo default, `--mode live` for Track B); `frontend/Dockerfile` + `output: 'standalone'`; `backend/scripts/smoke_track_b.py` smoke test; L1+L2+L3 of live pipe ✅ but 🔴 **Track B Vertex latency blocked** (`location=global` returns ~155 s, second call hung); ✅ flagged: Session 26 branch is **already on `origin/main`**, stale memory note. **8 files uncommitted on `main`**.) | [agent-handoffs.md](agent-handoffs.md) |
| 2026-06-01 | Session 27 cont. (✅ **Part B swarm Phases 1–3 built offline-first**, all 10 agents as a pure core: P2 = 5-researcher fan-out + deterministic routing + `LiteratureDiscovery` (ADR-007, offline fakes, off-by-default, sanitize→trust-tier→provenance→ingest→audit); P3 = **3 deliberately-weak baselines** (drafter/strategist/medical_necessity, a `registry.WEAK_V1_AGENTS` dial) + per-agent **firewall-safe `AgentTraceSignal`**; **+ evolution-integrity hardening** — weak-meta stripped from prompts→`WEAK_BASELINES.md`, strong prompts quarantined→`prompts/targets/`, "no known-good leakage" invariant. **173 unit green.** Commits `0454022`. Next: Phase 4) | [agent-handoffs.md](agent-handoffs.md#2026-06-01-2038--session-end-handoff-cursor--part-b-swarm-phases-13-done--evolution-integrity-hardening) |
| 2026-06-01 | Session 27 cont. (✅ **Part B swarm Phase 4 live surfaces** — ADK `run_swarm_appeal` + `POST /v1/swarm/appeal`, `VertexSearchCorpusStore`, grounded discovery hook, `OtelSwarmTraceRecorder` per-agent spans, `swarm_config` stub/live dial. **192 unit green.** Commits `0454022`+`27537ef`, **2 ahead of origin, not pushed**. Next: Phase 5 Learning Coordinator wire-up) | [agent-handoffs.md](agent-handoffs.md#2026-06-01-2115--session-end-handoff-cursor--part-b-swarm-phases-14-done-committed) |
| 2026-06-01 | Session 27 end (✅ **Part B swarm Phase 5 eval + MCP counterfactual** — `run_evaluated_swarm_case`, `run_swarm_counterfactual`, offline script; **207 unit green.** Commit `5bab203`. Phases 0–5 done; Phase 6 next. **26 commits ahead of origin, not pushed.** Dirty WIP: casegen/v1/drafts unrelated) | [agent-handoffs.md](agent-handoffs.md#2026-06-01--session-end-handoff-cursor--part-b-swarm-phase-5-done-committed) |
| 2026-06-02 | Session 28 end (✅ **Part B swarm Phase 6 Learning Coordinator re-point** — credit map → `SwarmLearningCoordinator`, all pipeline agents evolvable; autonomy ladder + 60/40 benchmark loader; **228 unit green.** Phases 0–6 complete. Unrelated WIP still dirty.) | [agent-handoffs.md](agent-handoffs.md#2026-06-02--session-28-handoff-cursor--part-b-swarm-phase-6-done-learning-coordinator-re-point) |
| 2026-06-05 | Session (Droid — Tier 1 Phoenix live wiring) | [agent-handoffs.md](agent-handoffs.md#2026-06-05--session-handoff-droid--tier-1-phoenix-live-wiring) |
| 2026-06-07 | Session (Cursor — showcase robustness committed `19a644b`; Cloud Run ops documented; demo cheatsheet + 10s poll; **8 files uncommitted**) | [agent-handoffs.md](agent-handoffs.md#2026-06-07--handoff-cursor--cloud-run-ops-clarity--demo-cheatsheet--poll-interval) |
| 2026-06-07 | Session (Warp/Oz — **ADK Phase 1 built**: student `Workflow` + drafter + all 6 @node steps; pipeline fully on ADK; **325 passed**) | [agent-handoffs.md](agent-handoffs.md#2026-06-07--session-warpoz--adk-phase-1-built-student-workflow--drafter) |

## Skill-output log

See [docs/skill-outputs/SKILL-OUTPUTS.md](../skill-outputs/SKILL-OUTPUTS.md).
