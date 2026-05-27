# Current State — Aegis

**Updated:** 2026-05-27 (Session 8 — close)
**Phase:** **Execution — Phase 1.** Phase 0 setup complete. Backend scaffolded with `/health`. Frontend scaffolded with full design system. Dev launcher scripts finished. Vertex AI via ADC configured and verified.

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

## What's blocked
- **Arize Cloud Auth** — A4 spike succeeded connecting to MCP tool, but Arize auth (`PHOENIX_CLIENT_HEADERS` or API key permissions) blocks actual trace retrieval.

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
| Frontend archetype | [`.design/aegis/ARCHETYPE.md`](../../.design/aegis/ARCHETYPE.md) |
| Frontend tokens (rationale) | [`.design/aegis/TOKENS.md`](../../.design/aegis/TOKENS.md) |
| Frontend tokens (runtime) | [`frontend/src/styles/tokens.css`](../../frontend/src/styles/tokens.css) + `tokens.ts` |
| Frontend icons strategy | [`.design/aegis/ICONS.md`](../../.design/aegis/ICONS.md) |
| Open questions | [`docs/open-questions.md`](../open-questions.md) |
| Agent rules | [`AGENTS.md`](../../AGENTS.md) + `frontend/AGENTS.md` + `backend/AGENTS.md` |
| Decision log | [`docs/memory/decision-log.md`](decision-log.md) |
| TODO + handoff | [`docs/memory/agent-handoffs.md`](agent-handoffs.md) |

## Next recommended action

T1.2 (frontend scaffold) and dev infrastructure are **done**. Next: T1.3 (wire Phoenix telemetry, emit one trace) or T1.4 spike pt.2 (20 MCP queries for A4 Day 2 EOD go/no-go). A4 is the most load-bearing for the demo and the soonest hard gate — recommend T1.4 next.

Hard gate to watch first: **A4 (Day 2 EOD)** — Phoenix MCP + ADK integration go/no-go. If FAIL, escalate to PM with fallback options before continuing.
