# Assumption Map — Aegis PRD + Plan

**Compiled:** 2026-05-25 (Session 2)
**Source plan:** [docs/prd/PRD.md](../prd/PRD.md) + Session 1 architecture + Session 2 decisions
**Method:** `assumption-mapping` skill applied to PRD §1–§25 and pre-mortem causes A, K, D, M from same session

**Hard rules applied:** every assumption stated as a falsifiable claim; assumptions ≠ risks; most-confident beliefs prioritized; max 15 mapped total; 5 critical ones get minimum tests.

---

## The Grid (visual reference)

```
                LOW EVIDENCE         HIGH EVIDENCE
HIGH IMPORTANCE   [CRITICAL]            [VALIDATED]
LOW IMPORTANCE    [MONITOR]             [DEPRIORITISE]
```

---

## CRITICAL — test these first (1–5)

### A1. Demonstrable improvement at the magnitudes the PRD promises

**Claim (falsifiable):**
> The Aegis learning loop will produce (a) v1 → v3 composite eval score improvement ≥ +20% on a 6-case held-out set by Day 7 (PRD SC1), AND (b) v1 → v8 composite lift from ~0.30 to ~0.75+ on a 40-case held-out set by Day 20 (PRD §16 demo claim), AND (c) the lift is statistically distinguishable from rubric/judge noise.

**Evidence we have:** None. No agent built, no eval rubric finalized (still using a violates-AlphaEval design), no cases written, no judge calibration done. PRD lift numbers (0.31 → 0.78) are aspirational placeholders.

**Importance:** CRITICAL. This is the entire submission thesis. If lift is small or visually noisy, Cause K fires (improvement is real but not demonstrable) and Cause L fires (bonus claim looks unearned).

**Minimum test (Day 3–5):**
1. Hand-author 3 calibration cases + 3 held-out cases per a stub of the new eval rubric.
2. Write v1 agent (deliberately weak prompt — no insurer specifics, no playbook).
3. Score v1 on held-out 3 cases. Hand-author v2 with insurer-specific playbook for one denial-type.
4. Score v2. **If v1 → v2 manual lift on 3 cases is < +15%, the eval signal is too noisy or v1 is too strong — kill the learning-loop pitch before Day 7 and recalibrate.**

**False condition:** v1 → v2 lift on a fully-controlled hand-tuned case < +15% composite, OR three different judge re-runs of the same v2 give scores that vary by > ±0.08 (judge noise floor exceeds the lift we need).

**True condition:** v1 → v2 lift ≥ +20% on 3 cases AND judge stability ≤ ±0.04 across re-runs.

**Owner:** PM. **By:** Day 5.

---

### A2. Phoenix Cloud UI can be visibly demo-load-bearing for ≥60s of the 3-min video

**Claim (falsifiable):**
> Phoenix Cloud's UI (datasets, experiments, traces, evals views) can hold attention for ≥60 of 180 seconds of demo video while telling a clear, judge-followable story of *learning happening*, without requiring extensive screen narration that would crowd out the rest of the pitch.

**Evidence we have:** Low. Arize's hackathon brief calls out tracing + MCP as a co-equal Arize judging criterion, and the [Arize-ai/gemini-hackathon quickstart](https://github.com/Arize-ai/gemini-hackathon) confirms Phoenix Cloud exists and supports the workflows. But we have not watched a Phoenix product demo, not used the Experiments UI, not seen what the eval-clustering view actually looks like with 200 traces, and not storyboarded which Phoenix screens are in our demo video.

**Importance:** CRITICAL. The Arize sub-criterion *"Meaningful use of tracing and MCP"* is one of two co-equal pillars. Under-demonstrating this leaves judging points on the table (Cause A). It's also a credibility floor — if Phoenix isn't visibly on screen, the "Phoenix is the swarm's nervous system" line is hollow.

**Minimum test (Day 1–2):**
1. Watch official Phoenix Cloud demo videos + scroll the docs gallery (1 hour).
2. Sign up for Phoenix Cloud free tier; manually instrument a toy ADK agent; produce 20 traces.
3. Walk through every major Phoenix UI surface (traces, datasets, experiments, evals, prompts) and answer: *which 3 of these can I show on screen for 20+ seconds each in a way that visually shows learning?*
4. Draft a Phoenix-UI shotlist for the demo before any agent code is written.

**False condition:** None of Phoenix Cloud's main UI surfaces can credibly support a 60s on-screen story without zoom-and-narrate-everything tactics; OR Phoenix Experiments UI is not usable for the v1-vs-v8 comparison story.

**True condition:** Three Phoenix UI surfaces identified that each support a 20s+ on-screen beat (e.g., Experiments comparison for v1-vs-v8, Eval clustering for failure patterns, Traces explorer for the hero case introspection moment).

**Owner:** PM. **By:** Day 2.

---

### A3. Real-anchored synthetic cases will look credible to judges

**Claim (falsifiable):**
> Synthetic composite cases — each one stitched from public real denial-letter language (insurer sample letters, ProPublica investigations, KFF Patient Voices, court filings) — will be perceived by judges as credible representations of real denial complexity, AND a non-domain-expert judge will trust that improvement on these cases reflects real learning (not rigged scenarios).

**Evidence we have:** Low. We have a list of source types in [impact-stats.md §6](impact-stats.md). We have not actually pulled denial language, not composited a case, not gotten an outside reader's reaction. Session 1's PRD §22 lists sources but no provenance discipline is implemented.

**Importance:** CRITICAL. If synthetic cases look toy, Cause D fires AND it makes K, L, and the bonus claim worse. Judges will discount the lift if the benchmark looks rigged.

**Minimum test (Day 2–3):**
1. Source one real denial letter from public material per insurer (Cigna, Aetna, UnitedHealthcare) — composite or anonymized.
2. Composite 3 synthetic cases (one per insurer, medical-necessity denial type) following a documented provenance template: every paragraph traced to a public source.
3. Show the 3 cases to 2 outside readers (e.g., a friend who's a healthcare worker, a friend who's a writer) and ask *"does this read like a real insurance denial scenario?"*
4. If both readers flag it as toy or AI-generated, abandon synthetic-only and re-source.

**False condition:** Either outside reader describes the cases as "feels fake", "too clean", "doesn't sound like real insurance".

**True condition:** Both outside readers describe the cases as plausible / "scary how realistic that is" / "I've seen this kind of letter".

**Owner:** PM. **By:** Day 3.

---

### A4. Phoenix MCP + Google ADK integration is mature enough for load-bearing use

**Claim (falsifiable):**
> The `@arizeai/phoenix-mcp` server, combined with `openinference-instrumentation-google-adk` and current Google ADK, supports the agent calling Phoenix MCP at runtime to query its own past traces, receiving structured summaries useful for in-context reasoning, with end-to-end latency < 5s per query and reliable formatting — well enough that the agent's quality genuinely degrades if Phoenix MCP is removed (PRD FR5 explicit requirement, §16 counterfactual demo beat).

**Evidence we have:** Low. Brief lists the components; quickstart repo exists; no one on this team has wired them together. The "removing this must degrade quality" requirement and the "disable Phoenix → composite collapses to 0.42" demo beat are designed assumptions, not tested behaviors.

**Importance:** CRITICAL. If the integration is immature or flaky, (a) build week is eaten debugging (Cause C), (b) the load-bearing claim is hollow, (c) the demo counterfactual fails on stage.

**Minimum test (Day 1–2 dedicated spike):**
1. Stand up Phoenix Cloud account; configure `openinference-instrumentation-google-adk` on a toy "echo" agent; confirm traces appear.
2. Configure `@arizeai/phoenix-mcp` as a tool on the agent. Get one query in, one structured summary out, with the result visible in the agent's reasoning trace.
3. Measure latency and structured-output reliability over 20 toy queries.
4. **Go/no-go decision EOD Day 2** — if integration fails or is too flaky, raise to PM and re-decide MCP-as-load-bearing thesis (fallback: use Phoenix SDK directly; lose some pitch shine but preserve the loop).

**False condition:** Latency consistently > 10s, OR MCP responses unstructured/unreliable for in-context use, OR breakage requires forking instrumentor or filing upstream issues.

**True condition:** Toy agent successfully queries its own traces in < 5s with structured, usable output, on first or second day of work.

**Owner:** PM. **By:** Day 2 EOD.

---

### A5. Learning Coordinator can autonomously generate meaningful prompt/playbook patches

**Claim (falsifiable):**
> A meta-agent reading Phoenix traces (failures + successes), given the current prompts and playbooks, can autonomously generate candidate patches that (a) pass all 6 hard safety gates in PRD §15.2, (b) produce held-out composite-score lifts ≥ +3%, (c) at a hit rate ≥ 1-in-5 candidates, (d) without producing absurd or unsafe edits requiring human cleanup.

**Evidence we have:** None directly. There's research on LLM self-improvement via traces (broadly works in narrow domains) and Phoenix supports the experiment framework. But Learning Coordinator as specified — auto-promotion on safety-gate pass — is novel and untested for this stack.

**Importance:** CRITICAL. If false, the autonomous-loop pitch collapses; the Full Plan demo falls back to "manual learning with human approval" (which is just MVP-style + repeated). The PRD's "Phoenix is the swarm's nervous system" framing depends on this.

**Minimum test (Day 8–10):**
1. Build Learning Coordinator early (PRD R2 already says "run learning loop EARLY (day 8, not day 16)").
2. Run 5 iterations on a single (insurer, denial_type) slice — Cigna medical necessity.
3. Track: candidate count, hit rate (≥ +3% lift on subsample), safety-gate pass rate, absurd-edit rate (counted manually).
4. **Go/no-go by Day 10** — if hit rate < 1-in-10 OR > 30% of candidates are absurd, demote autonomous-loop to manual-with-human-approval and update demo.

**False condition:** Hit rate < 1-in-10 candidates produces a passing patch with ≥+3% lift, OR human review needs to reject > 30% of "passing" patches as nonsensical.

**True condition:** Hit rate ≥ 1-in-5; safety gates pass on ≥ 50% of candidates; absurd-edit rate < 10%.

**Owner:** PM. **By:** Day 10.

---

## VALIDATED — solid foundations (or close to it)

- **V1. Arize judging rubric explicitly rewards self-improvement loops.** Confirmed by [challenge.md](../challenge.md): "Quality of the agent's self-improvement loop" is a co-equal sub-criterion AND there's an explicit bonus for "agents that use their own observability data to improve over time". This was previously a critical assumption; rubric re-read in Session 2 validates it.
- **V2. The problem is real and large.** Confirmed by [impact-stats.md](impact-stats.md): KFF, Commonwealth Fund, JAMA, Senate report all corroborate denial rates, appeal-rate gap, and asymmetry. Potential Impact criterion can be defended with primary sources.
- **V3. Google ADK is on the Arize-approved code-owned runtime list.** Confirmed by challenge.md — we are NOT at risk of disqualification (unlike submissions using Visual Agent Builder alone).
- **V4. Apache 2.0 license requirement is met.** Already in repo.
- **V5. The non-technical PM can use Amp effectively as a builder.** Confirmed by Session 1 & 2 outputs (PRD, design brief, research, decision logs all produced this way).

---

## MONITOR — watch but don't test yet

- **M1. PM can sustain 160 hours of focused build over 20 days alongside day job without burnout collapse.** Plausible-but-fragile; Session 1's skills-skipping pattern hints at risk. Mitigation: weekly retro on Day 7, 14; if energy < 50%, escalate to PM (per Code-Wall Escalation Protocol). Do not test in advance — just monitor.
- **M2. Phoenix Cloud free tier covers ~200 runs × 12 agents × 100 cases × 8 versions of trace volume.** Estimate trace count by end of Week 1; if projection > 80% of free quota, upgrade ($50 ceiling).
- **M3. Gemini 3 ships in build window.** Open question; fallback path (Gemini 2.5) already exists in code. Watch news + Google Cloud release notes.
- **M4. Aegis differentiation from Counterforce Health / Sheer Health / Cofactor.** Newly surfaced from impact-stats research. The 4-point differentiation thesis (self-improvement loop + UX quality + transparent autonomy ladder + open source Apache 2.0) is reasonable but untested. Add competitive section to PRD; watch Devpost for similar Arize-track submissions Day 14.
- **M5. Cloud Run cold start is acceptable for demo.** Mitigation already in PRD R9 (min-instance=1 during demo). Low risk.
- **M6. PRD's "12-agent swarm coordination buildable Days 8–14" schedule is realistic.** Aggressive but defensible; ADK sub-agent patterns documented. Real test happens at Day 8. If Day 14 milestone slips, escalate to PM.
- **M7. Consumer-grade Next.js UX shippable in 20 days by non-technical PM + Amp.** Newly inverted decision. Mitigation: start frontend Day 1 in parallel with agent spike; treat as a co-equal pillar in scheduling. Watch for the first "this looks vibecoded" tell and run [`design-review`](../../.agents/skills/design-review/SKILL.md).
- **M8. The "disable Phoenix MCP → composite collapses to 0.42" demo beat is achievable.** Currently aspirational. Mitigation: instrument the counterfactual case explicitly as a build deliverable Day 17; if collapse isn't dramatic enough, soften the demo claim. Don't test before the loop exists.

---

## DEPRIORITISE — don't spend energy here

- **D1. The hackathon submission portal will accept our submission format.** Standard Devpost; vetted. No test needed.
- **D2. ERISA/ACA legal language we cite is accurate.** As long as we cite from controlled local corpus and don't invent, this is structurally safe.
- **D3. Cloud Run hosting works.** Mature; well-documented. No test.

---

## Top 3 things this map changes about the plan

1. **The Day 1–2 plan now includes a dedicated Phoenix MCP+ADK spike (A4) and a Phoenix UI study (A2)** before any agent code is written. These are the load-bearing infra/UX assumptions. If they fail at Day 2, we save 18 days of building on a broken foundation.

2. **A4-day eval-signal test (A1) happens by Day 5** with hand-authored cases, BEFORE the MVP claims its v1→v3 lift on Day 7. This catches "the eval rubric is too noisy" early, when we can still rebuild the rubric.

3. **Learning Coordinator runs starting Day 8 (PRD R2 already), but now with an explicit Day 10 go/no-go** for autonomous-loop viability. If autonomy doesn't work, demote to manual-with-human-approval and update the demo. Don't drag a non-working autonomous claim to Day 20.

---

## Synthesis: what this assumption map says about Aegis's readiness

**Aegis is more credibly positioned than Session 1 suggested.** Rubric validation (V1) confirms self-improvement is rewarded; problem-scale (V2) is well-evidenced; runtime stack (V3) is on the safe list. The strategic frame is sound.

**But the pitch claims out-pace the evidence by a wide margin.** The PRD already promises specific numbers (v1=0.31, v8=0.78, +151%, "disable Phoenix → 0.42"). These are *designed-in pitch beats with no engineering backing*. Five of the most important PRD claims are essentially untested assumptions — and three of them (A1, A4, A5) are testable in the first 10 days. We should test them, in that order, and let the test results discipline the pitch.

**The most expensive failure mode would be** building all 12 agents and all 200 iterations and only discovering on Day 18 that the eval signal is too noisy / the cases look toy / the autonomous loop doesn't produce real lifts. The discipline of running these five tests early — and being willing to *update the pitch downward* if any of them fail — is the difference between a credible Day 20 submission and an embarrassing one.

---

## Counts

- Total assumptions surfaced: **20**
- Critical (high importance × low evidence): **5**
- Validated: **5**
- Monitor: **8**
- Deprioritised: **3** (cut from active map)
- Minimum experiments defined: **5**
