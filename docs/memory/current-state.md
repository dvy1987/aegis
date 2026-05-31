# Current State — Aegis

**Updated:** 2026-05-31 (Session 24)
**Phase:** **Execution — Phase 1.** Phase 0 setup complete. Backend wired up into a 3-service logical topology (v1, swarm, and generator job) to properly isolate Phoenix traces. Generator uses ADC, dev launcher spins up 3 processes. Firewall logic designed for eval scoring. 

---

## What's done (planning + corrections complete)

### Sessions 1–4
- Strategic ideation, codename Aegis, two-phase nested PRD (Part A MVP / Part B Full Plan)
- AGENTS.md (root + frontend + backend) via `project-setup` skill
- Architecture spec via `agent-system-architecture` — `docs/architecture/2026-05-27-aegis-arch.md`
- 5 ADRs backfilled (ADK choice, Phoenix+MCP load-bearing, Next.js+Python overturn, 12-agent swarm with revisit triggers, agents-cli adoption)
- Open questions catalogued; product-soul written; design-brief written; impact-stats compiled; assumption map (5 critical: A1–A5) compiled
- 10 v1 agent role prompts seeded in `backend/src/prompts/`

### Session 5 (corrections)
- ✅ **Eval rubric v2** at [`docs/evals/2026-05-27-aegis-appeal-rubric.md`](../evals/2026-05-27-aegis-appeal-rubric.md) — AlphaEval-compliant: 2 binary hard gates (J1 Safety, J2 Hallucination & Internal Consistency) + 5 weighted dimensions normalised to 1/3/5 (J3 Grounding 35%, J4 Case Specificity 25%, J5 Evidence Completeness 15%, J6 Insurer Tactic 15%, J7 Persuasive Coherence 10%). Calibration anchors, cost model ($0.014/call, $0.10/letter, $300/20-day ceiling), κ ≥ 0.6 gate, anti-pattern checklist included.
- ✅ **PRD §7 / §8 / §15.2 / §15.3 reconciled** with rubric v2 (hard-gate PASS rates as SC2/SC3, per-dimension regression gating, zero-tolerance auto-rollback on hard-gate FAIL).
- ✅ **10 agent prompts rewritten** as full LLM system prompts (persona + domain context + tool-use + CoT + output schema + few-shot + guardrails). Interface contract preserved as docstring section.
- ✅ **Day 1–20 implementation plan** generated via `implementation-plan` skill — [`docs/plans/2026-05-27-aegis-implementation-plan.md`](../plans/2026-05-27-aegis-implementation-plan.md) + companion flat task list. 4 phases, 67 tasks, 11 risks, full PRD-ID traceability. A1–A5 + Day 10 + Day 14/15 gates explicitly scheduled.
- ✅ **Autonomy Ladder thresholds finalized** via `brainstorming` skill (Moderate Scale + Aggressive Master), logged in `decision-log.md`.
- ✅ **Product Soul rewritten** via `product-soul` skill with anti-positioning, values hierarchy, and specific hypotheses.
- ✅ **Project Constitution established** via `project-constitution` skill — `docs/constitution.md` (v1) sets 7 non-negotiable engineering invariants (testing, security, performance, etc.).
- ✅ **Feature Specs written** via `feature-spec` skill for Part A (MVP) and Part B (Swarm). Both are in Draft status pending clarification review.

### Session 6 (Execution)
- ✅ MVP benchmark dataset size cut from 12-cases to 4-cases across all spec and plan documents.
- ✅ Phase 0 setup fully complete: GCP APIs enabled, `PHOENIX_API_KEY` stored in `.env`, `.pre-commit-config.yaml` established for PHI/secret checking.
- ✅ Tooling installed: `uv`, `google-agents-cli` (with 7 ADK skills via Node).
- ✅ **Backend scaffolded:** Task T1.1 done. Created standard ADK FastAPI app using `agents-cli create -a adk`, added custom `/health` endpoint (returns `{"ok":true}`).
- ⏸️ **Frontend scaffold:** Paused by PM. No Next.js app generated yet.
- ✅ **Memory closed:** Session 6 handoff finalised; current-state updated.
- ✅ **A4 spike:** Verified MCP client connects successfully and lists Phoenix trace tools.

### Session 7 (Frontend design system + scaffold — T1.2 done)
- ✅ **frontend-design skill chain run end-to-end** for the first time. Outputs in `.design/aegis/`.
- ✅ **Archetype locked** via `design-archetype` skill — premium-consumer (health-shaded), feels-like One Medical × Headspace, with Calm motion + Apple Health restraint. See `.design/aegis/ARCHETYPE.md`.
- ✅ **Design tokens generated** via `design-tokens-craft` skill — warm-paper neutrals, sage accent, no Tailwind defaults, oklch source-of-truth, hand-set dark mode, motion budget 240–520ms with Calm easing. CSS + TS in `.design/aegis/` and copied to `frontend/src/styles/tokens.{css,ts}`. Banned-defaults audit clean. See `.design/aegis/TOKENS.md`.
- ✅ **Icon strategy locked** via `icon-craft` — mixed: tuned Lucide subset (functional) + 8 bespoke SVGs (signature surfaces). Tuning rules + bespoke inventory in `.design/aegis/ICONS.md`. The 8 bespoke SVGs are drawn during T1.3+; tuning wrapper at `frontend/src/icons/lucide.tsx` is shipped.
- ✅ **T1.2 Next.js scaffolded** (`pnpm`, Next 16.2.6, React 19, Tailwind v4, App Router, src dir, TS strict). Hero page renders with serif display + Inter body, sage signature dot, hairline rules, no exclamation marks, full disclaimer. `pnpm build`, `pnpm lint`, and `pnpm dev` (HTTP 200) all green.
- ✅ Frontend `AGENTS.md` rewritten to merge Next.js 16 version-specific notice + design-system handoff section.
- ✅ Skill outputs ledger and current-state updated.

### Session 8 (Dev scripts + Vertex AI config)
- ✅ **Dev launcher scripts finished** — `scripts/dev.sh` + `scripts/dev.ps1`. Colored prefixes, .env loading (skip empty values), tool checks, 30s readiness probe, graceful shutdown.
- ✅ **ADC configured** — `gcloud auth application-default login` completed.
- ✅ **Vertex AI (Gemini Enterprise Agent Platform) configured** — backend uses `gemini-3.1-pro-preview` via ADC, location `global`. No API key needed.
- ✅ **`backend/WINDOWS_SETUP.md`** updated with ADC auth section and Vertex AI env vars.
- ✅ **Full end-to-end verified** — `./scripts/dev.sh` starts both services, health check passes.

### Session 9 (Dataset Generation & Eval Architecture - T2.4 Done)
- ✅ **10 Train and 10 Test synthetic cases drafted** for MVP Part A (T2.4 done).
- ✅ **Gumloop 8-agent case evaluation swarm designed** — prompts and architecture documented in `gumloop/`.
- ✅ **Case dataset lifecycle restructured** into strict `drafts/` -> `approved/` folders.
- ✅ **AlphaEval 2026 compliance enforced** — Gumloop & manual prompts updated to use strict 1/3/5 anchor scoring and binary hard gates for LLM Tells / Contradictions.
- ✅ **Manual Evaluation Prompts created** for ChatGPT and Perplexity (Mega-Prompt spot-check mode) with JSON schema output.

### Session 9 (Concurrent — Phoenix telemetry + A4 gate)
- ✅ **T1.3 Phoenix telemetry wired** — traces actively appearing in Phoenix under project `aegis-hackathon` via `openinference-instrumentation-google-adk`.
- ✅ **T1.4 A4 spike pt.1 complete** — MCP query successfully round-tripped and fetched trace data.
- ✅ **T1.5 J1 conflict resolved** — Phoenix is primary; agents-cli observability skill skipped.
- ✅ **T2.1 A4 spike pt.2 complete** — 20 MCP queries, 20/20 successes, p50=1.24s, p95=2.52s. **A4 GATE PASSED.** Phoenix MCP is a load-bearing dependency.
- ✅ **A4 go/no-go decision logged** in `decision-log.md`.

### Session 10 (Concurrent — Case Generator Swarm)
- ✅ **`backend/app/case_generator/` swarm built** — 4 producers + 19 per-stage critics (16 LLM, 3 deterministic) + safety + schema validator + writer.
- ✅ **21 versioned prompt templates** in `backend/app/case_generator/prompts/`.
- ✅ **CLI** `uv run python -m app.case_generator.cli --count N --split {train|test} --seed N --start-index N --dry-run -v`.
- ✅ **Smoke test** produced 1 valid case: `eval/cases/drafts/part-a/test/case_01_aetna_priorauth.json` (Aetna / Prior Auth / behavioral_health / missing_peer_to_peer / TMS for treatment-resistant OCD). All 19 critic verdicts captured in provenance.
- ✅ **Configs externalised**: `eval/diversity_matrix.json`, `eval/banned_topics.json`, `eval/case_schema.json`.
- ✅ **PM course corrections applied**: (1) Drafter+critic both Gemini — need different-family critics (G1: Claude-on-Vertex), (2) Harness Task tool can replace custom file-queue (G2: harness orchestration), (3) No Phoenix tracing needed for offline generation.
- ✅ **Plan for next session**: `docs/plans/2026-05-28-case-generator-harness-claude-plan.md` — G1 (Claude-on-Vertex critic, highest priority), G2 (harness-Task path, optional), G3 (keep Vertex-Python path).

### Session 11 (Demo Capture Planning + Combined Handoff)
- ✅ **Rolling demo capture plan established** — `docs/demo/rolling-capture-checklist.md` with PM-friendly step-by-step instructions for each capture point.
- ✅ **Implementation plan updated** with capture tasks at Days 3, 5, 7, 10, 14, 17.
- ✅ **PM question answered**: Yes, the UX must show the simulator outcome (APPROVE/DENY) — per FR8 and FR10, this is a core demo element. The flip from DENY to APPROVE is one of the most compelling visual moments.
- ✅ **Combined handoff** from 3 concurrent sessions written.

### Session 12 (Execution - aegis_v1 ADK agent)
- Done: **T3.3/T3.4**. `backend/app/agent.py` now exposes `aegis_v1` with the 7 MVP tools: `case_parser`, `corpus_retrieval`, `phoenix_mcp_lookup`, `playbook_loader`, `drafter`, `self_check`, `simulator`.
- Added Pydantic schemas and deterministic tool pipeline under `backend/app/aegis_v1/`: `schemas.py`, `tools.py`, `pipeline.py`.
- Strict JSON path: ADK `output_schema=AppealPackage` plus `response_mime_type="application/json"`.
- Local smoke produced structured `AppealPackage`: Cigna med-necessity, 3 corpus citations, self-check PASS, simulator score 9/10 -> DENY. This preserves the planned weak-v1 demo arc.
- Verification: `pytest tests/unit` -> 8 passed; ADK canonical tools resolve to 7 `FunctionTool`s. Ruff could not run because it is not installed in the backend venv.

### Session 13 (Realistic Imperfection & AlphaEval Gap Fixes)
- ✅ Overhauled architecture to support "Realistic Imperfection" for generated synthetic denial cases.
- ✅ Implemented schema `denial_pattern_sources`, `appeal_difficulty`, and `evaluator_disagreements`.
- ✅ Created `eval/denial_patterns.json` as the source-of-truth corpus for real-world insurer flaws.
- ✅ Recalibrated generator pipeline (`RealisticFlawInjector` added, critics refactored for AlphaEval compliance).
- ✅ Built out 16-agent Gumloop swarm (Tier 1 Hard Gates + Tier 2 Realism/Logical Critics + Meta-Evaluators).
- ✅ Rewrote `gumloop/architecture.md` to document the new multi-tier architecture.
- ⏸️ Generation trial paused due to missing `GEMINI_API_KEY`.


### Session 15 (Generation Pipeline P5)
- ✅ Added `StylisticDiversifier` (P5) to the generation pipeline to ensure clinical/procedural diversity.
- ✅ Re-architected pipeline to separate factual diversity (Orchestrator), logic flaws (P4), and stylistic noise (P5).
- ✅ Added strict safety rules to P5 to preserve P4's injected flaws and timestamps.

### Session 14 (User/Manual updates)
- ✅ Expanded `eval/denial_patterns.json` with a new `category` field and 19 new patterns across 5 categories.
- ✅ Added category 6 `algorithmic_ai_denial` patterns (3 patterns) to `eval/denial_patterns.json`.
- ✅ Simplified category 6 to 3 single-filer-detectable proxy patterns.

### Session 16 & 17 (Documentation Sweep & Multi-Service Topology)
- ✅ Codified the "Weak-v1" Demo arc rule explicitly into PRD Section 15.5.
- ✅ Added "Case Generation Pipeline (Offline Tooling)" Section 8 to the Architecture spec.
- ✅ Documented pipeline mechanics: Realistic Imperfection, Analysis-First rules, Split Scoring, Gumloop Arbiter REVISE logic, and Diversity constraints.
- ✅ Formalised the "Anti-Cheating Firewall" logic for the SkillOpt textual gradient descent structure.
- ✅ Implemented 3-service backend topology (`aegis-v1-api` on 8001, `aegis-swarm-api` on 8002) in `scripts/dev.sh` and created `ADR-006`.

## What's blocked
- **Arize Cloud Auth** — A4 MCP connection works, but Arize auth (`PHOENIX_CLIENT_HEADERS` or API key permissions) blocks actual trace retrieval from the MCP server. Workaround: direct Phoenix SDK calls work; MCP is functional for ADK tool integration (T2.1 proved this with 20/20 successes).

## Active decisions (top items)
- Codename: **Aegis**
- Stack: Google ADK + Gemini 3.1 Pro (Vertex AI / Agent Platform, via ADC) + Phoenix Cloud + Phoenix MCP + Next.js + Python FastAPI + Cloud Run + `google-agents-cli`
- License: Apache 2.0
- Autonomy ladder: 3-stage (Apprentice → Journeyman → Master) — thresholds TBD on Day 5 after judge calibration κ measured
- 12-agent Part B with 4 hard revisit triggers ([ADR-004](../adr/))
- Eval: 7-judge panel, 2 hard gates + 5 weighted, κ ≥ 0.6, per-dim regression gating ([rubric v2](../evals/2026-05-27-aegis-appeal-rubric.md))
- Phase 0 PM-gated; Phase 1 starts Day 1 once PM approves setup
- MVP Day 7 = safety net; Full Plan Day 20 = win condition

## Active risks (top)
- **R-PLAN-1** A4 Phoenix MCP + ADK integration breaks → Day 1–2 spike isolates this; fallback documented
- **R-PLAN-2** A1 eval signal too noisy → Day 5 gate; fallback = recalibrate or kill loop pitch
- **R-PLAN-3** A3 cases read as toy → Day 3 reader test; fallback = real anonymised public letters
- **R-PLAN-5** A5 Coordinator autonomy fails → Day 10 gate; fallback = stay on human-approved loop (MVP-style)
- Time pressure: 20-day window has not started; Phase 0 must clear quickly

## Source of truth files

| Artifact | File |
|---|---|
| Product spec | [`docs/prd/PRD.md`](../prd/PRD.md) (v4) |
| Architecture | [`docs/architecture/2026-05-27-aegis-arch.md`](../architecture/2026-05-27-aegis-arch.md) |
| Eval rubric | [`docs/evals/2026-05-27-aegis-appeal-rubric.md`](../evals/2026-05-27-aegis-appeal-rubric.md) (v2) |
| Eval pipeline | [`docs/evals/2026-05-27-aegis-eval-pipeline.md`](../evals/2026-05-27-aegis-eval-pipeline.md) |
| Judges spec | [`docs/evals/2026-05-27-aegis-judges.md`](../evals/2026-05-27-aegis-judges.md) |
| Agent prompts (v1) | Part A: [`backend/app/aegis_v1/prompts/`](../../backend/app/aegis_v1/prompts/) · Part B swarm: [`backend/app/aegis_swarm/prompts/`](../../backend/app/aegis_swarm/prompts/) (legacy `backend/src/prompts/` retired in Session 22) |
| Implementation plan | [`docs/plans/2026-05-27-aegis-implementation-plan.md`](../plans/2026-05-27-aegis-implementation-plan.md) |
| Agent-pickable tasks | [`docs/plans/2026-05-27-aegis-implementation-tasks.md`](../plans/2026-05-27-aegis-implementation-tasks.md) |
| ADRs | [`docs/adr/ADR-001..005`](../adr/) |
| Assumption map | [`docs/research/assumption-map.md`](../research/assumption-map.md) |
| Design brief | [`docs/design-brief.md`](../design-brief.md) |
| Impact stats | [`docs/research/impact-stats.md`](../research/impact-stats.md) |
| Product soul | [`docs/product-soul.md`](../product-soul.md) |
| Constitution | [`docs/constitution.md`](../constitution.md) |
| Feature Spec: Part A | [`docs/specs/2026-05-27-aegis-part-a-mvp-feature-spec.md`](../specs/2026-05-27-aegis-part-a-mvp-feature-spec.md) |
| Feature Spec: Part B | [`docs/specs/2026-05-27-aegis-part-b-swarm-feature-spec.md`](../specs/2026-05-27-aegis-part-b-swarm-feature-spec.md) |
| Autonomy Ladder Design | [`docs/specs/2026-05-27-autonomy-ladder-design.md`](../specs/2026-05-27-autonomy-ladder-design.md) |
| Frontend archetype | [`.design/aegis/ARCHETYPE.md`](../../.design/aegis/ARCHETYPE.md) |
| Frontend tokens (rationale) | [`.design/aegis/TOKENS.md`](../../.design/aegis/TOKENS.md) |
| Frontend tokens (runtime) | [`frontend/src/styles/tokens.css`](../../frontend/src/styles/tokens.css) + `tokens.ts` |
| Frontend icons strategy | [`.design/aegis/ICONS.md`](../../.design/aegis/ICONS.md) |
| Open questions | [`docs/open-questions.md`](../open-questions.md) |
| Agent rules | [`AGENTS.md`](../../AGENTS.md) + `frontend/AGENTS.md` + `backend/AGENTS.md` |
| Decision log | [`docs/memory/decision-log.md`](decision-log.md) |
| TODO + handoff | [`docs/memory/agent-handoffs.md`](agent-handoffs.md) |
| Demo capture checklist | [`docs/demo/rolling-capture-checklist.md`](../demo/rolling-capture-checklist.md) |
| Phoenix shotlist (A2) | [`docs/demo/phoenix-shotlist.md`](../demo/phoenix-shotlist.md) |
| Case generator plan (G1-G3) | [`docs/plans/2026-05-28-case-generator-harness-claude-plan.md`](../plans/2026-05-28-case-generator-harness-claude-plan.md) |
| Gumloop evaluator architecture | [`gumloop/architecture.md`](../../gumloop/architecture.md) |
| Gumloop evaluator prompts | [`gumloop/prompts/01-08_*.txt`](../../gumloop/prompts/) |
| Case generator code | [`backend/app/case_generator/`](../../backend/app/case_generator/) |
| Case generator prompts | [`backend/app/case_generator/prompts/`](../../backend/app/case_generator/prompts/) |
| Eval configs | [`eval/{diversity_matrix,banned_topics,case_schema}.json`](../../eval/) |
| Part A judge panel spec | [`docs/specs/2026-05-29-part-a-judge-panel-feature-spec.md`](../specs/2026-05-29-part-a-judge-panel-feature-spec.md) + [`docs/evals/2026-05-29-part-a-judge-panel-spec.md`](../evals/2026-05-29-part-a-judge-panel-spec.md) |
| Part A judge panel code | [`backend/app/evals/part_a/`](../../backend/app/evals/part_a/) |

### Session 18 (Critical Audit — Droid)
- ✅ Full cross-repo audit of all uncommitted changes from Sessions 15–17.
- ✅ Identified 16 inconsistencies (1 syntax-breaking bug, 4 high, 6 medium, 3 low, 2 deferred).
- ✅ Confirmed architectural direction is sound; inconsistencies are execution-layer cleanup, not design corrections.
- ⚠️ **dev.sh is broken** — duplicate C_RESET + orphaned else/fi block causes bash syntax error. Must fix before any dev work.
- ⚠️ **9+ files reference deleted `fast_api_app.py` and port 8000** — stale references across tests, Dockerfile, docs, scripts.
- ⚠️ **Phoenix project name split not propagated** — code/docs still say `aegis-hackathon`; dev.sh uses `aegis-baseline`/`aegis-swarm` per ADR-006.

### Session 19 (Part A Judge Panel)
- ✅ Approved and documented the Part A judge panel firewall: Aegis v1 gets a `StudentCasePacket`; judges get a teacher-only grading packet with provenance, expected appeal vectors, and exploitable weaknesses.
- ✅ Implemented local judge-panel package at `backend/app/evals/part_a/` with Pydantic schemas, teacher-packet builder, deterministic gates, offline heuristic judge client, Gemini-swappable client, aggregator, and CLI.
- ✅ Added seven judge prompt templates under `eval/judges/part_a/`, including J6 `Appeal-Vector Capture` to grade whether Aegis finds the synthetic case's embedded flaw.
- ✅ Added focused unit tests: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/evals/test_part_a_judge_panel.py -q` → 6 passed.
- ⚠️ Same-model judging is accepted: Gemini 3.1 Pro will judge Gemini 3.1 Pro drafts; mitigations are deterministic gates, single-dimension prompts, evidence-first scoring, quote validation, calibration, and human spot checks.
- ⚠️ Broad `tests/unit` remains blocked by pre-existing stale import `from app.agent` in `tests/unit/agent/test_aegis_v1_agent.py` (Session 18 issue family).

## Learning loop design (Session 21, 2026-05-30)
The self-improvement loop has been designed end-to-end (brainstorming) →
[`docs/specs/2026-05-30-learning-coordinator-design.md`](../specs/2026-05-30-learning-coordinator-design.md).
Key reframe (as of Session 21): the drafter was deterministic templating (no evolvable surface) and the
judge panel's signal never reached Phoenix — both addressed by substrate fixes F1–F7 before the
Learning Coordinator itself. **Plan 1 (substrate F1–F7) is written:**
[`docs/plans/2026-05-30-learning-loop-substrate-plan.md`](../plans/2026-05-30-learning-loop-substrate-plan.md)
— 9 TDD tasks, fully offline-testable. **Next: execute Plan 1**, then write Plan 2 (the Learning
Coordinator itself: per-dimension specialists + experiment harness + HITL gate). See the
orientation map ([`orientation-map.md`](orientation-map.md)) for the built-vs-designed picture and
`graphify-out/` for a queryable repo graph.

## Learning loop substrate BUILT (Session 22, 2026-05-30)
Plan 1 (substrate F1–F7) was executed end-to-end, subagent-driven, fully offline (no GCP). Now in code:
- **Drafter is LLM-driven** via an injected `DrafterLLMClient` (`StubDrafterClient` offline /
  `GeminiDrafterClient` prod) behind deterministic guardrails — the fixed template is gone.
- **Student is 6 tools**; the **Outcome Simulator** is relocated out of the agent. It now runs in the
  orchestration layer (`aegis_v1/appeal_orchestrator.run_appeal_with_outcome`, exposed at
  `POST /v1/appeal`) and in the eval harness (`evals/part_a/evaluated_run.run_evaluated_case`), via an
  injectable `SimulatorClient` (stub / `GeminiSimulatorClient`). `AppealPackage` no longer carries
  `simulator_result`.
- **`run_evaluated_case`** joins Student → record trace → judges (+ optional simulator) → writes a
  **firewall-safe laundered** eval signal to a `PhoenixRecorder` (`InMemoryPhoenixRecorder` offline /
  `OtelPhoenixRecorder` prod).
- **Prompts colocated** per backend; `playbooks/` created with a convention doc.
- **Tests:** 35 offline unit tests green (`tests/unit/{aegis_v1,evals,agent}`); a GCP-ready live
  integration test (`tests/integration/test_live_appeal.py`) auto-skips without ADC.

**Open (Plan 2):** the Learning Coordinator itself; live Phoenix MCP *reads* (`phoenix_mcp_lookup`
still a stub). (The Outcome Simulator's two-step transparent scoring is now **built** — see Session 23
below.) See [learnings.md](learnings.md) Session 22.

## Outcome Simulator two-step transparent scoring BUILT (Session 23, 2026-05-31)
The simulator is now a transparent two-step function, executed subagent-driven over the 6-task plan
([`docs/plans/2026-05-31-outcome-simulator-two-step-plan.md`](../plans/2026-05-31-outcome-simulator-two-step-plan.md);
spec [`docs/specs/2026-05-30-outcome-simulator-two-step-design.md`](../specs/2026-05-30-outcome-simulator-two-step-design.md)).
The `threshold=10` hack and the old single-LLM-call `simulate` path are deleted. Now in code:
- **LLM does fuzzy judgment only** (`SimulatorClient.assess` → `FeatureAssessment`): critique-first, then
  per-feature 1/3/5 anchors + evidence. The schema/prompt forbid it emitting a score or verdict (INV-S3).
  Inputs are insurer-visible only — `denial_text`/`clinical_context`/`appeal_letter`, no answer key (INV-S4).
- **Deterministic scorer** (`aegis_v1/simulator_scoring.score_outcome`): pure function of (LLM anchors,
  published `eval/simulator_rules.json`). score = Σ(weight·anchor)/max_anchor; APPROVE iff score ≥ 0.70
  AND every must-have feature ≥ anchor 3 (must-have veto). Emits `feature_scores` + `gaps` + `critique`
  for auditability (INV-S2). `eval/simulator_rules.json` is now the published rubric (6 features, weights
  sum to 1.0; `rebuts_specific_flaw` is the must-have) — its old unused gate content was overwritten.
- **`SimulatorResult`** now carries a float `score` (0.0–1.0), float `threshold` (0.70), `feature_scores`,
  `gaps`, `critique`. `tools.simulator()` composes `assess → load_simulator_rules → score_outcome`; it
  stays out of the Student's tool list (INV-S1) and feeds `POST /v1/appeal` + `run_evaluated_case` unchanged.
- **Math (test-asserted):** uniform(1)→0.2 DENY, uniform(5)→1.0 APPROVE, weak-v1→0.38 DENY,
  must-have-veto-despite-0.84→DENY. Weights/threshold are principled, not tuned to the demo arc (INV-S5).
- **Tests:** offline acceptance green — `tests/unit/{aegis_v1,evals,agent}` 48 passed; the GCP-ready
  `tests/integration/test_live_appeal.py` auto-skips (2 skipped) without ADC. Commits `b380469..89f737f`.
- **Deferred:** per-insurer rule sets; live-Gemini calibration of the weights/threshold against the
  benchmark (verify, never hand-tune); any Learning-Coordinator evolution of the rubric (Plan 2).
- **Live-agent bug fixed (was pre-existing, commit `7dec151`):** the *drafter* ADK tool exposed a DI
  `client: "DrafterLLMClient | None"` param whose type is imported lazily inside the body; with
  `from __future__ import annotations`, ADK's tool-schema builder called `get_type_hints()` on that
  forward ref at agent-run time and raised `NameError: DrafterLLMClient`, breaking the live `aegis_v1`
  agent + e2e server (offline unit tests never hit it). Fix: split into a clean ADK-facing `drafter()`
  wrapper (no DI seam in the model's tool schema) + an injectable `draft_appeal(..., client=None)` core
  (pipeline/tests use the core). Added regression tests (every registered tool's hints must resolve; no
  registered tool may expose a `client` param) and gave the live ADK-agent/server-e2e integration tests
  the same ADC skip-guard as `test_live_appeal.py`. Now: unit **51 passed**, `tests/integration` **6
  skipped** cleanly offline. The simulator was never affected (not a registered ADK tool, INV-S1).

## Learning Coordinator (Plan 2) — offline machinery BUILT (Session 24, 2026-05-31)
Phase 1 of the v2 plan is done: the full GEPA-faithful Learning Coordinator now exists as the offline
package `backend/app/learning/`, executed subagent-driven over the 12-task plan
([`docs/plans/2026-05-31-learning-coordinator-offline-plan.md`](../plans/2026-05-31-learning-coordinator-offline-plan.md);
spec [`docs/specs/2026-05-31-learning-coordinator-v2-gepa-design.md`](../specs/2026-05-31-learning-coordinator-v2-gepa-design.md)).
All 12 tasks green; commits `9f048f7..53f1eaf`. Now in code:
- **`models.py`** — `Component`/`Candidate`/`ScoredRun`/`DimensionSignal`/`ExperimentResult`/`PromotionProposal`
  + `composite_score` (weighted, hard-gated; all-5→1.0, all-1→0.2, gate-fail→0.0). Rubric weights:
  grounding .30, appeal_vector_capture .25, case_specific_clinical_rebuttal .20, evidence_completeness .15,
  persuasive_coherence .10.
- **`store.py`** — `PhoenixLearningStore` Protocol (the ONLY contract to Phoenix, INV-1) +
  `InMemoryPhoenixLearningStore` fake (reads back recorded runs, versions components, `register_promotion`
  appends only changed versions).
- **`signal.py`** — `acquire_signal()` reads the gradient FROM Phoenix, picks the weakest rubric dimension,
  collects **laundered** notes; returns `None` when Phoenix has no signal (INV-1 halt). `FORBIDDEN_FIELDS`
  firewall (INV-2) strips answer-key keys — **including on the `failing_cases` runs that feed the reflection
  minibatch** (a genuine plan bug a subagent caught and we fixed in `dab6dc0`; defence in depth).
- **`reflection_client.py`** — `ReflectionClient` Protocol + `StubReflectionClient` (deterministic
  constructive edit, tags target dimension) + `Gemini`/`Anthropic` backends (cloud SDK imports method-local,
  construction-only tested) + critique-first `build_reflection_prompt` (firewall holds in the prompt too).
- **`selection.py`/`mutation.py`/`merge.py`/`gates.py`** — pure GEPA mechanics: instance-wise Pareto
  frontier + coverage select + round-robin `select_component`; single-component `reflective_mutate` with
  lineage+credit (V2-INV-2); `system_aware_merge` of complementary lineages (None on conflict);
  `evaluate_vetoes` (held-out regression, safety/hard-gate, `simulator_approve_but_judges_fail` (INV-3),
  diff>200 tokens).
- **`experiment.py`** — `StubExperimentRunner` (deterministic monotone scorer — targeted dims bump 1→3→5,
  gives the loop a real gradient) + `LiveExperimentRunner` (real drafter+judge, construction-safe, run() is
  live-only). **`coordinator.py`** — `LearningCoordinator.optimize()` (Phoenix-signal probe → seed → reflect/
  select/merge rounds → `PromotionProposal`) + HITL `promote()`. **`efficacy_harness.py`** — `run_efficacy()`
  reports held-out lift for any injected backend; refuses to measure on the train split (V2-INV-3).
- **Tests:** `tests/unit/learning/*` **35 passed**; full `tests/unit` suite **86 passed** offline.
  Build-breaking invariant tests: INV-1 (no-signal → `optimize()` returns None), INV-2 (firewall in signal
  + prompt), V2-INV-2 (one component/child), V2-INV-3 (held-out-only). No module-top cloud imports.
- **Deferred to the companion (GCP/live) plan:** real `PhoenixLearningStore` over MCP/SDK; the
  `judge_client.score(...)` adapter over the Part-A panel; real Gemini/Anthropic drafter+judge+reflection;
  the stagnation from-scratch restart (needs re-recorded signal between promotions); measured +20% lift,
  κ≥0.6 calibration, MCP-off counterfactual, DENY→APPROVE demo capture.
- **Phase 2 (DONE, Session 24) — real efficacy measured.** Assistant-orchestrated manual GEPA run with
  the Claude session as the drafter/judge/reflection intelligence (no API keys) over the real synthetic
  cases. Optimized the Student drafter prompt for its weakest *promptable* dimension
  (`appeal_vector_capture`): **held-out composite 0.73 → 0.88 = +0.15 abs / +20.5% rel**, no vetoes,
  promotable — meeting the v1 §12 target on cases the reflection never saw, INV-2 firewall intact.
  `drafter_v1.md → drafter_v2.md` (+131-token focused reflection: "confront the denial's strongest
  stated ground head-on" + "audit for missing procedural/appeal-rights disclosures"); promoted in
  `tools.py` (now loads `drafter_v2`). Run captured under `eval/efficacy_runs/2026-05-31/`
  (inputs/drafts/judgments/reflections/result.json + prep/score scripts) and locked as an offline
  replay regression (`backend/tests/unit/learning/test_efficacy_run_fixture.py`, 4 tests). Full unit
  suite **90 passed**. Evidence doc + honest caveats (small N, single round, Claude-judges-Claude,
  grounding corpus-bound) in [`docs/evals/2026-05-31-coordinator-efficacy-run.md`](../evals/2026-05-31-coordinator-efficacy-run.md). Commit `2c21d33`.
  **Deferred:** round 2+ (next promptable dimension) + full 10/10 split; the Gemini-drafts + independent-judge
  + κ≥0.6 re-run lands in the companion GCP plan (these prompts are its starting point).
- **Next work planned (Session 24, ready to execute).** Two plans written + a Session-25 handoff:
  - **Tier 2 (offline, now):** [`docs/plans/2026-05-31-learning-efficacy-tier2-offline-plan.md`](../plans/2026-05-31-learning-efficacy-tier2-offline-plan.md) — extract a tested `efficacy_io` module, run efficacy round 2 on the full 10/10 split, A/B the reflection meta-prompt.
  - **Tier 1 (live, credential-gated):** [`docs/plans/2026-05-31-learning-coordinator-live-gcp-companion-plan.md`](../plans/2026-05-31-learning-coordinator-live-gcp-companion-plan.md) — the submission thesis: live `phoenix_mcp_lookup` (T4.1), `LivePhoenixLearningStore`, live Gemini+Phoenix coordinator, the **MCP-off counterfactual** demo, κ≥0.6 judge calibration. Offline cores are TDD'd against fixtures; network calls gated behind `_creds_available()`.
  - Runbook + order (Tier 2 first) + the MCP-auth critical path are in [`session-25-execution-handoff.md`](session-25-execution-handoff.md).

## Next recommended action

**Updated 2026-05-28 (Session 18):** Before any feature work, the next agent must resolve the inconsistencies identified in the audit. PM wants to review each issue individually — see Session 18 handoff in `agent-handoffs.md` for the full 16-item table with recommendations.

**Priority order:**
1. **Fix dev.sh syntax bug** (issue #1) — blocks all development. Likely OK to fix without PM debate since it's a plain bug.
2. **PM review of issues #2–#16** — go through each one with PM before fixing.
3. **Phoenix project name decision** (issues #10–#12) — blocks T4.1 (live MCP wiring).
4. **Gemini/cloud calibration for Part A judge panel** — once GCP is configured, run the seven judge prompts against calibration examples; offline heuristic scores are diagnostic only.
5. **T3.5 demo capture** — time-sensitive; cannot be recreated after prompt is patched.
6. **T4.1 live Phoenix MCP** — load-bearing demo feature.
7. **G1 critic model revisiting is no longer viable as originally written** if Gemini-only judging remains a hard constraint; use same-model mitigations instead.

**A4 gate is PASSED.** Next hard gates to watch: **A2 (Phoenix UI demo-viability — Day 2)**, **A3 (case credibility — Day 3)**, **A1 (eval signal — Day 5)**.

**Demo capture reminder:** First recording happens on **Day 3** when the v1 agent runs for the first time. See `docs/demo/rolling-capture-checklist.md`.
