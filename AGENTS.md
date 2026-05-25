# AGENTS.md — Reverse Project

This file orients AI agents (Amp, Claude Code, Cursor, etc.) working in this repository.

## User Context
The user is a product manager with minimal coding experience. This means:

- Explain technical decisions in plain language before making them
- When facing architecture or design trade-offs, ask the user for input — don't assume
- At key build stages, proactively collect the user's input on decisions that affect the product
- Never assume the user understands Docker, GCP, deployment, APIs, or backend concepts — explain simply when relevant then ask for the decision.
- The user cares deeply about product quality — never cut corners on prompts, evaluation or output

## What this project is

**Aegis** (codename Reverse v2) is a hackathon submission for the Google Cloud Rapid Agent Hackathon, Arize track. It's a self-improving multi-agent system for US health-insurance appeals built on Google ADK + Gemini 3 + Phoenix MCP. See [README.md](README.md), [docs/prd/PRD.md](docs/prd/PRD.md), and [docs/architecture.md](docs/architecture.md).

The PRD has **two nested specifications**:
- **Part A (MVP, Days 1–7)** — single agent, 12-case benchmark, manual learning. **Shippable as standalone submission.**
- **Part B (Full Plan, Days 8–20)** — 12-agent swarm, autonomous learning loop, 100-case benchmark. Builds on Part A.

Build MVP first (Day 7 safety net), layer Full Plan on top.

## Working with the PM (CRITICAL — applies to every agent in this repo)

The product owner is a **Product Manager with minimal coding experience**. Every agent (Amp, Claude Code, Cursor, etc.) working on this repo MUST follow these rules:

1. **Explain technical decisions in plain language BEFORE making them.** Never silently pick a database, framework, deployment pattern, or library. Surface the decision, explain in plain English what it is and what the tradeoffs are, then ask.
2. **When facing architecture or design tradeoffs, ask the PM — don't assume.** "Use Postgres vs SQLite" is a question, not a default.
3. **At key build stages, proactively collect input on product-affecting decisions.** Before starting a new feature, before deploying, before committing to a vendor or paid service, before changing the agent's autonomy level — pause and ask.
4. **Never assume understanding of Docker, GCP, deployment, APIs, OAuth, environment variables, container orchestration, CI/CD, observability concepts, or other backend topics.** Explain plainly when relevant, then ask for the decision.
5. **When asking, give context.** Plain-English summary → why it matters for the product → 2–3 options with tradeoffs → recommendation → ask. Don't dump jargon.
6. **One decision at a time when possible.** Bundling 5 unrelated questions is overwhelming.

Example of good behaviour:
> *"Before I set up the deployment, we need to pick how the app runs in the cloud. The two simple options are: **Cloud Run** (Google's serverless — pay per request, scales to zero when no one's using it, ~$0–$5 for the demo period) or **a small VM** (a tiny always-on server, ~$15/mo). For a demo URL judges visit once, Cloud Run is cheaper and easier. Want me to go with that?"*

Example of bad behaviour:
> *"I'll deploy via Cloud Run with min-instances=0 and use Cloud Build for CI."* ← (no explanation, assumes PM knows what any of that means)

## Strategic context (do not violate)

The Arize judging criteria reward **agents whose self-improvement loop is the core mechanic, not a bolted-on feature**. Phoenix MCP introspection must be load-bearing — if you can build this agent without Phoenix doing real work, you've broken the thesis.

**Pitch framing per phase:**
- MVP: *"Phoenix isn't monitoring this agent — it's how it improves."*
- Full Plan: *"A swarm of 12 agents that learn US insurance appeals from outcomes. Phoenix is the swarm's nervous system."*

Avoid: *"Learned US healthcare law from scratch"* (too grandiose, judges will sniff hand-waving unless backed by 200+ traces of evidence — which only Full Plan provides).

## Hard constraints

### Scope per phase
- **MVP (Part A):** commercial plans, 2 denial types (medical necessity + prior auth), 3 insurers (Aetna, Cigna, UHC), 12-case benchmark, manual learning with human approval.
- **Full Plan (Part B):** widens to 7 denial types, 10 insurers, 100-case benchmark, 12-agent swarm, autonomous learning with hard safety gates + auto-rollback.
- **Always out of scope:** Medicare/Medicaid, live filing with insurers, court representation, attorney work product, PHI, mobile app, multi-language, user accounts.

### Safety & disclosure
- No PHI in Phoenix traces — synthetic composite cases only.
- Every UI output and every demo claim must carry: *"Not legal or medical advice. Draft assistance only."*
- No invented statutes, case law, or policy text. The agent must cite from a controlled local corpus.
- No "this will win your appeal" claims, in code, UI, or demo video.

### Build discipline
- One ADK agent + one offline learning job. **Do not build a multi-agent swarm.**
- Streamlit frontend. **Do not switch to Next.js / React** — UI is not where this submission wins.
- No vector DB unless absolutely forced — local corpus + Phoenix datasets are sufficient.
- Promotion of prompt/playbook changes requires human approval click in the demo UI. No fully autonomous self-mutation.

## Tech stack (fixed)

| Layer | Tool |
|---|---|
| Agent runtime | Google ADK (Python) |
| LLM | Gemini 3 |
| Observability + evals | Arize Phoenix Cloud (free tier) |
| Runtime introspection | `@arizeai/phoenix-mcp` |
| Instrumentation | `openinference-instrumentation-google-adk` |
| Frontend | Streamlit |
| Hosting | Google Cloud Run |
| Storage | local files + GCS JSON for promoted playbooks |
| License | Apache 2.0 |

## Workflow for agents working on this repo

1. **Always read these first** when starting work: this file → `docs/prd/PRD.md` → `docs/architecture.md` → `docs/open-questions.md`.
2. **Check open questions** before designing — many things are intentionally undecided and need user input.
3. **Skill-first**: this repo has `.agents/skills/` — use `brainstorming` before any new feature, `feature-spec` to formalize, `implementation-plan` before coding, `test-driven-development` while coding, `code-review-crsp` before commits.
4. **Never commit credentials.** Phoenix API key, Google Cloud service account, etc. go in `.env` (gitignored).
5. **Never put PHI or real patient data in code, tests, evals, or traces.** Synthetic composite only.
6. **All eval cases live in `eval/` as plain markdown or JSON with provenance notes.**

## Demo discipline

The hackathon demo is 3 minutes. Every architectural decision should be evaluated against: *"does this make the 3-minute demo more compelling, more credible, or more rigorous?"* If not, defer it.

The hero demo arc (memorize this):
1. **0:00–0:20** — pitch: non-American PM, Phoenix-driven learning loop
2. **0:20–0:50** — v1 baseline appeal fails on the hero case
3. **0:50–1:30** — open Phoenix; show MCP-driven failure summary; show prompt/playbook diff
4. **1:30–2:10** — re-run with v3; better appeal, simulator approves
5. **2:10–2:40** — held-out benchmark chart: v1 vs v3 quality lift
6. **2:40–3:00** — close: *"Phoenix isn't monitoring Reverse — it's how Reverse improves."*

## Submission checklist (Devpost requirements)

- [ ] Hosted project URL (Cloud Run)
- [ ] Public GitHub repo with Apache 2.0 license visible in About section
- [ ] ~3-minute demo video
- [ ] Devpost submission form
- [ ] Track selected: **Arize**

## Files agents must update when relevant

- `docs/architecture.md` — when system shape changes
- `docs/open-questions.md` — close questions as resolved, open new ones as discovered
- `docs/prd/PRD.md` — only with user approval (it's the source of truth)
- `README.md` — when status milestones change

## Quick links

- [Product Requirements](docs/prd/PRD.md)
- [Architecture](docs/architecture.md)
- [Open Questions](docs/open-questions.md)
- [Idea exploration history](docs/ideas.md)
- [Hackathon brief](docs/challenge.md)
- [Phoenix docs](https://docs.arize.com/phoenix)
- [Phoenix MCP guide](https://docs.arize.com/phoenix/integrations/mcp/phoenix-mcp-server)
- [Google ADK](https://google.github.io/adk-docs/)
- [Arize hackathon quickstart](https://github.com/Arize-ai/gemini-hackathon)
