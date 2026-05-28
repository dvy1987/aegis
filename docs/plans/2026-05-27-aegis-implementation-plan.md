# Implementation Plan — Aegis (Day 1 – Day 20)

| | |
|---|---|
| **Project** | Aegis — self-improving multi-agent system for US health-insurance appeal drafting |
| **Plan version** | v1.0 (2026-05-27, Session 5) |
| **Author** | Droid (skill: `implementation-plan`) |
| **Source artifacts** | [PRD v4 §14](../prd/PRD.md) · [Architecture spec](../architecture/2026-05-27-aegis-arch.md) · [Eval pipeline](../evals/2026-05-27-aegis-eval-pipeline.md) · [Eval rubric v2](../evals/2026-05-27-aegis-appeal-rubric.md) · [Assumption map](../research/assumption-map.md) · [Product soul](../product-soul.md) · [ADR-001..005](../adr/) |
| **Companion** | [`2026-05-27-aegis-implementation-tasks.md`](2026-05-27-aegis-implementation-tasks.md) — flat agent-pickable task list |
| **Constitution** | None yet (see Open Item below). PRD FR/NFR/G/SC IDs used for traceability. |
| **Status** | Draft — pending PM sign-off on Phase 0 (GCP + Phoenix setup) |

---

## 1. Executive Summary

Build Aegis in two nested phases over 20 days:

- **Part A (Days 1–7)** — single ADK agent + 7 tools + 12-case benchmark + Phoenix MCP load-bearing. Shippable as a credible Arize-track submission on Day 7 (safety net).
- **Part B (Days 8–20)** — decompose into 12-agent swarm, expand to 100-case benchmark, ship the autonomous Learning Coordinator with hard safety gates + auto-rollback. This is the win-condition.

Daily work pattern: morning = build, afternoon = eval, end-of-day = commit + handoff. Assumption tests A1–A5 are scheduled as **hard go/no-go gates** at Days 2, 3, 5, 7, 10, and 15 — failure of any gate escalates to PM with options, not silent downscope.

**Rolling demo capture:** The demo's hero arc (agent getting better over time) requires capturing the *weak* v1 output while it still exists. Demo footage is captured throughout the build at key milestones, not just at the end. See [`docs/demo/rolling-capture-checklist.md`](../demo/rolling-capture-checklist.md) for the PM-friendly step-by-step guide. Capture points: Day 3 (first v1 run), Day 5 (v1 vs v2 eval), Day 7 (MVP full walkthrough = safety-net demo), Day 10 (swarm first run), Day 14 (benchmark improvement arc), Day 17 (counterfactual). Days 18-19 are editing and voiceover only — all footage already captured.

The plan is structured so each day has a demoable deliverable, every task has an explicit Definition of Done, and every task traces back to a PRD FR/NFR/G/SC identifier.

## 2. Technical Stack (fixed, from AGENTS.md + ADRs)

| Layer | Tool | ADR |
|---|---|---|
| Frontend | Next.js (App Router) + Tailwind + shadcn/ui + framer-motion + Lucide React | [ADR-003](../adr/) |
| Backend / agent runtime | Python 3.11 + `uv` + FastAPI + Google ADK | [ADR-001](../adr/) |
| Dev workflow | `google-agents-cli` (`uvx google-agents-cli setup`) | [ADR-005](../adr/) |
| LLM | Gemini 3 (fallback: Gemini 2.5) | PRD §19 |
| Observability + evals | Arize Phoenix Cloud (free tier; $50 ceiling approved) | [ADR-002](../adr/) |
| Runtime introspection | `@arizeai/phoenix-mcp` | [ADR-002](../adr/) |
| Instrumentation | `openinference-instrumentation-google-adk` | [ADR-002](../adr/) |
| Hosting | Google Cloud Run (2 services: frontend + backend) | PRD §19 |
| Retrieval | BM25 (`rank_bm25`) over local markdown corpus | backend/AGENTS.md |
| Storage | Local files + GCS JSON for promoted playbooks | PRD §19 |
| License | Apache 2.0 | PRD §19 |

## 3. Architecture Overview

Two-service Cloud Run deployment:

```
[Next.js frontend] --HTTPS--> [FastAPI backend hosting ADK agent(s)]
        |                              |
        |                              +--> Phoenix Cloud (traces, evals, experiments, prompts)
        |                              +--> Phoenix MCP (runtime trace introspection)
        |                              +--> Local corpus (BM25) + Playbooks (versioned JSON)
        +-----visible Phoenix links in UI------+
```

- **Part A:** one ADK Orchestrator with 7 tools (case_parser, corpus_retrieval, phoenix_mcp_lookup, playbook_loader, drafter, self_check, simulator).
- **Part B:** 14 components total — 10 LLM agents (Triage, Orchestrator, 5 Researchers, Strategist, Drafter, Adversarial Reviewer) + 1 Quality Judge Panel (7 LLM judges) + 1 Outcome Simulator + 2 meta-agents (Learning Coordinator, Pattern Synthesizer). See [architecture spec §3](../architecture/2026-05-27-aegis-arch.md).

---

## 4. Phased Breakdown

### Phase 0 — Prerequisites & Environment Setup (Day 0 / pre-build)

**⚠ STOP-AND-ASK gate before executing this phase.** PM is non-technical; backend/cloud setup is plain-English-explained first.

| Task | Description | DoD | Traces to |
|---|---|---|---|
| T0.1 | Resolve open blockers in `docs/open-questions.md` (J1 observability conflict, J2 deploy compat, account creation, account limits) | All 🔴 BLOCKER items closed or explicitly deferred with rationale | PRD §24 |
| T0.2 | Google Cloud project created; billing alert at $30; `gcloud auth login` works locally; Cloud Run + Artifact Registry APIs enabled | `gcloud projects describe aegis-hackathon` succeeds | G1 |
| T0.3 | Phoenix Cloud account created; API key in local `.env` (gitignored); `PHOENIX_API_KEY` resolves in a Python shell | `from phoenix.otel import register; register()` runs without error | G2, FR5 |
| T0.4 | `git init` clean checkpoint + initial push to `origin/main` (or new public repo if not yet created); Apache 2.0 LICENSE file at root visible | `git log` shows ≥1 commit on `origin/main` | G6 |
| T0.5 | Install `uv`, `uvx`, `google-agents-cli`; run `uvx google-agents-cli setup` and confirm 7 ADK skills appear | `agents-cli --version` succeeds; `/skills` shows the 7 bundled skills | backend/AGENTS.md |
| T0.6 | Pre-commit hook for PHI/secret scan installed and tested with a deliberately bad string | A commit containing a fake SSN gets rejected | NFR3 |

**Phase 0 exit gate:** All 6 tasks pass. PM has signed off on cloud-spend posture. Phoenix dashboard visible in browser.

---

### Phase 1 — MVP (Days 1–7) — Single Agent + Benchmark + Phoenix MCP Loop

> **Goal:** Day 7 = Aegis MVP is fully submittable as a standalone Arize-track entry.
> **Hard gates this phase:** A2 (Day 2), A4 (Day 2 EOD), A3 (Day 3), A1 (Day 5).

#### Day 1 — Scaffold + A4 Integration Spike
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T1.1 | `agents-cli create aegis-backend` scaffold inside `backend/`; FastAPI `/health` endpoint returns 200 | `curl localhost:8000/health` returns `{"ok":true}` | G1 |
| T1.2 | Next.js scaffold inside `frontend/` (Tailwind + shadcn/ui + framer-motion + Lucide installed) | `pnpm dev` serves a hero page on `localhost:3000` | G8, FR10 |
| T1.3 | Wire `openinference-instrumentation-google-adk`; instantiate a stub "echo agent"; emit ≥1 trace to Phoenix Cloud | One trace visible in Phoenix UI tagged `aegis-hackathon` | G2, NFR4 |
| T1.4 | **A4 spike — part 1:** Configure `@arizeai/phoenix-mcp` server as an ADK tool; toy "query my own traces" call returns a structured summary | MCP roundtrip latency logged; result printed to stdout in structured form | A4, FR5 |
| T1.5 | Resolve J1 (`google-agents-cli` observability skill vs Phoenix MCP) — confirm both can coexist or document the workaround | Note added to backend/AGENTS.md + decision logged | open-q J1 |

**End-of-day commit:** `Day 1: backend + frontend scaffold + Phoenix instrumentation`.

**Demo capture (rolling):** No capture yet — no agent output exists.

#### Day 2 — A2 + A4 Final Go/No-Go
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T2.1 | **A4 spike — part 2:** Run 20 MCP queries; record p50/p95 latency, structured-output reliability. **EOD go/no-go decision.** | If p95 > 10s or unstructured > 20% → escalate to PM with fallback options | A4 |
| T2.2 | **A2 Phoenix UI study:** Watch official Phoenix demos, scroll docs, manually use Experiments/Traces/Evals/Datasets/Prompts UI. Storyboard the 3 demo-load-bearing screens. | `docs/demo/phoenix-shotlist.md` drafted (3 surfaces × ≥20s each) | A2, G5 |
| T2.3 | Build the local corpus seed (~30 docs): public ERISA §503/2719 text, Aetna/Cigna/UHC appeal-instructions, AMA/InterQual/MCG summaries (public), No Surprises Act FAQs, MHPAEA basics | `corpus/authorities/` populated; BM25 returns ≥3 hits for a test query like "medical necessity appeal Cigna" | FR3 |
| T2.4 | Draft 2 calibration cases (1 insurer × 2 denial types) using provenance template; show 2 to outside readers (start A3) | 2 case files in `eval/cases/train/`; `eval/dataset_card.md` initialised | FR8, NFR3, A3 |

**Hard gate (EOD Day 2):** A4 PASS → continue. A4 FAIL → PM escalation; fallback is Phoenix SDK direct calls and softening the "Phoenix MCP load-bearing" pitch.

**Demo capture (rolling):** No capture yet — agent doesn't run until Day 3.

#### Day 3 — A3 Validation + First End-to_End Agent
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T3.1 | **A3 Reader test:** show 3 cases to 2 outside readers; if either flags "feels fake / too clean" → re-source with more public denial-letter language | Both readers describe cases as "plausible" / "scary realistic" — yes/no recorded in `eval/dataset_card.md` | A3 |
| T3.2 | Draft 2 held-out cases (distinct from train) — composite from different public sources | 2 case files in `eval/cases/holdout/`; provenance documented | FR8 |
| T3.3 | Build single ADK agent in `backend/src/agent/aegis_v1.py` with 7 tools (case_parser, corpus_retrieval, phoenix_mcp_lookup, playbook_loader, drafter, self_check, simulator); deliberately weak v1 prompt | First end-to-end run on 1 calibration case produces a structured `AppealPackage` JSON | FR1, FR2, FR3, FR4, FR6, FR7 |
| T3.4 | Strict JSON output enforced (`response_mime_type="application/json"`); Pydantic schemas in `backend/src/agent/schemas.py` | Schema validation passes on the Day-3 output | NFR4 |

**Hard gate (EOD Day 3):** A3 PASS → continue. A3 FAIL → swap cases or move to real-anonymised public denial letters.

**🔴 Demo capture (rolling — CRITICAL, cannot be recreated later):** Record the first v1 agent run. Open two browser windows: Aegis app (left) + Phoenix dashboard (right). Load a calibration case, run the agent, capture the weak v1 appeal output + low eval scores + simulator DENY. Switch to Phoenix, show the trace. Save as `docs/demo/raw/day3-v1-first-run.mp4`. See [rolling-capture-checklist.md](../demo/rolling-capture-checklist.md) for step-by-step instructions.

#### Day 4 — Phoenix MCP Wired Load-Bearing
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T4.1 | Phoenix MCP call inserted into agent's pre-draft step (FR5): query `traces WHERE insurer=X AND denial_type=Y` → structured failure-pattern summary feeds into prompt | A trace shows the MCP query, the response, and the prompt augmentation step | FR5 |
| T4.2 | Counterfactual harness: env-flag `PHOENIX_MCP_ENABLED=false` to bypass MCP; record difference in output | Toggle works; difference is logged for later demo measurement | PRD §16 counterfactual |
| T4.3 | Trace metadata enforced: `case_id, insurer, denial_type, plan_type, state, prompt_version, playbook_version, dataset_split, run_mode` on every trace | Phoenix UI shows all 9 metadata fields populated | NFR4 |
| T4.4 | First 2 playbooks scaffolded in `playbooks/` (Cigna-medical-necessity, Aetna-prior-auth); versioned JSON | `playbook_loader` tool retrieves them by `(insurer, denial_type)` | FR4 |

#### Day 5 — Judges + A1 Eval Signal Gate
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T5.1 | Implement Layer 1 deterministic checks per [eval pipeline](../evals/2026-05-27-aegis-eval-pipeline.md): regex PHI, disclaimer string-match, length, tool-call JSON validity | All 4 checks pass on the v1 output; fail-injected outputs are correctly rejected | NFR2, FR7 |
| T5.2 | Implement 5 of 7 LLM judges as Phoenix Evals: J1 Safety (gate), J2 Hallucination & Internal Consistency (gate), J3 Grounding, J4 Case Specificity, J5 Evidence Completeness — judge model = Claude 4 or GPT-5 (cross-model) | Eval call returns rubric-shaped JSON; Phoenix UI shows the eval run | FR7 |
| T5.3 | Calibration: hand-score 2 calibration cases on each judge dimension; compute Cohen's κ; reject any judge with κ < 0.6 (advisory only until fixed) | `eval/calibration_log.md` records κ per judge; only κ≥0.6 judges count toward promotion gates | rubric §calibration |
| T5.4 | **A1 Eval Signal Gate:** run v1 (weak prompt) vs v2 (hand-tuned insurer-specific prompt) on 2 held-out cases. If `weighted_quality` lift < +15% on 2 cases OR judge re-run std-dev > ±0.08 → escalate to PM (kill or recalibrate). | A1 PASS or FAIL recorded in `eval/calibration_log.md` | A1, SC1 |

**Hard gate (EOD Day 5):** A1 PASS → continue MVP build. A1 FAIL → PM call: recalibrate eval, kill learning-loop pitch, or both.

**Demo capture (rolling):** Record the v1 vs v2 eval comparison. Open Aegis app (left) + Phoenix Experiments (right). Show score delta between v1 (weak) and v2 (hand-tuned). Show the v2 appeal citing plan language. Show simulator outcome improvement. Save as `docs/demo/raw/day5-v1-vs-v2-eval.mp4`.

#### Day 6 — Frontend Workbench + 2 Remaining Judges
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T6.1 | Implement J6 Insurer Tactic Alignment + J7 Persuasive Coherence judges | All 7 judges run end-to-end on a hero case in <90s | rubric §weighted dims |
| T6.2 | Next.js MVP workbench page: case selector (4 cases), v1/v3 toggle, side-by-side appeal output, eval score panel, simulator outcome, Phoenix Cloud deep-links | Local demo run with 1 hero case shows all 5 UI regions populated | FR10, G8 |
| T6.3 | Tone + accessibility pass per [design brief](../design-brief.md) §4 + §8: calm copy, no exclamation marks, AA contrast minimum, focus rings, no AI marketing voice, "person" not "human" | Lighthouse a11y score ≥ 90; copy review passes against design-brief checklist | NFR7, G8 |
| T6.4 | J2-style verification: J1+J2 deterministic gates short-circuit cheap checks before invoking LLM judges | Cost log shows hard-gate FAIL skips the 5 weighted judges | rubric §cost |

#### Day 7 — MVP Milestone (Cloud Run + Submission-ready)
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T7.1 | `agents-cli deploy` (or manual Cloud Build) deploys backend to Cloud Run; verify J2 (deploy compat for 2-service Cloud Run) | Backend reachable on a Cloud Run URL; first end-to-end run from Next.js → backend → Phoenix completes | open-q J2 |
| T7.2 | Deploy Next.js as the second Cloud Run service; configure CORS + environment variables | Hosted URL serves the workbench end-to-end on a hero case in <60s | G1, NFR6 |
| T7.3 | Manual learning loop (`backend/learn.py`): pull v1 failed traces from Phoenix MCP, propose 1 prompt patch, run as Phoenix Experiment on held-out 6 cases, present in UI for human approval, version-bump on approval | One v1→v2→v3 promotion run end-to-end, all approvals captured | FR9 |
| T7.4 | **MVP eval run:** full 12-case benchmark, v1 vs v3. Record `weighted_quality`, hard-gate PASS rates, latency p95. Save Phoenix experiment URL. | SC1 +20% lift achieved? SC2/SC3 100% PASS? SC5 trace completeness 100%? — yes/no logged | SC1, SC2, SC3, SC5 |
| T7.5 | MVP-only Devpost draft ready (safety-net submission text + 3-min demo script per PRD §9) | `docs/demo/mvp-script.md` reviewed by PM | G5, G7 |

**🎯 Milestone 1 (Day 7):** Aegis MVP is shippable as a complete Arize-track submission. If anything from Day 8+ fails, this is the safety-net submission.

**🔴 Demo capture (rolling — SAFETY-NET DEMO):** Record a full v1→v3 walkthrough on the hero case. This footage can be edited into a complete 3-minute MVP demo if Days 8+ fail. Open Aegis app (left) + Phoenix (right). Walk through: v1 weak appeal → Phoenix MCP failure summary → approved patch → v3 strong appeal → score jump → simulator flip from DENY to APPROVE → benchmark chart. Save as `docs/demo/raw/day7-mvp-full-walkthrough.mp4`.

---

### Phase 2 — Part B Swarm (Days 8–14) — 9-Agent Decomposition + 60-Case Benchmark

> **Hard gates this phase:** Day 10 progress gate ([ADR-004](../adr/)), Day 10 A5 autonomy go/no-go, demo-coherence pre-check on Day 14.

#### Day 8 — Decompose Single Agent into Triage + Strategist + Drafter
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T8.1 | Split `aegis_v1.py` into ADK Coordinator (Orchestrator) + 3 sub-agents per the [v1 role prompts](../../backend/src/prompts/) | Orchestrator routes 1 calibration case Triage → Strategist → Drafter; traces show 3 distinct agent spans | PRD §12.1 |
| T8.2 | Migrate prompts from monolithic to `backend/src/prompts/*_v1.md` (already drafted in Session 5) — register each as a Phoenix Prompt with version | Phoenix Prompts UI shows 3 versioned prompts | PRD §12.2 |
| T8.3 | Re-run 12-case benchmark on 3-agent decomposition; record regression vs MVP single-agent | Composite within ±5% of Day 7 baseline (decomposition shouldn't hurt yet) | SC1 |

#### Day 9 — Insurer Intelligence Agent (Phoenix MCP Heavy User)
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T9.1 | Add Insurer Intelligence Agent (Phoenix-MCP-first) per `insurer_intelligence_v1.md`; queries past traces by `(insurer, denial_type, state)` | Agent outputs `InsurerBrief` JSON; trace shows MCP call with structured response | PRD §12.2 #3, FR5 |
| T9.2 | Add 5th playbook (UHC mental-health-parity) for swarm variety | `playbooks/uhc__mhpaea.json` retrieved by playbook_loader | FR4 |

#### Day 10 — Specialist Researchers (Policy Detective, Medical Necessity, Legal) + GATE
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T10.1 | Add Policy Detective + Medical Necessity Researcher + Legal Researcher as ParallelAgent fan-out from Orchestrator | One end-to-end run completes with 5 specialists writing briefs in parallel; latency p95 < 90s | PRD §12.2 #4–6, NFR6 |
| T10.2 | Expand benchmark to 40 cases (+28 from MVP 12) | `eval/cases/train/` + `eval/cases/holdout/` total 40; dataset_card updated | PRD §13.5 |
| T10.3 | **Day 10 Progress Gate ([ADR-004](../adr/)):** are ≥5 of 9 specialist agents shipping credible briefs? If <5 → escalate to PM with leaner-topology options | Gate status (PASS/FAIL) logged in `docs/memory/decision-log.md` with evidence | ADR-004 |
| T10.4 | **A5 Autonomy Spike:** stub Learning Coordinator on 3 failed traces; manually verify it can produce a credible patch candidate. EOD go/no-go on autonomous loop. | If ≥1-in-5 hit rate looks unattainable → escalate, fall back to human-approval flow | A5 |

**Hard gate (EOD Day 10):** Day 10 + A5 both PASS → continue Part B as designed. Either FAIL → PM escalation with options per Code-Wall Protocol.

**Demo capture (rolling):** Record the swarm first run. Open Aegis app (left) + Phoenix Traces (right). Show the 9-agent fan-out, parallel researcher briefs, and the trace waterfall. If Learning Coordinator has proposed its first patch, capture that in Phoenix. Save as `docs/demo/raw/day10-swarm-first-run.mp4`.

#### Day 11 — Precedent Miner + Benchmark to 60
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T11.1 | Add Precedent Miner agent (state insurance commissioner decisions, public IRO decisions, ProPublica *Denied* cases) | Brief includes ≥1 traceable precedent per case | PRD §12.2 #7 |
| T11.2 | Expand benchmark to 60 cases (training-side priority) | 60 case files; provenance entry per case in dataset_card | PRD §13.5 |
| T11.3 | Mid-Part-B regression run on 40-case held-out subset | `weighted_quality` ≥ Day 7 MVP baseline; no hard-gate FAIL spike | SC1 |

#### Day 12 — Adversarial Reviewer + Iteration Loop
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T12.1 | Add Adversarial Reviewer agent per `adversarial_reviewer_v1.md`; if `severity > 0.6`, loop back to Drafter (max 1 iteration) | Iteration loop visible in traces; severity score recorded | PRD §12.2 #10 |
| T12.2 | Adversarial severity becomes a tracked dimension in the eval rubric | Phoenix UI shows severity time-series | rubric §weighted |

#### Day 13 — Quality Judge Panel (Full 7-Judge Wiring)
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T13.1 | Wire the 7-judge panel as a Phoenix Eval suite running on every Part B run; verify the 2 hard gates run first (short-circuit) | Cost per letter ≈ $0.10 as predicted in rubric §cost; Phoenix Evals UI shows the panel | rubric §cost, FR7 |
| T13.2 | Outcome Simulator (Part B variant) — per-insurer tuned rules; transparent two-step (LLM feature extract + deterministic scoring) | Simulator outputs APPROVE/DENY + explanation traceable to `eval/simulator_rules.json` | FR8 |

#### Day 14 — Milestone 2 + Demo-Coherence Pre-Check
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T14.1 | Full 60-case benchmark run; record `weighted_quality` v1→v_current, per-dimension scores, hard-gate PASS rates | All metrics dumped to `eval/benchmark-runs/2026-XX-XX-day14.json` | SC1 |
| T14.2 | **Demo-coherence pre-check (ADR-004 trigger):** can you tell the v1→v_n story end-to-end in ≤3 min with current artifacts? If not → escalate | `docs/demo/day14-script-draft.md` reviewed by PM | ADR-004 |
| T14.3 | Frontend polish pass #1: animated architecture diagram, agent-status streaming, Phoenix link-out for each agent | Hero case run shows 9-agent activity in real time | G8 |

**🎯 Milestone 2 (Day 14):** 9-agent swarm + 60-case benchmark shippable. If Days 15–20 fail, this submits.

**Demo capture (rolling):** Record the benchmark improvement arc. Open Aegis app (left) + Phoenix Experiments + Prompts (right). Show the prompt version timeline (v1→v_current), click a diff (e.g., added MHPAEA citation rule), show the experiment score climbing version by version, show the benchmark chart. Capture the "learning loop is protagonist" beat. Save as `docs/demo/raw/day14-benchmark-arc.mp4`.

---

### Phase 3 — Learning Loop + Polish (Days 15–20)

> **Hard gates this phase:** Day 15 demo-coherence formal pass; Day 18 promotion-gate stability; Day 19 demo lock.

#### Day 15 — Learning Coordinator + Demo-Coherence Formal Check
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T15.1 | Implement Learning Coordinator meta-agent: wakes hourly, queries Phoenix MCP for sub-0.6 traces, generates 1–3 candidate patches per slice, each candidate becomes a Phoenix Experiment | First autonomous experiment run end-to-end; patches archived with reason | PRD §15.1 |
| T15.2 | Implement the 6 hard safety gates per PRD §15.2 (binary; rubric v2): J1 PASS, J2 PASS, no weighted_quality regression, no per-dim drop > 10%, adversarial severity stable, diff ≤ 200 tokens, ≤ 5 promotions / 24h | Patch that fails any gate is rejected with audit; one that passes all 6 auto-promotes | PRD §15.2 |
| T15.3 | **Demo-coherence formal check ([ADR-004](../adr/)):** 3-minute walkthrough rehearsal against current build. If story doesn't hold → escalate | PM signs off on the rehearsal video | ADR-004 |

#### Day 16 — Learning Loop Iterations 1–4
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T16.1 | Run 4 learning iterations: Cigna medical-necessity, UHC prior-auth, Aetna mental-health-parity, Anthem step-therapy | Each iteration logged in Phoenix Experiments; promotions/archives all visible in audit | PRD §14 Day 16 |
| T16.2 | Auto-rollback test: deliberately push a regressing patch through the gates as a dry-run; confirm auto-rollback triggers per §15.3 | Rollback log entry created; previous version restored | PRD §15.3 |

#### Day 17 — Pattern Synthesizer + 100-Case Benchmark + Counterfactual
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T17.1 | Pattern Synthesizer post-run agent: summarises meta-patterns across insurers; output writes to inherited meta-playbook | Meta-playbook updates visible across multiple slices; trace shows synthesis step | PRD §12.2 +Pattern |
| T17.2 | Expand benchmark to 100 cases (60 train + 40 held-out) | All 100 cases in `eval/cases/`; dataset_card complete | PRD §13.5 |
| T17.3 | Learning iterations 5–8 | 4 more iterations promoted/archived | PRD §14 Day 17 |
| T17.4 | **Counterfactual recording:** Run with `PHOENIX_MCP_ENABLED=false`, capture quality collapse. Open Aegis app (left), run same hero case with Phoenix off, show generic appeal + low score + simulator DENY. Save as `docs/demo/raw/day17-counterfactual.mp4` | Clip shows quality collapsing when Phoenix MCP is disabled | PRD §16, FR5 |

#### Day 18 — Polish + v1→v8 Comparison Chart
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T18.1 | Frontend polish pass #2: full design-brief compliance, motion design pass, accessibility AAA where possible, copy review | Lighthouse perf ≥ 90, a11y ≥ 95, Best Practices ≥ 95 | NFR7, G8 |
| T18.2 | v1→v8 comparison chart in UI (composite over time, per-insurer breakdown, prompt diff viewer) | Chart visible in Next.js workbench; reads from Phoenix Prompts versions | PRD §15.4 |
| T18.3 | Min-instance=1 on Cloud Run for demo period; cost cap reverified | `gcloud run services describe` shows min instances; spend dashboard < $50 | NFR5 |

#### Day 19 — Demo Recording + Edit
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T19.1 | Record 3-min demo per PRD §16 script: hook → swarm reveal → hero case → learning loop → benchmark chart → counterfactual mic-drop → close | Raw recording stored locally; Phoenix UI visible ≥60s of 180s as measured | G5, A2 |
| T19.2 | Edit + caption + 1080p export; soft-numbers verified (no "wins 78%" without "simulated on synthetic benchmark") | Final MP4 in `docs/demo/aegis-final.mp4`; tone-guardrail review PASS | NFR2 |

#### Day 20 — Final Benchmark + Devpost Submission
| Task | Description | DoD | Traces to |
|---|---|---|---|
| T20.1 | Final 100-case benchmark run; freeze metrics for submission | Final numbers in `eval/benchmark-runs/2026-XX-XX-final.json` and pinned in README | SC1–SC5 |
| T20.2 | README + Devpost fields: hosted URL, GitHub URL with Apache 2.0 visible, video URL, track=Arize | Devpost form submitted; confirmation email | G6, G7 |
| T20.3 | Tag repo `v1.0-aegis-final`; final commit; final memory-handoff entry | Tag visible on `origin/main`; `docs/memory/agent-handoffs.md` closes Session N | (housekeeping) |

**🎯 Milestone 3 (Day 20):** Full Plan shipped. Devpost submitted. Final benchmark frozen.

---

## 5. Risk & Mitigation

| Risk | Severity | Mitigation |
|---|---|---|
| **R-PLAN-1** Phoenix MCP+ADK integration breaks (A4 FAIL) | High | Day 1–2 spike isolates this risk; fallback = Phoenix SDK direct calls + softened MCP-load-bearing pitch |
| **R-PLAN-2** Eval signal too noisy (A1 FAIL) | High | Day 5 hard gate; fallback = harder cases, fewer judges, longer calibration |
| **R-PLAN-3** Synthetic cases read as toy (A3 FAIL) | High | Day 3 reader test; fallback = real anonymised letters from public sources |
| **R-PLAN-4** Day 10 progress gate: <5 of 9 specialist agents credible (ADR-004) | High | Documented escalation in ADR-004; lean topology (5-agent) is the pre-approved fallback |
| **R-PLAN-5** A5 Learning Coordinator can't auto-generate credible patches | High | Day 10 go/no-go; fallback = keep loop human-approved (MVP-style), keep §15 visible as roadmap |
| **R-PLAN-6** Phoenix Cloud free-tier limit hit mid-build | Medium | Monitor on Day 7 + Day 14; upgrade approved up to $50 |
| **R-PLAN-7** Cost overrun on Gemini API | Medium | Cap at $200; Flash for cheap roles (Triage, Adversarial), Pro for Strategist/Drafter |
| **R-PLAN-8** Cloud Run cold start during recording | Medium | Min-instance=1 from Day 18; pre-warm before recording |
| **R-PLAN-9** Demo coherence fails Day 15 check | Medium | Pre-check Day 14, formal check Day 15; if FAIL → escalate, drop to MVP-style demo with what's working |
| **R-PLAN-10** Tone guardrail breach in any artifact | Low | Pre-merge check on every PR; root AGENTS.md + design-brief §8 |
| **R-PLAN-11** PM time slippage (life happens) | Medium | Daily working-commit discipline; MVP-as-safety-net means losing a day still ships |

## 6. Timeline Estimate

| Phase | Days | Effort estimate | Output |
|---|---|---|---|
| Phase 0 (setup) | Day 0 / pre-build | S (4–6h) | GCP, Phoenix, repo init |
| Phase 1 (MVP) | Days 1–7 | M (~50h) | Single-agent + 12-case benchmark, shippable |
| Phase 2 (Swarm) | Days 8–14 | L (~60h) | 9-agent swarm + 60-case benchmark |
| Phase 3 (Learning + polish) | Days 15–20 | L (~50h) | Autonomous loop, 100-case benchmark, demo, submission |
| **Total** | **20 days** | **~160h** | Full Plan + MVP safety net |

T-shirt: **L** with a clearly-defined **M** safety net at Day 7.

---

## 7. Requirement Traceability

Subset showing the high-value links — every task above carries explicit IDs. (Full traceability is generated by `spec-crosscheck` when a feature-spec exists; this is a PRD-IDs traceability matrix in the interim.)

| Requirement | Tasks | Verification |
|---|---|---|
| **G1** (working agent on Cloud Run) | T0.2, T1.1, T7.1, T7.2 | End-to-end hosted call < 60s |
| **G2** (Phoenix instrumentation) | T1.3, T1.4, T4.1 | Trace visible in Phoenix Cloud |
| **G3** (Phoenix MCP runtime use) | T1.4, T4.1, T4.2, T9.1 | MCP query → prompt augmentation visible in trace |
| **G4** (v1→v3 measurable lift) | T5.4 (A1), T7.4 | SC1 ≥+20% on 6 held-out |
| **G5** (3-min demo video) | T2.2, T7.5, T19.1, T19.2 | MP4 with Phoenix on-screen ≥60s |
| **G8** (UX as first-class pillar) | T1.2, T6.2, T6.3, T14.3, T18.1 | Lighthouse a11y ≥90; design-brief compliance pass |
| **FR3** (BM25 corpus retrieval) | T2.3, T3.3 | ≥3 hits on test query |
| **FR5** (Phoenix MCP load-bearing) | T1.4, T4.1, T4.2, T9.1 | Counterfactual measurable: composite drops with MCP off |
| **FR7** (self-check + judges) | T5.1, T5.2, T13.1 | All 7 judges run; deterministic gates short-circuit |
| **FR8** (transparent simulator) | T2.4, T3.2, T13.2 | Simulator output traceable to `simulator_rules.json` |
| **FR9** (manual learning, Part A) | T7.3 | One v1→v2→v3 cycle with human approval logged |
| **NFR2** (safety disclaimer) | T5.1, T19.2 | String present in every output |
| **NFR3** (no PHI) | T0.6, T2.4 | Pre-commit hook + dataset_card provenance |
| **NFR4** (trace fidelity) | T3.4, T4.3 | 9 required metadata fields populated |
| **NFR6** (latency < 60s) | T7.2, T10.1, T13.1 | p95 latency under 60s in benchmark runs |
| **NFR7** (UX quality) | T6.3, T14.3, T18.1 | Design-brief compliance review |
| **A1** (eval signal) | T5.4 | Day 5 gate PASS |
| **A2** (Phoenix UI demo-viable) | T2.2, T19.1 | 3 surfaces × 20s on shotlist |
| **A3** (case credibility) | T3.1 | 2 outside readers PASS |
| **A4** (MCP+ADK integration) | T1.4, T2.1 | Day 2 EOD go/no-go PASS |
| **A5** (Learning Coordinator autonomy) | T10.4 | Day 10 EOD go/no-go PASS |
| **SC1** (≥+20% v1→v3) | T7.4, T20.1 | Final benchmark hit |
| **SC2** (Safety hard gate 100%) | T5.1, T13.1, T20.1 | All runs PASS J1 |
| **SC3** (Hallucination hard gate 100%) | T5.2, T13.1, T20.1 | All runs PASS J2 |
| **ADR-004** (12-agent revisit triggers) | T10.3, T14.2, T15.3 | Gate status logged at each trigger |
| **Open Q J1** (agents-cli vs Phoenix MCP) | T1.5 | Decision logged in backend/AGENTS.md |
| **Open Q J2** (deploy compat) | T7.1 | 2-service Cloud Run reachable |

---

## 8. Open Items the Plan Surfaces

1. **No `docs/constitution.md` exists yet.** Project rules live in [AGENTS.md](../../AGENTS.md). When `spec-driven-development` is run on a future feature, the constitution should be authored via `project-constitution` and this plan re-traced.
2. **Phase 0 needs PM go-ahead before execution** — explicit per the PM's instructions in Session 5.
3. **The autonomy ladder (Apprentice/Journeyman/Master)** referenced in PRD §16 and product-soul has thresholds TBD — those numbers depend on the calibrated rubric output and should be finalised at Day 5 once judge κ is measured.
4. **`feature-spec` was deferred in Session 1** — for any Part B agent whose behaviour materially changes, write a spec via `feature-spec` before code. This plan stands in for the MVP single-agent feature-spec until then.

---

## 9. Definition of Done — Whole Plan

- [ ] Phase 0 complete and PM-signed.
- [ ] All 5 assumption gates (A1–A5) recorded as PASS or escalated.
- [ ] Day 10 progress + A5 + Day 14 demo coherence + Day 15 demo coherence gates recorded.
- [ ] Final 100-case benchmark numbers frozen and pinned in README.
- [ ] Devpost submitted; repo public; Apache 2.0 visible in About; demo video < 3 min with Phoenix on-screen ≥60s.
- [ ] All commits clean; daily memory-handoff entries present.

---

## Impact Report

```
Plan complete: Aegis Day 1–20 implementation
Phases defined: 4 (0 setup + 3 build)
Total tasks: 67 (Phase 0: 6, Phase 1: 28, Phase 2: 16, Phase 3: 17)
Critical risks identified: 11 (R-PLAN-1..11)
Estimated effort: L (with M safety-net at Day 7)
Ready for: engineering execution (after PM signs off on Phase 0)
```
