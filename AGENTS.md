# Aegis — Agent Rules

Read this first. Then in order: `docs/memory/MEMORY-ROUTING.md` → `docs/prd/PRD.md` → `docs/design-brief.md` → `docs/open-questions.md`.

## What this project is

**Aegis** is a self-improving multi-agent system that helps people draft US health-insurance appeal letters. Hackathon submission for the Google Cloud Rapid Agent Hackathon — Arize partner track ($5K prize). Built over 20 days by a solo PM (non-technical) using Amp + skills.

The PRD has two nested parts: **Part A MVP (Days 1–7)** = single agent + 12-case benchmark, shippable as a safety-net submission; **Part B Full Plan (Days 8–20)** = 12-agent swarm + autonomous learning loop + 100-case benchmark, the win-condition. Build MVP first; layer Full Plan on top.

## User Context

The product owner is a Product Manager with minimal coding experience, building primarily with Amp + Cursor. They are strong on product, strategy, copy, and design judgment. They defer to agents on architecture, code style, testing, DevOps, and deployment — but every product-affecting or architecture-affecting decision must be surfaced before it is made.

## Working with the PM (applies to every agent in this repo)

1. **Explain technical decisions in plain language BEFORE making them.** Never silently pick a database, framework, deployment pattern, or library. Surface the decision → plain-English summary → why it matters → 2–3 options with tradeoffs → recommendation → ask.
2. **When facing architecture or design tradeoffs, ask — don't assume.** Defaults are not silent decisions.
3. **At key build stages, proactively collect input on product-affecting decisions.** Before starting a new feature, before deploying, before committing to a vendor or paid service, before changing the agent's autonomy level — pause and ask.
4. **Never assume understanding of Docker, GCP, deployment, APIs, OAuth, environment variables, CI/CD, observability concepts, or other backend topics.** Explain plainly when relevant, then ask.
5. **One decision at a time when possible.** Bundling 5 unrelated questions is overwhelming.
6. **No unilateral scope cuts.** If timeline or technical reality forces scope decisions, escalate with options. Do not silently downscope.

### Code-Wall Escalation Protocol
- Every coding session ends with a working commit + a "what's stuck" note.
- If stuck >4h on the same issue, escalate (oracle, switch tactic) — don't dig.
- If the MVP timeline slips materially, present the PM with options. Don't decide.

### Autonomy boundaries
| Area | Default |
|---|---|
| Product, architecture, copy, design choices | **Ask first.** Surface → explain → ask. |
| New library, vendor, or paid service | **Ask first.** Always. |
| Tests, internal refactors, behaviour-preserving cleanups | **Full autonomy.** Just do it. |
| Code-style choices inside the decided stack, tooling, lint/format | **Full autonomy.** Match existing patterns. |

## Hard Scope Constraints

**MVP (Part A).** Commercial plans · 2 denial types (medical necessity, prior auth) · 3 insurers (Aetna, Cigna, UHC) · 12-case benchmark · manual learning with human approval.

**Full Plan (Part B).** Adds 7 denial types · 10 insurers · 100-case benchmark · 12-agent swarm · autonomous learning loop with hard safety gates + auto-rollback.

**Always out of scope.** Medicare/Medicaid · live filing with insurers · court representation · attorney work product · PHI · mobile app · multi-language · user accounts.

## Safety & Disclosure

- **No PHI** in code, tests, evals, or Phoenix traces. Synthetic composite cases only; provenance in `eval/dataset_card.md`.
- Every user-facing output and demo claim carries: *"Not legal or medical advice. Draft assistance only."*
- **No invented statutes, case law, or policy text.** Citations come only from the controlled local corpus.
- **No "this will win your appeal" claims** in code, UI, demo, README, Devpost.
- **No invocations of violence, vigilantism, or polarizing public events around the insurance industry** in any artifact. The product earns trust by being constructive, not by riding cultural anger. Impact stats come from primary research (KFF, Commonwealth Fund, JAMA, Senate report) and are framed factually.
- **Tone discipline:** see [docs/design-brief.md](docs/design-brief.md) §4. No AI marketing voice, no exclamation marks, no "powered by Gemini" in user UI. Use "person" not "human".

## UX as Co-Equal Product Pillar

UX/design is one of three co-equal must-nail pillars alongside (1) Phoenix MCP load-bearing in the demo and (2) demonstrable self-improvement lift. When a design choice trades polish for speed, the default is *polish* — push schedule, not quality. See [docs/design-brief.md](docs/design-brief.md).

## Tech Stack (fixed)

| Layer | Tool |
|---|---|
| Frontend | Next.js (App Router) + Tailwind + shadcn/ui + framer-motion + Lucide React |
| Backend / agent runtime | Python 3.11 + `uv` + FastAPI + Google ADK |
| Backend dev workflow | `google-agents-cli` (`uvx google-agents-cli setup`) — scaffold, eval, deploy, observability |
| LLM | Gemini 3 (fallback: Gemini 2.5 if unavailable in window) |
| Observability + evals | Arize Phoenix Cloud (free tier) |
| Runtime introspection | `@arizeai/phoenix-mcp` |
| Instrumentation | `openinference-instrumentation-google-adk` |
| Hosting | Google Cloud Run (2 services: frontend + backend) |
| Storage | Local files + GCS JSON for promoted playbooks |
| License | Apache 2.0 |

Per-directory specifics: [frontend/AGENTS.md](frontend/AGENTS.md) · [backend/AGENTS.md](backend/AGENTS.md).

## Build Discipline

- One ADK agent + one offline learning job for Part A. 12-agent swarm only in Part B (Days 8+).
- Day 1: install `google-agents-cli` via `uvx`. Sanity-check that its observability skill doesn't conflict with our Phoenix MCP setup before relying on it.
- Days 1–10 run the 5 critical assumption tests in [docs/research/assumption-map.md](docs/research/assumption-map.md) — A1 eval signal, A2 Phoenix UI demo viability, A3 case credibility, A4 MCP+ADK integration, A5 Learning Coordinator autonomy. If any fail, the pitch is updated downward *before* further commitment.
- Promotion of prompt/playbook changes in Part A requires human approval click in the demo UI. Autonomous learning is allowed in Part B only, with hard safety gates (PRD §15.2) and one-click rollback.
- No vector DB unless absolutely forced — local corpus + Phoenix datasets are sufficient.
- **Part B architecture revisit triggers:** if Day 10 progress shows <50% of swarm agents have credible prompts, OR if Learning Coordinator autonomy (assumption A5) fails by Day 10, escalate to PM with options for a leaner topology. Do not silently downscope.

## Session Lifecycle (mandatory)

**At session start:**
1. Run the `memory-startup` skill.
2. Read the latest entry in `docs/memory/agent-handoffs.md`.
3. Confirm git state (`git status`).
4. State recovered context in 2–4 lines before any action.

**During and at session end:**
- After meaningful changes (PRD edit, ADR added, spec written, feature shipped, decision made) call `memory-capture` / `memory-decision` and update `docs/memory/current-state.md`.
- Before ending, call `memory-handoff` and append to `docs/memory/agent-handoffs.md`.

## Orchestration Map

| Phase | Skills (in order) |
|---|---|
| Strategy & framing | `deep-thinking` · `inversion` · `pre-mortem` · `assumption-mapping` · `product-soul` · `brainstorming` |
| Spec-driven development | `spec-driven-development` → `project-constitution` (/constitution) → `feature-spec` (/specify, /clarify) → `implementation-plan` (/plan) → `problem-to-plan` (/tasks) → `spec-crosscheck` (/analyze) → `test-driven-development` (/implement) |
| Eval design | `eval-output` → `eval-rubric-design` → `eval-judge` → `eval-pipeline` |
| Architecture | `agent-system-architecture` · `agent-builder` · `create-agent-prompt` · `tool-finder` · `architectural-decision-log` |
| Design | `frontend-design` → `design-archetype` → `design-tokens-craft` → `icon-craft` → `design-review` |
| Backend lifecycle (ADK) | `google-agents-cli-workflow` · `google-agents-cli-adk-code` · `google-agents-cli-scaffold` · `google-agents-cli-eval` · `google-agents-cli-deploy` · `google-agents-cli-observability` (installed via `uvx google-agents-cli setup`) |
| Build | `test-driven-development` · `debug-and-fix` · `code-review-crsp` |
| Security (on external content) | `secure-skill` · `secure-skill-content-sanitization` · `secure-skill-repo-ingestion` · `secure-skill-runtime` |
| Memory (every session) | `memory-startup` (start) · `memory-capture` / `memory-decision` (events) · `memory-handoff` (end) |

**Spec-first rule:** when behaviour changes, update the feature-spec in `docs/specs/` first. Never edit code that violates the latest `spec-crosscheck` PASS.

**Skill routing rule:** ADK-specific work (scaffold, eval, deploy, ADK Python API, observability) routes to `google-agents-cli-*` skills. Framework-agnostic process work (TDD, code review, architecture decisions) routes to our existing skills. Deconflict overlaps as they surface.

## Files Agents Must Update When Relevant

- `docs/prd/PRD.md` — only with PM approval (source of truth)
- `docs/architecture.md` — when system shape changes
- `docs/open-questions.md` — close resolved, open new
- `docs/memory/decision-log.md` — when a non-trivial decision is made (`memory-decision`)
- `docs/memory/current-state.md` — at session end if state shifted
- `README.md` — when status milestones change
- `docs/skill-outputs/SKILL-OUTPUTS.md` — ledger of every skill invocation + output file

## Never

- Never commit credentials. Phoenix API key, Google Cloud service account, etc. live in `.env` (gitignored).
- Never put PHI or real patient data in code, tests, evals, or traces.
- Never invent statutes, case law, or insurer policy text.
- Never push to remote without explicit PM instruction.

## Demo Discipline

The hackathon demo is 3 minutes. Every architectural decision is evaluated against *"does this make the 3-minute demo more compelling, more credible, or more rigorous?"* — if not, defer. Phoenix Cloud UI must be visibly on screen ≥60 of the 180 seconds. Hero arc in [docs/prd/PRD.md](docs/prd/PRD.md) §9 (MVP) and §16 (Full Plan).

## Submission Checklist (Devpost)

- [ ] Hosted project URL (Cloud Run)
- [ ] Public GitHub repo with Apache 2.0 license visible in About
- [ ] ~3-minute demo video
- [ ] Devpost submission form complete
- [ ] Track selected: **Arize**

## Quick Links

[PRD](docs/prd/PRD.md) · [Design Brief](docs/design-brief.md) · [Architecture](docs/architecture.md) *(needs Session 2 update)* · [Impact Stats](docs/research/impact-stats.md) · [Assumption Map](docs/research/assumption-map.md) · [Open Questions](docs/open-questions.md) · [Memory Routing](docs/memory/MEMORY-ROUTING.md) · [Hackathon Brief](docs/challenge.md) · [Phoenix docs](https://docs.arize.com/phoenix) · [Phoenix MCP](https://docs.arize.com/phoenix/integrations/mcp/phoenix-mcp-server) · [Google ADK](https://google.github.io/adk-docs/) · [Agents CLI](https://google.github.io/agents-cli/) · [ADK multi-agent patterns](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/) · [Arize hackathon quickstart](https://github.com/Arize-ai/gemini-hackathon)
