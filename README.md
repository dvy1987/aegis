# Aegis

> **A self-improving multi-agent system that drafts US health-insurance appeal letters and gets measurably better at them by introspecting its own Arize Phoenix traces via MCP.**

**Hackathon submission for the [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com/) — Arize partner track.**

---

## The Problem: Asymmetric Warfare

**Who is facing this problem?** Patients navigating an insurance denial—often when they are sick, stressed, and financially squeezed.

**What is the problem?** US health insurers deny roughly 19% of in-network claims (about 85 million a year on ACA exchanges alone). Fewer than 1% are ever appealed. The asymmetry is structural: insurers automate denial with AI and entire third-party "denial-management" companies, while patients face a thirty-page policy document and a phone tree.

**Why is it important?** Of the appeals that *are* filed, more than a third are overturned. That means roughly 99 of every 100 denied patients walk away from money or care that an appeal could have recovered. 

**What is our solution?** 
Aegis exists to close that gap. It is a calm, free tool that helps any patient understand a denial and draft an appeal in plain language, in under thirty minutes. We don't promise to win the appeal—half of all appeals lose. We promise to make filing one feel possible. Every appeal Aegis helps with becomes a learning signal that makes the next one better, transparently, with the receipts visible in Phoenix Cloud.

---

## Why this fits the Arize track

The Arize partner track judges submissions on:
1. Technological implementation
2. Design
3. Potential impact
4. **Quality of the agent's self-improvement loop** ← Aegis's core mechanic
5. Bonus: agents that use observability data to improve over time

Most submissions will be single-agent chatbots with Phoenix bolted on. Aegis makes Phoenix MCP **structurally load-bearing** — without it, the agents cannot work well, and you can see this in the demo by toggling it off and watching the quality collapse.

---

## How it works

```diagram
                            ╭─────────────────────╮
                            │   Orchestrator      │
                            ╰──┬──────────┬───────╯
                               │          │
              ╭────────────────┤          ├──────────────╮
              │                │          │              │
       ╭──────▼──────╮  ╭──────▼──────╮  ╭▼─────────────────╮
       │  Triage     │  │  Insurer    │  │  Learning        │
       │  Agent      │  │  Intel      │  │  Coordinator     │
       │             │  │  Agent      │  │  (meta-agent)    │
       ╰──────┬──────╯  ╰──────┬──────╯  ╰──────────┬───────╯
              │                │                    │
              ▼                ▼                    │ continuously
    ╭────────────────────────────────╮              │ rewrites prompts
    │  Specialist Researcher Pool    │              │ / playbooks via
    │  • Policy Detective            │              │ Phoenix MCP
    │  • Medical Necessity Researcher│              │
    │  • Legal Researcher            │              │
    │  • Precedent Miner             │              │
    ╰──────────────┬─────────────────╯              │
                   ▼                                │
            ╭──────────────╮                        │
            │ Strategist   │◄──── playbook ◄───────┤
            ╰──────┬───────╯                        │
                   ▼                                │
            ╭──────────────╮                        │
            │ Drafter      │◄──── prompt v_n ◄─────┤
            ╰──────┬───────╯                        │
                   ▼                                │
            ╭──────────────╮                        │
            │ Adversarial  │                        │
            │ Reviewer     │                        │
            ╰──────┬───────╯                        │
                   ▼                                │
            ╭──────────────╮                        │
            │ Quality      │◄── 7 LLM judges ──────┤
            │ Judge Panel  │                        │
            ╰──────┬───────╯                        │
                   ▼                                │
                                                    │
            ALL traces stream to ───────────────────┘
            Phoenix Cloud continuously.

            Learning Coordinator queries Phoenix MCP ~200 times during
            the 20-day build to evolve prompts and playbooks. Each
            version is a Phoenix experiment.
```

For the full system blueprint, see [docs/architecture.md](docs/architecture.md).

---

## The self-improvement loop

Aegis learns in three graduating stages — a **competency-gated autonomy ladder**:

| Stage | Mode | Graduation criteria |
|---|---|---|
| 🟢 **Apprentice** | Every improvement requires PM approval | After 50 reviewed proposals AND held-out composite ≥ 0.55 |
| 🟡 **Journeyman** | Auto-promote on hard safety gates (lift ≥ +3%, no safety regression, no hallucinations, ≤5/day) | After 100 auto-promotions AND held-out composite ≥ 0.75 |
| 🔴 **Master** | Aggressive: relaxed gates (lift ≥ +1%), higher rate limit, broader patch types | Auto-demotes to Journeyman if composite drops > 10% |

The system **knows when it's competent** and **knows when it isn't** — that's the Arize thesis embodied.

---

## What's in scope

| Dimension | MVP (Days 1–7) | Full Plan (Days 8–20) |
|---|---|---|
| Agents | 1 + 1 offline learning job | 12 specialist agents + Learning Coordinator |
| Insurers benchmarked | 3 (Aetna, Cigna, UHC) | 10 (+ Anthem, Humana, Kaiser, Centene, Molina, 2× BCBS) |
| Denial types | 2 (medical necessity, prior auth) | 7 (+ coverage exclusion, network adequacy, experimental, MHPAEA parity, step therapy) |
| Benchmark cases | 12 (6 train + 6 held-out) | 100 (60 train + 40 held-out) |
| Learning loop | Manual, ~3 runs | Continuous, ~200 runs |
| Promotion | Human-approved | Staged autonomy ladder |

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
| Backend | **FastAPI** | Hosts the ADK orchestrator and specialist swarm |
| Hosting | **Google Cloud Run** | 2 services (Frontend + Backend); scales to zero |

---

## Build plan (20 days)

- **Week 1 (Days 1–7) — MVP.** Single ADK agent + 7 tools + 12-case benchmark + Phoenix MCP wired. Shippable as standalone submission on Day 7 if anything goes wrong.
- **Week 2 (Days 8–14) — Swarm.** Decompose into 9-agent runtime swarm. Expand benchmark to 60 cases.
- **Week 3 (Days 15–20) — Autonomous learning + demo.** Add Learning Coordinator. Run ~200 learning iterations across slices. Expand benchmark to 100 cases. Record demo. Submit.

| Milestone | Win probability estimate |
|---|---|
| End of Day 7 (MVP shippable) | Top 3 plausible |
| End of Day 14 (swarm shippable) | Top 2 plausible |
| End of Day 20 (Full Plan shippable) | **Win** |

---

## Status

**Phase:** Pre-build planning. PRD drafted. Architecture defined. **No code yet.** Build starts Day 1 once open questions clear.

**Latest handoff:** [docs/memory/agent-handoffs.md](docs/memory/agent-handoffs.md)
**Current state:** [docs/memory/current-state.md](docs/memory/current-state.md)
**Open questions:** [docs/open-questions.md](docs/open-questions.md)

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
├── corpus/                        ← (TBD) authorities
├── playbooks/                     ← (TBD) learning patches and tactics
├── eval/                          ← (TBD) benchmark cases + judges + simulator rules
└── scripts/                       ← (TBD) deployment and eval execution
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

Built by a Product Manager who, twenty days before submission, had never read a US insurance denial letter. Aegis didn't either — it learned from outcomes.

That's the whole point.
