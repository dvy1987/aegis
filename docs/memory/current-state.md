# Current State — Aegis

**Updated:** 2026-05-27 (Session 5 — close)
**Phase:** **Planning complete.** All Phase 0 / Phase 1 artifacts (PRD v4, architecture spec, eval rubric v2, eval pipeline, agent prompts v1, Day 1–20 implementation plan + task list) are aligned and committed. **Ready for Phase 0 execution pending PM sign-off on GCP + Phoenix Cloud setup.** No application code exists yet.

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
- ✅ **Memory closed:** Session 5 handoff finalised; decision-log appended with new entries; skill-outputs ledger updated.

## What's blocked
- **Phase 0 execution (GCP + Phoenix + repo + agents-cli setup)** — gated on PM sign-off per Session 5 instruction. No `gcloud` runs, no Phoenix account creation, no remote push without PM confirmation.

## Active decisions (top items)
- Codename: **Aegis**
- Stack: Google ADK + Gemini 3 + Phoenix Cloud + Phoenix MCP + Next.js + Python FastAPI + Cloud Run + `google-agents-cli`
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
| Agent prompts (v1) | [`backend/src/prompts/*_v1.md`](../../backend/src/prompts/) |
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
| Open questions | [`docs/open-questions.md`](../open-questions.md) |
| Agent rules | [`AGENTS.md`](../../AGENTS.md) + `frontend/AGENTS.md` + `backend/AGENTS.md` |
| Decision log | [`docs/memory/decision-log.md`](decision-log.md) |
| TODO + handoff | [`docs/memory/agent-handoffs.md`](agent-handoffs.md) |

## Next recommended action

**Get PM sign-off on Phase 0**, then execute Phase 0 tasks T0.1–T0.6 (open-questions sweep + GCP + Phoenix Cloud + `git push` + `google-agents-cli` setup + pre-commit hook). Once Phase 0 is green, Day 1 starts the parallel work streams: backend scaffold (T1.1), frontend scaffold (T1.2), Phoenix instrumentation (T1.3), Phoenix MCP toy roundtrip (T1.4 — the A4 spike).

Hard gate to watch first: **A4 (Day 2 EOD)** — Phoenix MCP + ADK integration go/no-go. If FAIL, escalate to PM with fallback options before continuing.
