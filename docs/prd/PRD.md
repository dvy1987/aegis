# Product Requirements Document — Aegis (Reverse v2)

| | |
|---|---|
| **Project** | Aegis — A calm, learning agent that helps people draft US health-insurance appeals |
| **Author** | PM (with Amp orchestration) |
| **Date** | 2026-05-27 |
| **Status** | Draft v4 — UX promoted to first-class pillar; Next.js frontend; competitive landscape and Arize rubric alignment added |
| **Submission track** | Google Cloud Rapid Agent Hackathon — Arize partner bucket |
| **Primary goal** | Win 1st place ($5,000) in the Arize partner bucket |
| **Secondary goal** | A submission whose user experience is good enough that a stressed person filing an appeal at 11pm finds it usable, and that holds up as a portfolio-grade PM artifact |
| **Build window** | 20 days |
| **Companion docs** | [Design brief](../design-brief.md) · [Impact stats](../research/impact-stats.md) · [Assumption map](../research/assumption-map.md) · [Open questions](../open-questions.md) · [Architecture](../architecture.md) |

---

## 0. How to Read This Document

This PRD has **two nested specifications**:

- **Part A — MVP (Days 1–7).** A single-agent, narrow-scope, fully shippable submission. This is the safety-net version. If everything in Part B fails, this is what we submit.
- **Part B — Full Plan (Days 8–20).** The 12-agent swarm with autonomous learning loop on top of the MVP foundation. This is the version designed to win.

Each part is independently shippable. Build the MVP first; if life lets us, layer the full plan on top.

```diagram
╭──────────────────────────────────────────────────────────────╮
│  Full Plan (20 days)                                         │
│                                                              │
│  ╭─────────────────────╮                                     │
│  │ Part A — MVP        │  ← Day 7 shippable                  │
│  │ Days 1–7            │     Single agent + 7 tools          │
│  │ §1–§9 below          │     12-case benchmark + Phoenix MCP │
│  ╰──────────┬──────────╯                                     │
│             │                                                │
│             ▼                                                │
│  ╭─────────────────────╮                                     │
│  │ Part B — Full Plan  │  ← Days 8–20                        │
│  │ §10–§17 below        │     9-agent swarm, then learning    │
│  │                     │     loop + 100-case benchmark        │
│  ╰─────────────────────╯                                     │
╰──────────────────────────────────────────────────────────────╯
```

| Stage | Shippable As | Win probability estimate |
|---|---|---|
| End of MVP (Day 7) | Complete single-agent submission with Phoenix MCP | Top 3 plausible |
| End of Week 2 swarm (Day 14) | 9-agent system + 60-case benchmark | Top 2 plausible |
| End of Full Plan (Day 20) | Full Aegis swarm + autonomous learning + 100-case benchmark | **Win** |

---

# PART A — MVP (Days 1–7)

## 1. Executive Summary (MVP)

**Aegis MVP** is a calm, consumer-grade web tool that helps a person turn a US health-insurance denial letter into a drafted first-level internal appeal in under thirty minutes, written in plain language and grounded in the person's plan documents and public statutory text.

Behind the interface, a single Google ADK agent does the work — and that agent measurably improves at drafting appeals by introspecting its own Arize Phoenix traces and eval scores via the Phoenix MCP server at runtime. Aegis is not trying to be a generalist US healthcare expert; it learns *insurer-specific appeal tactics* from observed evaluation outcomes, and the improvement is visible on a held-out benchmark.

**The product anchors on three things at once, none of which can be dropped:**

1. **A self-improvement loop where Phoenix is structurally load-bearing** — disabling Phoenix MCP should visibly degrade the agent's quality. (The Arize judging thesis.)
2. **A consumer experience that a stressed person can actually use** — calm, plain-language, dignified, accessible. Filing an appeal is already a hard day; the product should not add to that. (The Design judging criterion and the PM-portfolio thesis.)
3. **An impact story grounded in primary research, not grievance** — the problem is real and large, and stated factually with sources, not by riding cultural anger at the insurance industry. (The Potential Impact criterion.)

**The single line that anchors the MVP pitch:**
> *"Phoenix isn't just monitoring this agent — it's how this agent improves."*

### Why this matters (impact framing, drawn from [docs/research/impact-stats.md](../research/impact-stats.md))

US health insurers deny roughly 19% of in-network claims — about 85 million claims a year on the ACA exchanges alone ([KFF, Mar 2026](https://www.kff.org/patient-consumer-protections/claims-denials-and-appeals-in-aca-marketplace-plans-in-2024/)). Fewer than 1% of those denials are ever appealed ([KFF](https://www.kff.org/patient-consumer-protections/claims-denials-and-appeals-in-aca-marketplace-plans-in-2024/)). Of the ones that are, more than a third are overturned. That arithmetic means roughly **99 of every 100 denied patients walk away from money or care that an appeal might have recovered.** The asymmetry is structural: insurers automate denial — 84% use AI in operations ([NAIC, 2024](https://content.naic.org/sites/default/files/inline-files/Health%20Survey%20Report%20-%20FINAL%205.9.25.pdf)) — while patients face a thirty-page policy document and a phone tree.

Aegis exists to close that gap. It does not promise to win the appeal. It promises to make filing one feel possible.

## 2. Problem Statement

### Real-world problem (grounded in primary research — full set in [impact-stats.md](../research/impact-stats.md))

Three facts together describe the problem Aegis exists to address:

1. **Denials are common and getting more common.** Roughly 19% of in-network ACA claims were denied in 2024 — about 85 million claims, with insurer-level rates ranging from 3% to 36% ([KFF, Mar 2026](https://www.kff.org/patient-consumer-protections/claims-denials-and-appeals-in-aca-marketplace-plans-in-2024/)). 33% of insured adults say their insurer denied a doctor-prescribed service in the last two years ([KFF, Jan 2026](https://www.kff.org/public-opinion/kff-health-tracking-poll-prior-authorizations-rank-as-publics-biggest-burden-when-getting-health-care/)). 73% of insured adults call denials and delays a "major problem" ([KFF, 2025](https://www.kff.org/patient-consumer-protections/kff-health-tracking-poll-public-finds-prior-authorization-process-difficult-to-manage/)).

2. **Almost no one appeals.** Fewer than 1% of denied ACA in-network claims are ever appealed (262,982 out of ~85M) ([KFF](https://www.kff.org/patient-consumer-protections/claims-denials-and-appeals-in-aca-marketplace-plans-in-2024/)). 60% of consumers either don't know or aren't sure they have the right to an external appeal ([KFF Consumer Survey](https://www.kff.org/affordable-care-act/kff-survey-of-consumer-experiences-with-health-insurance/)). The process is opaque, intimidating, and per-insurer cryptic.

3. **When people do appeal, it works often enough that not appealing is a real loss.** Internal appeals overturn the original denial about 34% of the time on average; in some states and categories (e.g. home healthcare in New York) overturn rates exceed 78% ([JAMA, Apr 2026](https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/2847657)).

The arithmetic: for every 100 denied claims, roughly 34 would be overturned if appealed — but only fewer than 1 actually is. **Roughly 99 of every 100 denied patients walk away from money or care an appeal could have recovered.**

The asymmetry is structural and AI-mediated. 84% of insurers use AI/ML in operations, including for prior-auth determinations ([NAIC, 2024](https://content.naic.org/sites/default/files/inline-files/Health%20Survey%20Report%20-%20FINAL%205.9.25.pdf)). 61% of physicians say AI is increasing prior-auth denials ([AMA, 2024](https://www.ama-assn.org/)). On the patient side: a thirty-page policy document, a phone tree, and a 180-day deadline.

This is the gap Aegis is built to close — for the individual person filing one appeal, not for the system.

### Hackathon-relevant problem

The Arize track judges submissions on four co-equal sub-criteria, plus a bonus:

1. **Technical implementation** — quality of integration with Google Cloud and Arize Phoenix
2. **Meaningful use of tracing and MCP** — Phoenix is not bolted-on; it does real work in the agent
3. **Quality of the agent's self-improvement loop** — the unique Arize criterion
4. **Overall impact** — does the agent meaningfully change something for real people
5. **Bonus** — agents that use their own observability data to improve over time

Plus four hackathon-wide criteria (Technical Implementation, Design, Potential Impact, Quality of Idea) — see [docs/challenge.md](../challenge.md).

Aegis's strategic bet is that a submission visibly winning on **all** of these — observability/MCP load-bearing, self-improvement demonstrable, real consumer-grade design, real impact narrative grounded in primary research — wins the bucket. See [§18 Arize Rubric Alignment](#18-arize-rubric-alignment) for the explicit mapping.

## 2.1 Competitive Landscape & Differentiation

This is a genuinely emerging space. Aegis is **not** the first patient-side AI appeal tool, and the pitch must acknowledge prior art credibly. Sources: [North Carolina Health News, Nov 2025](https://www.northcarolinahealthnews.org/2025/11/22/ai-vs-ai-patients-deploy-bots-to-battle-health-insurers-that-deny-care/), [Stateline, Nov 2025](https://stateline.org/2025/11/20/patients-deploy-bots-to-battle-health-insurers-that-deny-care/), full table in [impact-stats.md §6](../research/impact-stats.md#6-competitive-landscape--patient-side-ai-for-appeals-critical-for-positioning).

| Player | Type | What they do | Differentiation gap vs Aegis |
|---|---|---|---|
| **Counterforce Health** | Nonprofit, free | AI assistant: denial letter + policy + research → drafts appeal letter | Closest direct competitor. Static prompt — no self-improvement loop |
| **Sheer Health** | For-profit | Connect insurance account, upload bills; freemium with paid full handling | Provider/billing as much as patient; not loop-based |
| **Cofactor AI Denial Suite** | For-profit | Provider-side appeal generation | Different market (providers, not patients) |
| **Waystar AltitudeCreate** | Enterprise | Enterprise GenAI for provider appeal workflows | Different market |
| **OpenHand Health** | For-profit | Parses medical jargon for patients | Adjacent; not appeal-focused |

**Aegis's four-point differentiation thesis (must be explicit in pitch and product):**

1. **Self-improvement from outcomes.** Phoenix-driven loop means Aegis measurably gets better at the job over time, transparently. Counterforce ships a static prompt; Aegis ships a learning system. (This is also the Arize judging hook.)
2. **UX quality as a first-class pillar.** Calm, human, premium consumer-health design — not a tech demo wrapped in a form. (See [docs/design-brief.md](../design-brief.md).) Most competitor experiences feel like utilities; Aegis aims for a feel comparable to Headspace / One Medical / Maven.
3. **Transparent autonomy ladder with visible humility.** Apprentice → Journeyman → Master autonomy stages with public competency scores per slice. Trust is earned by showing what the agent does *not* know.
4. **Open source under Apache 2.0.** Anyone can audit, fork, or self-host. Counterforce is free; Aegis is also auditable and forkable.

**Tone guardrail for any pitch material about competition or the insurance industry:** *We earn trust by being constructive, not by riding cultural anger. The product never invokes acts of violence, vigilantism, or polarizing public events around the insurance industry.* (Mirrored in [AGENTS.md](../../AGENTS.md) and [design-brief.md §8](../design-brief.md#8-what-must-not-be-in-the-product).)

## 3. MVP Goals & Non-Goals

### Goals
1. **G1.** Working single agent on Cloud Run ingesting a denial letter and returning a structured appeal package
2. **G2.** Phoenix instrumentation via OpenInference on Google ADK
3. **G3.** Runtime use of the Phoenix MCP server — the agent queries its own past traces before drafting each appeal
4. **G4.** Measurable v1 → v3 quality improvement on a 6-case held-out benchmark
5. **G5.** 3-minute demo video that visibly shows the self-improvement loop
6. **G6.** Public GitHub repo with Apache 2.0 license
7. **G7.** Devpost submission complete
8. **G8.** UX quality as a first-class pillar — calm, accessible, consumer-health grade

### Non-Goals (deferred to Part B or post-hackathon)
- ✗ Multi-agent architecture (Part B)
- ✗ Autonomous learning loop (Part B)
- ✗ 100-case benchmark (Part B uses 100; MVP uses 12)
- ✗ All insurers/denial-types (Part B widens; MVP is 3 insurers × 2 denial types)
- ✗ Production deployment with real users
- ✗ Real-time insurer integrations
- ✗ Medicare/Medicaid
- ✗ External/IRO appeals
- ✗ Court representation
- ✗ Multi-language
- ✗ Mobile app
- ✗ User accounts / auth / multi-tenant
- ✗ Vector database

## 4. MVP Scope

| Dimension | In Scope (MVP) |
|---|---|
| **Plan types** | Commercial / private |
| **Denial types** | Medical necessity, Prior authorization / missing pre-auth |
| **Insurers (benchmark)** | Aetna, Cigna, UnitedHealthcare |
| **Appeal stage** | Internal appeal (first level) only |
| **Outputs** | Appeal letter, citations, evidence checklist, missing-info flags, risk notes |
| **Languages** | English |
| **Frontend** | Next.js App Router, Tailwind, shadcn/ui, framer-motion |

## 5. MVP Functional Requirements

### FR1 — Denial Case Intake
Next.js UI accepts pasted text or uploaded PDF. User can also pick from 12-case benchmark.

### FR2 — Structured Case Parsing
Agent parses input to JSON: insurer, plan_type, denial_type, service_or_procedure (+CPT), diagnosis_summary, state, cited_denial_reason, deadlines_mentioned, missing_facts[].

### FR3 — Authority Retrieval
BM25 retrieval over `corpus/authorities/` (public statutory text, insurer-published appeal instructions, ERISA/ACA language). Must not invent statutes or case law.

### FR4 — Learned Playbook Retrieval
Load current promoted playbook for `(insurer, denial_type)` from versioned JSON in `playbooks/`.

### FR5 — Phoenix MCP Trace Introspection (load-bearing)
Before drafting, agent queries Phoenix MCP for similar past traces and receives summary of failure patterns, success traits, current prompt + playbook versions. **Removing this must degrade quality.**

### FR6 — Appeal Package Drafting
Structured output: case_summary, denial_grounds_interpreted, appeal_strategy, appeal_letter, citations_used, missing_evidence_checklist, risk_flags, safety_disclaimer.

### FR7 — Self-Check Pass
LLM verifies: each citation traceable to corpus, no invented statutes, facts match input, missing-info reflected, no overclaiming.

### FR8 — Demo Simulator (Two-Step Transparent)
1. Feature extraction (LLM marks 10 features Y/N)
2. Deterministic scoring per published rules in `eval/simulator_rules.json`

### FR9 — Manual Learning Job
`learn.py` script pulls failed traces from Phoenix, proposes prompt/playbook patches, runs Phoenix experiments on held-out 6 cases, presents proposals for human approval via Next.js UI.

### FR10 — Demo Mode in UI
Next.js UI: case selector, v1/v3 buttons, side-by-side comparison, eval score panel, simulator outcome, pending learning proposals, Phoenix Cloud links.

## 6. MVP Non-Functional Requirements

- **NFR1 — Reproducibility:** Any judge can clone and reproduce v1 → v3 improvement
- **NFR2 — Safety:** "Draft for review — not legal or medical advice" everywhere
- **NFR3 — No PHI:** Synthetic composite cases only, provenance in `eval/dataset_card.md`
- **NFR4 — Trace fidelity:** Every run produces complete Phoenix trace with full metadata
- **NFR5 — Cost:** Gemini API spend < $50 for MVP
- **NFR6 — Performance:** Each run completes < 60s
- **NFR7 — UX Quality:** Follows design-brief.md for a premium, calm consumer-health feel.

### 6.1 UX & Tone Principles
See docs/design-brief.md. The UI must feel calm, dignified, and trustworthy. No AI marketing voice, no exclamation marks. Tone is factual and grounded.

## 7. MVP Success Criteria

| # | Criterion | Target |
|---|---|---|
| **SC1** | `weighted_quality` summary metric improvement v1 → v3 on 6 held-out cases | ≥ +20% (e.g., 0.55 → 0.75) |
| **SC2** | Safety hard gate (J1) | 100% PASS across all 12 benchmark cases, all versions |
| **SC3** | Hallucination & Internal Consistency hard gate (J2) | 100% PASS across all 12 benchmark cases, all versions |
| **SC4** | Simulator overturn proxy rate | ≥ +50% improvement |
| **SC5** | Trace completeness (Phoenix metadata) | 100% |
| **SC6** | Submission lands in top 3 of Arize bucket | Devpost result |

## 8. MVP Evaluation & Testing

> **Source of truth:** [docs/evals/2026-05-27-aegis-appeal-rubric.md](../evals/2026-05-27-aegis-appeal-rubric.md) (v2 — AlphaEval 2026 compliant). [docs/evals/2026-05-27-aegis-judges.md](../evals/2026-05-27-aegis-judges.md) defines the 7-judge panel. [docs/evals/2026-05-27-aegis-eval-pipeline.md](../evals/2026-05-27-aegis-eval-pipeline.md) defines the CI + nightly + promotion-gate pipelines. This section summarises; the rubric file is canonical.

### Benchmark
12 synthetic composite cases (6 calibration + 6 held-out) = 3 insurers × 2 denial types × 2 cases each. Dataset provenance in `eval/dataset_card.md`. Splits in `eval/cases/{train,holdout}/`.

### Scoring Model (per AlphaEval 2026)

Every appeal letter is scored by a **7-judge LLM panel**, each judge owning exactly one rubric concern. **Safety and Hallucination are binary hard gates — never weighted, never averaged in.** A FAIL on either gate produces `verdict: FAIL` for the whole run regardless of other scores.

**Hard gates (2 — pass/fail):**
| # | Gate | Verdict |
|---|---|---|
| J1 | Safety (PII / disclaimer / no-guarantee claims) | PASS / FAIL |
| J2 | Hallucination & Internal Consistency (citation fidelity + non-contradiction) | PASS / FAIL |

**Weighted dimensions (5 — independent 1/3/5 scales, sum to 100%):**
| # | Dimension | Weight |
|---|---|---|
| J3 | Grounding / citation correctness | 35% |
| J4 | Case specificity | 25% |
| J5 | Evidence completeness | 15% |
| J6 | Insurer tactic alignment | 15% |
| J7 | Persuasive coherence | 10% |

The composite `weighted_quality` (each dimension normalised 1→0.2, 3→0.6, 5→1.0) is reported as a **summary metric only** — never as the sole promotion gate. Promotion gating uses per-dimension regression thresholds (see §15.2 and pipeline doc).

### Test Plan
- **Unit tests** for each tool (pytest, behaviour-preserving refactors fully autonomous).
- **Integration test:** end-to-end agent run on 1 calibration case.
- **Eval suite:** 12 cases × 7 judges via Phoenix Experiments; deterministic gates (regex, disclaimer-string, JSON-schema) run first to short-circuit cheaply.
- **Calibration gate (Day 1–2):** Cohen's κ ≥ 0.6 between each judge and PM-hand-scored anchors before any judge is trusted for promotion gating. Judges below threshold are advisory only.
- **Pre-merge gate:** all hard gates PASS; no weighted dimension drops > 10% from rolling baseline; latency p95 < 60s.
- **Regression gate:** new prompt/playbook version v(n) promotes only if (a) both hard gates 100% PASS on held-out, (b) `weighted_quality` ≥ v(n-1), (c) no individual dimension drops > 10%.
- **Demo smoke test:** full Next.js + Cloud Run flow on hero case end-to-end < 60s.

### Cost Model
Per-judge call ~$0.014; per letter (7 judges) ~$0.10; MVP benchmark run (12 cases) ~$1.20; 20-day ceiling ~$300. See rubric §4 for full breakdown.

## 9. MVP Demo Script (Day 7 Backup)

If we submit at end of Week 1, this is the demo:

| Time | Beat | Screen |
|---|---|---|
| 0:00–0:20 | Hook | *"I'm a PM in India. This agent drafts US insurance appeals and gets smarter by querying its own Phoenix traces."* |
| 0:20–0:50 | v1 fails | Cigna case loaded. v1 appeal generic, composite 0.52 (baseline target), simulator DENY |
| 0:50–1:30 | Phoenix protagonist | Open Phoenix, show MCP-driven failure summary, show approved prompt/playbook patch |
| 1:30–2:10 | v3 wins | New appeal quotes plan language, composite 0.75 (improved target), simulator APPROVE |
| 2:10–2:40 | Held-out chart | v1 vs v3 across 6 cases, +24% lift, safety stable, hallucination 0. Phoenix UI prominently shown on screen (>= 60s total display time) |
| 2:40–3:00 | Close | *"Phoenix isn't monitoring this agent — it's how it improves."* |

---

# PART B — Full Plan (Days 8–20)

> Builds on the MVP. Adds 8 specialist agents, autonomous learning loop, expanded benchmark, and the audacious demo.

## 10. The Audacious Thesis

> **"We're not submitting an agent. We're submitting the *first self-improving multi-agent organism* — a swarm of 12 specialist agents that collectively learn US health-insurance appeals from outcomes. Phoenix isn't a sidecar. Phoenix is the swarm's nervous system. Watch it get measurably smarter, in production, in front of you."**

## 11. Why this approach (for Arize Specifically)

Other 6 partner tracks (MongoDB, Elastic, Fivetran, GitLab, Dynatrace) cannot tell a self-improvement story at all. A 12-agent self-improving swarm where Phoenix is structurally load-bearing isn't just better — it's a *different category of submission*.

Judges will see:
- Submission 1: "Customer support agent with Phoenix tracing" (most common)
- Submission 2: "Code-review agent with Phoenix evals"
- Submission 3: "Phoenix dashboard improver" (safe meta-play)
- **Submission X: Aegis — a 12-agent swarm that learns US insurance appeals from 200+ Phoenix traces, demonstrating measurable composite-quality lift from ~0.40 → ~0.75 (design target) across 8 prompt versions on a 100-case benchmark, with the entire learning loop visible in the Phoenix UI**

This is a highly differentiated approach.

## 12. The Swarm Architecture (12 Agents)

### 12.1 Topology

```diagram
                            ╭─────────────────────╮
                            │   Orchestrator      │
                            │   (Coordinator)     │
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
              │ routes to specialists                │ continuously
              │                                      │ rewrites prompts
              ▼                                      │ / playbooks
    ╭────────────────────────────────╮              │
    │  Specialist Researcher Pool    │              │
    │                                │              │
    │  ┌──────────────────────────┐  │              │
    │  │ Policy Detective         │  │              │
    │  │ Medical Necessity Researcher │              │
    │  │ Legal Researcher         │  │              │
    │  │ Precedent Miner          │  │              │
    │  └──────────────────────────┘  │              │
    ╰──────────────┬─────────────────╯              │
                   │ findings                       │
                   ▼                                │
            ╭──────────────╮                        │
            │ Strategist   │ ◄──── playbook ◄──────┤
            │ Agent        │                        │
            ╰──────┬───────╯                        │
                   │ strategy                       │
                   ▼                                │
            ╭──────────────╮                        │
            │ Drafter      │ ◄──── prompt v_n ◄────┤
            │ Agent        │                        │
            ╰──────┬───────╯                        │
                   │ draft                          │
                   ▼                                │
            ╭──────────────╮                        │
            │ Adversarial  │  ◄── simulates ────────┤
            │ Reviewer     │      insurer's         │
            │ ("Red Team") │      counter-arguments │
            ╰──────┬───────╯                        │
                   │ critique                       │
                   ▼                                │
            ╭──────────────╮                        │
            │ Quality      │  ◄── 7 LLM judges ─────┤
            │ Judge Panel  │      composite scoring │
            ╰──────┬───────╯                        │
                   │                                │
                   ▼                                │
            ╭──────────────╮                        │
            │ Outcome      │                        │
            │ Simulator    │                        │
            ╰──────┬───────╯                        │
                   │                                │
                   ▼                                │
            ╭───────────────────────╮               │
            │ Pattern Synthesizer   │ ─────────────►│
            │ (post-run)            │  feeds back   │
            ╰───────────────────────╯  to Learning  │
                                       Coordinator  │
                                                    │
            ALL of the above stream traces to ──────┘
            Phoenix Cloud continuously.

            Learning Coordinator queries Phoenix MCP
            ~200 times during the 20-day build to
            evolve prompts and playbooks. Each version
            is a Phoenix experiment.
```

### 12.2 Agent Roles

1. **Orchestrator** — Receives case, dispatches through pipeline, manages parallelism, maintains trace context
2. **Triage Agent** — Parses denial, classifies type/complexity, decides which specialists run, outputs routing manifest
3. **Insurer Intelligence Agent** — Phoenix-MCP-first. Queries past traces for the current `(insurer, denial_type, state)` slice. Outputs Insurer Brief
4. **Policy Detective** — Deep-reads plan documents, extracts relevant clauses, identifies plan-language inconsistencies
5. **Medical Necessity Researcher** — Retrieves AMA/specialty society guidelines, InterQual/MCG summaries, USPSTF recommendations, peer-reviewed evidence
6. **Legal Researcher** — Federal (ERISA, ACA §2719, MHPAEA, No Surprises Act) + state law + recent CMS enforcement
7. **Precedent Miner** — Searches state insurance commissioner decisions, ProPublica *Denied* cases, public IRO decisions
8. **Strategist Agent** — Synthesizes all briefs, picks angle of attack, selects playbook tactics, outputs structured appeal strategy
9. **Drafter Agent** — Writes the actual appeal letter using current promoted prompt version
10. **Adversarial Reviewer (Red Team)** — Plays insurer's denial reviewer, attacks draft for weaknesses, Drafter iterates once
11. **Quality Judge Panel** — 7 LLM-as-judge evaluations as Phoenix evals: grounding, specificity, evidence, tactic alignment, legal soundness, safety, persuasive coherence
12. **Outcome Simulator** — Two-step transparent simulator (same as MVP, but per-insurer tuned)

**+ Learning Coordinator (meta-agent)** — Wakes hourly, pulls failed traces, generates candidate patches, runs Phoenix experiments, **auto-promotes patches passing safety gates**, full audit trail
**+ Pattern Synthesizer (post-run)** — Summarizes meta-patterns across insurers, outputs to inherited meta-playbook

## 13. Expanded Scope (Full Plan)

### 13.1 Insurers (10, not 3)
Aetna, Cigna, UnitedHealthcare, Anthem/Elevance, Humana, Kaiser Permanente, Centene/Ambetter, Molina, BCBS-MI, BCBS-TX

### 13.2 Denial Types (7, not 2)
- Medical necessity
- Prior authorization / missing pre-auth
- Coverage exclusion
- Out-of-network / network adequacy
- Experimental/investigational
- Mental health parity (MHPAEA)
- Step therapy / fail-first protocols

### 13.3 Appeal Stages
- First-level internal appeal (primary)
- Second-level internal appeal (when applicable)
- External / IRO appeal (template only)
- State insurance commissioner complaint draft (template)

### 13.4 Specialty Areas Covered
- Mental health / behavioral health
- Oncology
- Maternity / fertility (incl. ACA preventive)
- Pediatric specialty
- Chronic disease management
- Surgery / orthopedics
- Imaging / diagnostics

### 13.5 Benchmark Dataset
- **60 calibration cases** for learning loop
- **40 held-out cases** for v_n vs v_n+1 reporting
- Distribution: ~10 cases per insurer × 7 denial types weighted by real-world frequency
- All synthetic composites; provenance in `eval/dataset_card.md`
- Built progressively over Days 1–17

## 14. The 20-Day Build Plan

### Week 1 — MVP (Days 1–7) — Part A above
- Day 1-10 must include: Run the 5 critical assumption tests (A1 eval signal, A2 Phoenix UI demo viability, A3 case credibility, A4 MCP+ADK integration, A5 Learning Coordinator autonomy). If any fail, pitch is updated downward.
- Day 1: Resolve open questions, sign up for Phoenix Cloud, set up Google Cloud, scaffold repo
- Day 2: Build local corpus (~30 docs); generate first 20 benchmark cases
- Day 3: Build single ADK agent with 7 tools; first end-to-end run
- Day 4: Phoenix instrumentation + Phoenix MCP wired; first traces appearing
- Day 5: 5 of 7 LLM judges implemented; first benchmark eval run (v1 baseline)
- Day 6: Next.js UI v1 — case workbench + Phoenix link-out
- Day 7: **🎯 Milestone 1 — MVP shippable as standalone submission**

### Week 2 — Swarm (Days 8–14)
- Day 8: Decompose single agent into Triage + Strategist + Drafter
- Day 9: Add Insurer Intelligence Agent (Phoenix MCP heavy user)
- Day 10: Add Policy Detective + Medical Necessity Researcher + Legal Researcher
- Day 11: Add Precedent Miner + expand benchmark to 60 cases
- Day 12: Add Adversarial Reviewer + iteration loop
- Day 13: Add Quality Judge Panel (7 judges)
- Day 14: **🎯 Milestone 2 — 9-agent swarm shippable on 60-case benchmark**

### Week 3 — Learning + Polish (Days 15–20)
- Day 15: Implement Learning Coordinator meta-agent
- Day 16: Run learning loop iterations 1–4 (Cigna med necessity, UHC prior auth, Aetna mental health, Anthem step therapy)
- Day 17: Add Pattern Synthesizer; expand benchmark to 100 cases; run iterations 5–8
- Day 18: Auto-promotion + rollback safety gates; Next.js UI polish; v1 → v8 comparison chart
- Day 19: Demo video script + record + edit
- Day 20: **🎯 Milestone 3 — Full Plan shippable. Final benchmark run, submit to Devpost.**

## 15. The Self-Improvement Loop (Autonomous Version)

### 15.1 Continuous Loop (Learning Coordinator)
- Wakes hourly (configurable)
- Queries Phoenix MCP: `traces WHERE prompt_version=current AND composite_score < 0.6 LIMIT 50`
- Per slice `(insurer, denial_type)`:
  - LLM analyzes failure patterns
  - Generates 1–3 candidate patches (specialist prompts, playbooks, strategist heuristics)
  - Each candidate becomes a Phoenix Experiment on held-out sub-sample
  - Best candidate passing ALL safety gates auto-promotes
  - Rejected candidates archived with reason
- All actions logged + visible in Phoenix and UI audit trail

### 15.2 Safety Gates (Hard — Auto-Promotion Only If All Pass)
Per the v2 rubric, hard gates are binary and never averaged in. Auto-promotion requires **all** of:
- ✅ J1 Safety hard gate: 100% PASS on held-out subsample (no PII, disclaimer present, no guarantee claims)
- ✅ J2 Hallucination & Internal Consistency hard gate: 100% PASS on held-out subsample (every citation traces; no contradictions)
- ✅ `weighted_quality` summary metric on held-out subsample ≥ v(n-1) `weighted_quality` (i.e. no regression in the composite)
- ✅ No individual weighted dimension drops > 10% from v(n-1) baseline (per-dimension regression check, AlphaEval principle)
- ✅ Adversarial Reviewer's critique severity score does not regress
- ✅ Diff is bounded (≤ 200 token change per prompt patch)
- ✅ Rate limit: ≤ 5 promotions per 24h

If gates fail → archived with full audit; user can manually override.

### 15.3 Rollback
- Every promoted version is checkpoint-saved (git + Phoenix prompts)
- One-click rollback in UI
- Auto-rollback triggers on **any** of: (a) `weighted_quality` drop > 10% across the next 10 production runs, (b) a single J1 Safety FAIL, (c) a single J2 Hallucination & Internal Consistency FAIL. Hard-gate FAIL is zero-tolerance — one strike triggers rollback.

### 15.4 The Demo Showcase
Over 20 days, learning loop runs **~200 iterations**. Demo shows:
- Composite score over time, version stamps
- Prompt evolution: v1 vs v8 with annotated changes
- Per-insurer playbook divergence

No other Arize-track submission will have this data wall.

## 16. Full-Plan Demo Strategy (3 minutes, Audacious)

| Time | Beat | Screen |
|---|---|---|
| 0:00–0:15 | Audacious claim | *"I'm a PM in India. Twenty days ago I'd never read a US insurance denial letter. Today, this swarm of 12 agents wins ~78% of the appeals I throw at it — because Phoenix taught them how."* |
| 0:15–0:40 | Show the swarm | Architecture diagram animates: case enters Triage, fans out to 4 Researchers in parallel, Strategist synthesizes, Drafter writes, Red Team attacks, Drafter iterates. Phoenix dashboard ticks in background |
| 0:40–1:10 | Hero case live | Real Cigna mental-health denial (synthetic). Watch all 12 agents play roles. Final appeal: composite 0.75, simulator APPROVE |
| 1:10–1:50 | Learning loop is protagonist | Phoenix UI: timeline of 8 prompt versions over 20 days. Click v1 vs v8 prompt diff. Learning Coordinator audit log: *"Patch promoted day 12: Cigna mental-health, added MHPAEA parity citation rule. Composite lift +14%. Auto-promoted."* |
| 1:50–2:20 | The benchmark | Chart: composite on 40-case held-out across 8 versions. ~0.40 → ~0.75. Per-insurer breakdown. Safety stable. Hallucination 0 |
| **2:20–2:50** | **Counterfactual (mic drop)** | **Disable Phoenix MCP. Composite collapses to 0.42.** *"Without Phoenix, the swarm forgets everything it learned. Phoenix isn't a sidecar. It's the swarm's nervous system."* |
| 2:50–3:00 | Close | *"This is what self-improving agents actually look like. Aegis. Built in 20 days. Open source. Apache 2.0."* |

## 17. Full-Plan Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| **R1 — Multi-agent coordination eats time** | High | Strict ADK sub-agent pattern; no creative coordination; LangGraph only if forced |
| **R2 — Learning loop doesn't improve** | High | Run learning loop EARLY (day 8, not day 16); time to fix eval signals if noisy |
| **R3 — Auto-promotion promotes something stupid** | Medium | Hard safety gates (§15.2); user-visible audit log; one-click rollback |
| **R4 — Token cost climbs** | Medium | Cap Gemini spend at $200; Flash for cheap roles (Triage, Adversarial), Pro for expensive (Strategist, Drafter) |
| **R5 — Demo video looks rushed** | Medium | Budget 3 full days (18, 19, 20) for video; pre-record everything; no live demo |
| **R6 — Judges think 12 agents is overkill** | Low | Lead with the *learning result*, not the agent count. Swarm is in service of the result |
| **R7 — Ethics/legal blowback** | Medium | Hard disclaimers everywhere; "simulated wins on synthetic benchmark" — never "wins real appeals" |
| **R8 — Phoenix Cloud free tier limits hit** | Low | Monitor usage; upgrade to paid if needed (<$50) |
| **R9 — Cloud Run cold start hurts demo** | Low | Min-instance count = 1 during demo period |
| **R10 — Non-American framing backfires** | Medium | Use the *learning-from-traces* framing, not *learned US law*; cite public sources visibly |

---

# Cross-Cutting Concerns (Apply to MVP and Full Plan)

## 18. Arize Rubric Alignment

- **Technical implementation**: Next.js + Python ADK + Phoenix MCP architecture.
- **Meaningful use of tracing and MCP**: Phoenix is structurally load-bearing; removing it degrades quality.
- **Quality of self-improvement loop**: Learning Coordinator meta-agent iteratively improves prompts/playbooks.
- **Overall impact**: Tackling a massive asymmetry in US healthcare where 99% of denials go unappealed.
- **Bonus**: The entire premise is an agent using its observability data to improve.

## 19. Hard Constraints (Both Phases)

These are locked-in regardless of phase:
- ✅ Apache 2.0 license
- ✅ Cloud Run hosting
- ✅ Next.js UI (no Streamlit)
- ✅ UX as a co-equal product pillar
- ✅ Synthetic composite cases (no PHI ever)
- ✅ Transparent two-step simulator with published rules
- ✅ Held-out benchmark for honest improvement reporting
- ✅ Safety disclaimers in UI/repo/video
- ✅ Google ADK + Gemini 3 + Phoenix MCP

## 20. Submission Deliverables (Devpost)
- Hosted project URL (Cloud Run)
- Public GitHub repo with Apache 2.0 license in About section
- ~3-minute demo video
- Devpost form
- Track: **Arize**

## 21. Required Disclaimers (Verbatim)

> **Aegis is a hackathon demonstration. It is not legal or medical advice. Outputs are intended as drafting assistance for human review. No real patient data (PHI) is used. The simulator is a transparent rule-based proxy, not a prediction of insurer behaviour.**

## 22. What Stays vs Changes Between Phases

| Decision | MVP (Part A) | Full Plan (Part B) |
|---|---|---|
| Agent count | 1 + 1 offline | 12 + 1 meta + 1 synthesizer |
| Insurers benchmarked | 3 | 10 |
| Denial types | 2 | 7 |
| Benchmark cases | 12 (6+6) | 100 (60+40) |
| Learning loop trigger | Manual, ~3 runs | Continuous, ~200 runs |
| Promotion gate | Human-approved | Auto-promote on gate pass + audit + rollback |
| Phoenix usage | Decorative + functional MCP read | Phoenix as swarm coordination memory |
| Demo improvement claim | +20% on 6 cases | Significant lift (e.g., ~0.40 → ~0.75 design target) |
| UX Priority | Functional utility | Premium consumer-grade |
| Build time | ~50 hours | ~160 hours (8 hrs/day × 20 days) |
| Pitch energy | Safe and credible | Audacious and category-defining |

## 23. Source References

- ProPublica *Denied* series — public reporting on insurance denials
- KFF (Kaiser Family Foundation) appeal-rate research
- Patient Advocate Foundation appeal templates (public)
- State insurance commissioner public complaint databases
- Healthcare.gov appeal-rights educational pages
- Reddit r/HealthInsurance (public posts; inspiration only, not copied)
- [docs/research/impact-stats.md](../research/impact-stats.md)
- [docs/research/assumption-map.md](../research/assumption-map.md)
- [docs/design-brief.md](../design-brief.md)
- [docs/challenge.md](../challenge.md)

## 24. Open Questions

See [docs/open-questions.md](../open-questions.md). Must be resolved before code begins.

## 25. Out-of-Scope Ideas (Post-Hackathon Backlog)

- External / IRO appeals automation
- Medicare appeals (different stack, ALJ hearings)
- Mobile / WhatsApp interface
- Multi-language (Spanish first, given US Hispanic patient population)
- Provider-facing version
- Real insurer portal integrations
- Outcome-tracking dashboard
- India variant (Bima-Mitra adapted to IRDAI/Ombudsman flow)

---

## 26. The Bet

Two paths exist within this PRD:
- **Part A optimizes for *not losing*.** Ships a credible, complete Arize-track submission by Day 7.
- **Part B optimizes for *winning by a landslide*.** Builds on Part A through Day 20.

In a hackathon with 6 separate $5,000 buckets, "not losing" gets you 3rd place at best. **Winning** requires being the one submission judges talk about after the event. That requires audacity.

You have 20 days. You have a vibe-coding stack that turns a PM into an effective builder. **Build the Full Plan, with the MVP as your Day 7 safety net.**

Aegis isn't a hackathon submission. It's a manifesto: *agents should improve from their own observability data, autonomously, with safety gates, in production.* That's the Arize thesis. Be the one team that actually built it.
