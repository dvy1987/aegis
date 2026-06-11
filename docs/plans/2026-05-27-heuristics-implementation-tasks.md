# Heuristics — Agent-Pickable Task List (Day 1 – Day 20)

> Flat companion to [`2026-05-27-heuristics-implementation-plan.md`](2026-05-27-heuristics-implementation-plan.md). Each task is pickable by a single coding-agent session: clear DoD, traces to a PRD ID, no hidden dependencies.
>
> Status legend: `[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked / escalated
>
> When picking up a task, start by reading the linked DoD and traceability ID, then run `memory-startup` to load context. Commit at the end of each task with the task ID in the commit message (e.g. `T1.4: Phoenix MCP toy query roundtrip`).

---

## Phase 0 — Setup (STOP-AND-ASK gate)

- [ ] **T0.1** Resolve open blockers in `docs/open-questions.md` (J1, J2, accounts, scope). **DoD:** All 🔴 BLOCKER items closed or explicitly deferred. **Trace:** PRD §24.
- [ ] **T0.2** Create Google Cloud project; set $30 billing alert; `gcloud auth login`; enable Cloud Run + Artifact Registry APIs. **DoD:** `gcloud projects describe $GOOGLE_CLOUD_PROJECT` succeeds. **Trace:** G1.
- [ ] **T0.3** Sign up for Phoenix Cloud free tier; put `PHOENIX_API_KEY` in `.env`; verify in Python shell. **DoD:** `register()` succeeds. **Trace:** G2, FR5.
- [ ] **T0.4** Initial `git push` of clean checkpoint to `origin/main` with `LICENSE` (Apache 2.0). **DoD:** `git log` shows ≥1 commit on remote. **Trace:** G6.
- [ ] **T0.5** Install `uv`, `uvx`, `google-agents-cli`; run `uvx google-agents-cli setup`. **DoD:** `agents-cli --version` succeeds; 7 bundled skills visible. **Trace:** backend/AGENTS.md.
- [ ] **T0.6** Install pre-commit secret/PHI scan hook; test with a fake SSN. **DoD:** Bad commit rejected. **Trace:** NFR3.

---

## Phase 1 — MVP (Days 1–7)

### Day 1 — Scaffold + A4 spike
- [ ] **T1.1** `agents-cli create` backend scaffold; FastAPI `/health` returns 200. **DoD:** `curl localhost:8001/health` → `{"ok":true}` AND `curl localhost:8002/health` → `{"ok":true}`. **Trace:** G1.
- [ ] **T1.2** Next.js scaffold + Tailwind + shadcn/ui + framer-motion + Lucide. **DoD:** `pnpm dev` serves a hero page. **Trace:** G8, FR10.
- [x] **T1.3** Wire `openinference-instrumentation-google-adk` on a stub agent; emit ≥1 trace to Phoenix. **DoD:** Trace visible in Phoenix UI tagged `default`. **Trace:** G2, NFR4.
- [x] **T1.4** **A4 spike pt.1:** Configure `@arizeai/phoenix-mcp` as ADK tool; one toy query returns structured summary. **DoD:** MCP roundtrip latency logged; structured result in stdout. **Trace:** A4, FR5.
- [x] **T1.5** Resolve **Open-Q J1** (agents-cli observability vs Phoenix MCP). **DoD:** Note in backend/AGENTS.md + decision-log entry. **Trace:** Open Q J1.

### Day 2 — A2 + A4 go/no-go
- [x] **T2.1** **A4 spike pt.2:** Run 20 MCP queries; record p50/p95 latency + reliability. **DoD:** EOD go/no-go decision recorded; PM escalation if p95 > 10s. **Trace:** A4.
- [x] **T2.2** **A2 Phoenix UI study:** demos + docs + manual UI walk; draft `docs/demo/phoenix-shotlist.md` with 3 surfaces × ≥20s each. **DoD:** Shotlist exists with concrete screens. **Trace:** A2, G5.
- [x] **T2.3** Build local corpus seed (~30 public docs: ERISA §503/2719, insurer appeal instructions, MCG/InterQual, MHPAEA, NSA). **DoD:** BM25 returns ≥3 hits on a sample query. **Trace:** FR3.
- [x] **T2.4** Draft 2 calibration cases (1 insurer × 2 denial types) with provenance template; show 2 to outside readers (start A3). **DoD:** 2 case files in `eval/cases/train/`; dataset_card initialised. **Trace:** FR8, NFR3, A3.

### Day 3 — A3 reader test + first end-to-end agent
- [ ] **T3.1** **A3 Reader test:** 2 outside readers rate case realism. **DoD:** Both "plausible/realistic" or escalate to re-source. **Trace:** A3.
- [ ] **T3.2** Draft 2 held-out cases from distinct public sources. **DoD:** 2 cases in `eval/cases/holdout/` + provenance. **Trace:** FR8.
- [x] **T3.3** Build single ADK agent (`aegis_v1`) with 7 tools + deliberately-weak v1 prompt. **DoD:** End-to-end run on 1 case → structured `AppealPackage`. **Trace:** FR1, FR2, FR3, FR4, FR6, FR7. **Done 2026-05-28:** `backend/app/agent.py` now wires the 7 MVP tools as ADK `FunctionTool`s; local 7-tool smoke produced a structured `AppealPackage`.
- [x] **T3.4** Strict JSON output via `response_mime_type=application/json`; Pydantic schemas in `backend/src/agent/schemas.py`. **DoD:** Schema validation passes on Day-3 run. **Trace:** NFR4. **Done 2026-05-28:** schema source lives at `backend/app/aegis_v1/schemas.py`; ADK `output_schema=AppealPackage` and JSON MIME configured.
- [ ] **🔴 T3.5** **Demo capture: first v1 run.** Open Heuristics app (left) + Phoenix dashboard (right). Load a calibration case, run v1 agent, capture the weak appeal output + low eval scores + simulator DENY + Phoenix trace. **DoD:** `docs/demo/raw/day3-v1-first-run.mp4` saved. **Trace:** G5. **Note:** This footage CANNOT be recreated after the prompt is patched.

### Day 4 — Phoenix MCP load-bearing
- [ ] **T4.1** Insert Phoenix MCP query into pre-draft step (FR5); structured failure-summary augments the prompt. **DoD:** Trace shows MCP query + summary + prompt augmentation. **Trace:** FR5.
- [ ] **T4.2** Add `PHOENIX_MCP_ENABLED=false` flag (counterfactual harness). **DoD:** Toggle works; difference recorded. **Trace:** PRD §16.
- [ ] **T4.3** Enforce 9-field trace metadata on every span. **DoD:** Phoenix UI shows all fields populated. **Trace:** NFR4.
- [ ] **T4.4** Scaffold 2 playbooks (Cigna-medical-necessity, Aetna-prior-auth) as versioned JSON. **DoD:** `playbook_loader` retrieves them. **Trace:** FR4.

### Day 5 — Judges + **A1 eval-signal gate**
- [ ] **T5.1** Layer-1 deterministic checks: PHI regex, disclaimer string match, length, JSON validity. **DoD:** 4/4 pass; fail-injected outputs rejected. **Trace:** NFR2, FR7.
- [ ] **T5.2** Implement J1–J5 LLM judges as Phoenix Evals (cross-model: Claude 4 or GPT-5). **DoD:** Eval call returns rubric-shaped JSON; run visible in Phoenix Evals UI. **Trace:** FR7.
- [ ] **T5.3** Calibration: hand-score 2 cases; Cohen's κ; reject judges with κ < 0.6. **DoD:** `eval/calibration_log.md` has κ per judge. **Trace:** rubric §calibration.
- [ ] **T5.4** **A1 GATE:** v1 vs v2 on 2 held-out cases — lift ≥ +15%? judge std-dev ≤ ±0.08? **DoD:** PASS/FAIL recorded; PM escalation if FAIL. **Trace:** A1, SC1.
- [ ] **T5.5** **Demo capture: v1 vs v2 eval comparison.** Open Heuristics app (left) + Phoenix Experiments (right). Show score delta between v1 and v2. Show v2 appeal citing plan language. Show simulator outcome improvement. **DoD:** `docs/demo/raw/day5-v1-vs-v2-eval.mp4` saved. **Trace:** G5.

### Day 6 — Frontend workbench + last 2 judges
- [ ] **T6.1** Implement J6 + J7 judges. **DoD:** All 7 judges run end-to-end in <90s. **Trace:** rubric.
- [ ] **T6.2** Next.js workbench: case selector, v1/v3 toggle, side-by-side appeal, eval panel, simulator, Phoenix link-outs. **DoD:** Local demo on hero case shows all 5 UI regions. **Trace:** FR10, G8.
- [ ] **T6.3** Tone + accessibility pass per design-brief §4 + §8. **DoD:** Lighthouse a11y ≥ 90; copy review PASS. **Trace:** NFR7, G8.
- [ ] **T6.4** Wire deterministic gates to short-circuit before LLM judges. **DoD:** Cost log shows hard-gate FAIL skips weighted judges. **Trace:** rubric §cost.

### Day 7 — 🎯 Milestone 1 (MVP shippable)
- [ ] **T7.1** `agents-cli deploy` backend to Cloud Run (resolves **Open-Q J2**). **DoD:** Cloud Run URL reachable; end-to-end Next.js→backend→Phoenix completes. **Trace:** Open Q J2, G1.
- [ ] **T7.2** Deploy Next.js as second Cloud Run service; CORS + env vars. **DoD:** Hosted URL serves hero case <60s. **Trace:** G1, NFR6.
- [ ] **T7.3** Manual learning loop `backend/learn.py`: pull failed traces, propose patch, Phoenix Experiment on held-out 6, human approval in UI, version bump. **DoD:** v1→v2→v3 cycle logged. **Trace:** FR9.
- [ ] **T7.4** MVP eval run: full 4-case benchmark, v1 vs v3, record `weighted_quality`, hard-gate PASS rates, p95, Phoenix URL. **DoD:** SC1/SC2/SC3/SC5 logged. **Trace:** SC1–SC5.
- [ ] **T7.5** Draft MVP Devpost text + 3-min demo script per PRD §9. **DoD:** `docs/demo/mvp-script.md` reviewed by PM. **Trace:** G5, G7.
- [ ] **🔴 T7.6** **Demo capture: MVP full walkthrough (SAFETY-NET DEMO).** Record a full v1→v3 walkthrough on the hero case. Open Heuristics app (left) + Phoenix (right). Walk through: v1 weak appeal → Phoenix MCP failure summary → approved patch → v3 strong appeal → score jump → simulator flip from DENY to APPROVE → benchmark chart. **DoD:** `docs/demo/raw/day7-mvp-full-walkthrough.mp4` saved. This footage can be edited into a complete 3-minute MVP demo if Days 8+ fail. **Trace:** G5.

---

## Phase 2 — Swarm (Days 8–14)

### Day 8 — Decompose into Triage + Strategist + Drafter
- [ ] **T8.1** Split `aegis_v1` into ADK Coordinator + 3 sub-agents (Triage, Strategist, Drafter). **DoD:** Routing visible; 3 distinct agent spans in trace. **Trace:** PRD §12.1.
- [ ] **T8.2** Register the 3 prompts as Phoenix Prompts (versioned). **DoD:** Phoenix Prompts UI shows 3 versions. **Trace:** PRD §12.2.
- [ ] **T8.3** Re-run 12-case benchmark; record regression vs MVP. **DoD:** Composite within ±5% of Day 7 baseline. **Trace:** SC1.

### Day 9 — Insurer Intelligence (Phoenix MCP heavy user)
- [ ] **T9.1** Add Insurer Intelligence Agent per `insurer_intelligence_v1.md`. **DoD:** `InsurerBrief` JSON returned; MCP call traced. **Trace:** PRD §12.2 #3, FR5.
- [ ] **T9.2** Add 5th playbook (UHC mental-health-parity). **DoD:** Retrieved by playbook_loader. **Trace:** FR4.

### Day 10 — Specialist researchers + **GATE**
- [ ] **T10.1** Add Policy Detective + Medical Necessity + Legal Researcher (ParallelAgent fan-out). **DoD:** End-to-end with 5 specialists in parallel; p95 < 90s. **Trace:** PRD §12.2 #4–6, NFR6.
- [ ] **T10.2** Expand benchmark to 40 cases. **DoD:** 40 case files; dataset_card updated. **Trace:** PRD §13.5.
- [ ] **T10.3** **Day 10 PROGRESS GATE (ADR-004):** ≥5 of 9 specialist agents credible? **DoD:** PASS/FAIL in decision-log with evidence. **Trace:** ADR-004.
- [ ] **T10.4** **A5 GATE:** stub Learning Coordinator on 3 failed traces; ≥1-in-5 credible-patch rate? **DoD:** PASS/FAIL recorded; PM call if FAIL. **Trace:** A5.
- [ ] **T10.5** **Demo capture: swarm first run.** Open Heuristics app (left) + Phoenix Traces (right). Show 9-agent fan-out, parallel researcher briefs, trace waterfall. If Learning Coordinator has proposed first patch, capture in Phoenix. **DoD:** `docs/demo/raw/day10-swarm-first-run.mp4` saved. **Trace:** G5.

### Day 11 — Precedent Miner + benchmark to 60
- [ ] **T11.1** Add Precedent Miner agent. **DoD:** Each brief includes ≥1 traceable precedent. **Trace:** PRD §12.2 #7.
- [ ] **T11.2** Expand benchmark to 60 cases. **DoD:** 60 cases + provenance. **Trace:** PRD §13.5.
- [ ] **T11.3** Mid-Part-B regression on 40 held-out. **DoD:** `weighted_quality` ≥ Day 7 MVP baseline; no hard-gate FAIL spike. **Trace:** SC1.

### Day 12 — Adversarial Reviewer + iteration loop
- [ ] **T12.1** Add Adversarial Reviewer per `adversarial_reviewer_v1.md`; loop back to Drafter when `severity > 0.6` (max 1). **DoD:** Iteration visible in traces; severity recorded. **Trace:** PRD §12.2 #10.
- [ ] **T12.2** Add adversarial severity as a tracked dimension. **DoD:** Severity time-series in Phoenix UI. **Trace:** rubric.

### Day 13 — Quality Judge Panel (full 7)
- [ ] **T13.1** Full 7-judge Phoenix Eval suite; hard gates short-circuit first. **DoD:** Cost ≈ $0.10/letter; Evals UI shows panel. **Trace:** rubric §cost, FR7.
- [ ] **T13.2** Outcome Simulator Part B variant (per-insurer rules). **DoD:** APPROVE/DENY traceable to `simulator_rules.json`. **Trace:** FR8.

### Day 14 — 🎯 Milestone 2 + pre-check
- [ ] **T14.1** Full 60-case benchmark. **DoD:** Metrics dumped to `eval/benchmark-runs/day14.json`. **Trace:** SC1.
- [ ] **T14.2** **Demo-coherence pre-check (ADR-004):** can current build sustain a 3-min story? **DoD:** PM reviews script draft. **Trace:** ADR-004.
- [ ] **T14.3** Frontend polish #1: animated arch diagram, agent-status streaming, Phoenix link-outs per agent. **DoD:** Hero case shows live 9-agent activity. **Trace:** G8.
- [ ] **T14.4** **Demo capture: benchmark improvement arc.** Open Heuristics app (left) + Phoenix Experiments + Prompts (right). Show prompt version timeline, click a diff, show experiment score climbing, show benchmark chart, show safety stable. **DoD:** `docs/demo/raw/day14-benchmark-arc.mp4` saved. **Trace:** G5.

---

## Phase 3 — Learning + Polish (Days 15–20)

### Day 15 — Learning Coordinator + demo-coherence formal
- [ ] **T15.1** Learning Coordinator meta-agent (hourly; queries Phoenix MCP; 1–3 patches/slice; each → Phoenix Experiment). **DoD:** First autonomous experiment ran; patches archived with reason. **Trace:** PRD §15.1.
- [ ] **T15.2** Implement 6 safety gates per PRD §15.2 (rubric v2): J1/J2 PASS, no composite regression, no per-dim drop >10%, severity stable, diff ≤200 tokens, ≤5 promo/24h. **DoD:** Failing patch rejected; passing patch auto-promotes; audit complete. **Trace:** PRD §15.2.
- [ ] **T15.3** **Demo-coherence formal (ADR-004):** 3-min rehearsal video. **DoD:** PM signs off. **Trace:** ADR-004.

### Day 16 — Learning iterations 1–4
- [ ] **T16.1** 4 iterations (Cigna med-necessity, UHC prior-auth, Aetna MH parity, Anthem step-therapy). **DoD:** Each logged in Phoenix Experiments; promotions/archives visible. **Trace:** PRD §14 Day 16.
- [ ] **T16.2** Auto-rollback dry-run: push a regressing patch; confirm rollback triggers per §15.3. **DoD:** Rollback log entry; previous version restored. **Trace:** PRD §15.3.

### Day 17 — Pattern Synthesizer + 100 cases
- [ ] **T17.1** Pattern Synthesizer post-run agent. **DoD:** Meta-playbook updates across slices; synthesis step traced. **Trace:** PRD §12.2 +Pattern.
- [ ] **T17.2** Expand benchmark to 100 cases (60 train + 40 held-out). **DoD:** All 100 + provenance. **Trace:** PRD §13.5.
- [ ] **T17.3** Learning iterations 5–8. **DoD:** 4 more promoted/archived. **Trace:** PRD §14 Day 17.
- [ ] **🔴 T17.4** **Demo capture: counterfactual (mic drop).** Run same hero case with `PHOENIX_MCP_ENABLED=false`. Show quality collapse: generic appeal + low score + simulator DENY. **DoD:** `docs/demo/raw/day17-counterfactual.mp4` saved. **Trace:** G5, PRD §16.

### Day 18 — Polish + v1→v8 chart
- [ ] **T18.1** Frontend polish #2: full design-brief compliance, motion pass, AAA where possible. **DoD:** Lighthouse perf ≥90, a11y ≥95, best-practices ≥95. **Trace:** NFR7, G8.
- [ ] **T18.2** v1→v8 comparison chart in UI (composite over time, per-insurer breakdown, prompt-diff viewer). **DoD:** Chart reads from Phoenix Prompts versions. **Trace:** PRD §15.4.
- [ ] **T18.3** Cloud Run min-instance=1 for demo window; cost reverify. **DoD:** `gcloud run describe` shows min=1; spend dashboard <$50. **Trace:** NFR5.

### Day 19 — Demo recording
- [ ] **T19.1** Record 3-min demo per PRD §16: hook → swarm → hero case → learning loop → benchmark → counterfactual → close. **DoD:** Raw recording stored; Phoenix on screen ≥60s. **Trace:** G5, A2.
- [ ] **T19.2** Edit + caption + 1080p export; tone-guardrail review (no "wins 78%" without "simulated on synthetic benchmark"). **DoD:** Final MP4 in `docs/demo/aegis-final.mp4`. **Trace:** NFR2.

### Day 20 — 🎯 Milestone 3 (final benchmark + submission)
- [ ] **T20.1** Final 100-case benchmark; freeze metrics. **DoD:** Numbers in `eval/benchmark-runs/final.json` and pinned in README. **Trace:** SC1–SC5.
- [ ] **T20.2** README + Devpost: hosted URL, GitHub URL, video URL, track=Arize. **DoD:** Devpost form submitted; confirmation email. **Trace:** G6, G7.
- [ ] **T20.3** Tag `v1.0-aegis-final`; final commit; final memory-handoff. **DoD:** Tag on `origin/main`; handoff entry closes the session. **Trace:** (housekeeping).

---

## Gate Index (where to escalate)

| Gate | Day | Owner | Escalation if FAIL |
|---|---|---|---|
| **A4** MCP+ADK integration | 2 EOD | PM | Fallback to Phoenix SDK direct; soften MCP-load-bearing pitch |
| **A2** Phoenix UI demo-viable | 2 EOD | PM | Re-storyboard; consider extra UI overlays |
| **A3** Case credibility | 3 EOD | PM | Re-source from real public anonymised letters |
| **A1** Eval signal | 5 EOD | PM | Recalibrate rubric; kill learning-loop pitch |
| **Day 10 progress** | 10 EOD | PM | Lean-topology fallback (5-agent) per ADR-004 |
| **A5** Coordinator autonomy | 10 EOD | PM | Keep loop human-approved (MVP-style) |
| **Demo coherence pre-check** | 14 EOD | PM | Drop to MVP-style demo with what works |
| **Demo coherence formal** | 15 EOD | PM | Reduce demo scope or re-record from Day 19 cushion |
