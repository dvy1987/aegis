# Heuristics

> **A self-improving appeal-drafting system that helps patients respond to US health-insurance denials — and gets measurably better by learning from Arize Phoenix traces via MCP.**

**Hackathon submission for the [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com/) — Arize partner track.**

---

## The Problem: Asymmetric Warfare

**Who is facing this problem?** Patients navigating an insurance denial—often when they are sick, stressed, and financially squeezed.

**What is the problem?** US health insurers deny roughly 19% of in-network claims (about 85 million a year on ACA exchanges alone). Fewer than 1% are ever appealed. The asymmetry is structural: insurers automate denial with AI and entire third-party "denial-management" companies, while patients face a thirty-page policy document and a phone tree.

**Why is it important?** Of the appeals that *are* filed, more than a third are overturned. That means roughly 99 of every 100 denied patients walk away from money or care that an appeal could have recovered. 

**What is our solution?** 
Heuristics exists to close that gap. It is a calm, free tool that helps any patient understand a denial and draft an appeal in plain language, in under thirty minutes. We don't promise to win the appeal—half of all appeals lose. We promise to make filing one feel possible. Every appeal Heuristics helps with becomes a learning signal that makes the next one better, transparently, with the receipts visible in Phoenix Cloud.

---

## Why this fits the Arize track

The Arize partner track judges submissions on:
1. Technological implementation
2. Design
3. Potential impact
4. **Quality of the agent's self-improvement loop** ← Heuristics' core mechanic
5. Bonus: agents that use observability data to improve over time

Most submissions will be single-agent chatbots with Phoenix bolted on. Heuristics makes Phoenix MCP **structurally load-bearing** — training signal and runtime memory flow through Phoenix; the showcase demo runs a GEPA-style learning loop that proposes prompt and playbook changes you approve before they ship.

---

## How it works (hackathon submission)

The **shipped product** is a **v1 Student** (Google ADK workflow), not the 12-agent swarm. The swarm in `backend/app/aegis_swarm/` is **deferred to post-hackathon** (see [PRD Part B](docs/prd/PRD.md)).

```text
Denial + clinical context
        │
        ▼
┌───────────────────┐     ┌─────────────────────┐
│ Question agent    │────▶│ Enriched patient    │  (showcase + appeal)
│ (optional)        │     │ context for drafter │
└───────────────────┘     └─────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────┐
│ v1 Student workflow (ADK)                         │
│  parse → insurer playbook + US-playbook → Phoenix │
│  → library retrieval → drafter → self-check       │
└───────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────┐     ┌─────────────────────┐
│ Appeal letter     │     │ Outcome simulator   │  (orchestrator, not Student)
└───────────────────┘     └─────────────────────┘

Showcase path (training / learning):
  judges + question judge → Phoenix traces → GEPA loop
  → promotion proposal (drafter + slice playbooks + US-playbook)
  → human approve in UI → write to disk

Appeal path: draft only. No learning, no promotion.
```

**Three learnable layers:** drafter prompt · insurer slice playbooks (`insurer × denial × sub-tactic`) · US-playbook (federal / state-scoped rules).

For architecture detail, see [docs/architecture.md](docs/architecture.md).

---

## The self-improvement loop

Heuristics learns in three graduating stages — a **competency-gated autonomy ladder**:

| Stage | Mode (hackathon) | Post-hackathon (Part B, deferred) |
|---|---|---|
| 🟢 **Apprentice** | **Active.** Showcase GEPA proposes changes; PM approves in the promotion modal | Same |
| 🟡 **Journeyman** | Not enabled | Auto-promote on hard safety gates |
| 🔴 **Master** | Not enabled | Relaxed gates + higher autonomy |

Appeal runs never promote — only the showcase training path can change prompts or playbooks.

---

## What's in scope (hackathon submission)

| Dimension | Shipped (June 2026) | Deferred post-hackathon |
|---|---|---|
| Runtime | v1 Student (ADK) + question agent + library finder | 12-agent **Heuristics swarm** (`aegis_swarm/`) |
| Insurers | 3 (Aetna, Cigna, UHC) in benchmark / showcase | 10 insurers |
| Denial types | 2 (medical necessity, prior auth) | 5 additional types |
| Showcase cohort | Preview 5+2 · Production 50+20 (cases 101–200) | Full 100-case matrix |
| Learning | Showcase GEPA + human approve (Apprentice) | Autonomous Journeyman / Master ladder |
| Playbooks | Slice + US-playbook (`geo_playbooks/`) | State-scoped geo rules when cases carry `us_state` |

## What's NOT in scope (and never will be)

- Live filing with insurers
- Medicare, Medicaid, ERISA self-insured edge cases
- External / Independent Review Organization (IRO) appeals automation
- Court representation, attorney work product
- Real Protected Health Information (PHI) — **synthetic composite cases only**
- Multi-language, mobile, user accounts

---

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| Agent runtime | **Google ADK** (Python) | Hackathon requirement; built with `google-agents-cli` |
| LLM | **Gemini 3** | Hackathon requirement |
| Observability + evals | **Arize Phoenix Cloud** (free tier) | The whole point of the Arize track |
| Runtime introspection | **`@arizeai/phoenix-mcp`** | Lets the agent query its own past traces at runtime |
| Instrumentation | **`openinference-instrumentation-google-adk`** | Auto-tracing for ADK |
| Frontend | **Next.js** (React) | Consumer-grade UX is a first-class product pillar |
| Backend | **FastAPI** | Hosts the v1 ADK Student + showcase learning API |
| Hosting | **Google Cloud Run** | 2 services (Frontend + Backend); scales to zero |

---

## Post-hackathon assessments (open)

Two economics questions are **not answered yet** — they should drive the next roadmap after submission:

1. **Library retrieval quality** — If the library agent can search **online sources more freely** (beyond the controlled local corpus + Vertex search), how much does appeal quality actually improve on held-out cases?
2. **GEPA cost vs lift** — Showcase GEPA loops are **expensive** (many Gemini calls: drafter, judges, question judge, reflection, re-score). Is the measured quality delta large enough to justify that cost at preview vs production cohort scale?

Tracked in [docs/open-questions.md](docs/open-questions.md) §G.

---

## Status

**Phase:** Hackathon submission build. v1 Student, question agent, US-playbook, showcase GEPA, and promotion UI are implemented. **Heuristics swarm (Part B) deferred post-hackathon.** 446 backend unit tests passing.

**Latest handoff:** [docs/memory/agent-handoffs.md](docs/memory/agent-handoffs.md)  
**Current state:** [docs/memory/current-state.md](docs/memory/current-state.md)  
**PRD:** [docs/prd/PRD.md](docs/prd/PRD.md) (Part A = submission; Part B = deferred reference)

---

## Repository structure

```text
aegis/
├── README.md                      ← you are here
├── LICENSE                        ← Apache 2.0 (hackathon requirement)
├── AGENTS.md                      ← rules for AI agents working on this repo
├── .gitignore
├── .env.example                   ← template for Google Cloud + Phoenix credentials
│
├── docs/
│   ├── challenge.md               ← hackathon brief
│   ├── ideas.md                   ← exploration & ranking of 15 ideas (history)
│   ├── architecture/              ← system blueprint & ADRs
│   ├── open-questions.md          ← what's still unresolved
│   ├── prd/
│   │   └── PRD.md                 ← unified PRD: MVP (Part A) + Full Plan (Part B)
│   ├── memory/                    ← agent memory (handoffs, state, index)
│   └── skill-outputs/             ← ledger of skill invocations
│
├── frontend/                      ← Next.js App Router UI
├── backend/                       ← Python ADK FastAPI service + `google-agents-cli`
├── corpus/                        ← controlled local authority snippets
├── playbooks/                     ← promoted insurer slice playbooks
├── geo_playbooks/                 ← US-playbook (insurer-agnostic rules)
├── eval/                          ← benchmark cases, simulator rules, showcase manifest
└── scripts/                       ← deploy, eval CLI, learning runners
```

---

## Built with

- [Google Cloud Agent Development Kit (ADK)](https://google.github.io/adk-docs/)
- [google-agents-cli](https://google.github.io/agents-cli/)
- [Gemini 3](https://ai.google.dev/gemini-api)
- [Arize Phoenix](https://docs.arize.com/phoenix)
- [Phoenix MCP Server](https://docs.arize.com/phoenix/integrations/mcp/phoenix-mcp-server)
- [OpenInference instrumentors](https://github.com/Arize-ai/openinference)
- [Next.js](https://nextjs.org/) + [FastAPI](https://fastapi.tiangolo.com/)
- [Google Cloud Run](https://cloud.google.com/run)
- Built with [Amp](https://ampcode.com) (AI pair-programming)

---

## Disclaimers

This project is a hackathon demo.

- It is **not legal or medical advice.** Outputs are intended as drafting assistance for human review only.
- The simulator is a **transparent rule-based proxy**, not a prediction of real insurer behaviour. Rules are published in the repo at `eval/simulator_rules.json`.
- **No real patient data (PHI) is used.** All benchmark cases are synthetic composites derived from public reporting (ProPublica's *Denied* series, KFF research, state insurance commissioner public records, Patient Advocate Foundation templates).
- The "wins X% of appeals" figures shown in the demo refer to **simulated outcomes on synthetic benchmark cases**, not real-world appeal wins.

---

## License

[Apache License 2.0](LICENSE).

---

## Acknowledgements

Built by a Product Manager who, twenty days before submission, had never read a US insurance denial letter. Heuristics didn't either — it learned from outcomes.

That's the whole point.
