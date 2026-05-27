# Phoenix UI Demo Shotlists (A2)

Per the PRD, the Phoenix Cloud UI must be visibly on screen for ≥60 seconds of the 180-second demo in both the MVP (Part A) and Full Plan (Part B) scenarios.

---

## PART B: Full-Plan Demo Shotlist (The 12-Agent Swarm)
*Reference: PRD §16 Full-Plan Demo Strategy*

## 1. Traces & Spans (The "Swarm's Brain")
**Duration:** ~25 seconds (Demo arc: 0:40–1:10 "Hero Case Live")

**What to show:**
- The Phoenix `Traces` view filtered to `project: aegis-hackathon`.
- Click into the hero case's trace to expand the waterfall view.

**Visual anchors to highlight:** 
- The parallel fan-out of the 4 Researcher agents (visually showing `ParallelAgent` execution).
- The `list-traces` tool call span (the agent actively querying Phoenix MCP to find past precedents).
- The LLM step showing the raw prompt injected with the trace summaries.

**Narrative:** *"Here you see the 12 agents working. But notice this span right here—this is the agent querying Phoenix via MCP to find past failed Cigna appeals to avoid making the same mistakes."*

---

## 2. Experiments & Prompts (The "Learning Loop")
**Duration:** ~25 seconds (Demo arc: 1:10–1:50 "Learning loop is protagonist")

**What to show:**
- The Phoenix `Experiments` or `Prompts` view.
- Show the timeline of the 8 prompt versions (v1 through v8).
- Open the prompt-diff viewer showing the change introduced by the Learning Coordinator.

**Visual anchors to highlight:**
- The diff adding: `If insurer == 'Cigna' and denial == 'Mental Health', cite MHPAEA parity.`
- The corresponding jump in the composite eval score for that version in the Experiments UI.

**Narrative:** *"This is the Learning Coordinator. On Day 12, it analyzed 3 failed Cigna appeals, realized it was missing the MHPAEA citation, drafted a patch, and auto-promoted it. You can see the exact diff here, and the resulting +14% score lift."*

---

## 3. Evals & Benchmarks (The "Lift")
**Duration:** ~20 seconds (Demo arc: 1:50–2:20 "The benchmark")

**What to show:**
- The Phoenix `Datasets` or `Evals` aggregate view.
- The 40-case held-out benchmark results over time.

**Visual anchors to highlight:**
- The bar chart or line graph showing `composite_score` climbing from ~0.40 to ~0.75.
- Filter down to the binary hard-gates (`hallucination = 0`, `safety = PASS`).

**Narrative:** *"Over 20 days and 200 iterations, the swarm climbed from a 40% pass rate to a 75% pass rate on our held-out test set, with zero hallucinations and perfect safety compliance."*

---
**Total guaranteed Phoenix screen time:** ~70 seconds. 

---

## PART A: MVP Demo Shotlist (Day 7 Backup)
*Reference: PRD §9 MVP Demo Script*

If we submit at the end of Week 1, the demo focuses on a single agent and human-approved learning loop.

### 1. Traces & MCP Summary (The "Protagonist")
**Duration:** ~40 seconds (Demo arc: 0:50–1:30 "Phoenix protagonist")

**What to show:**
- The Phoenix `Traces` view showing a v1 (failed) appeal trace.
- Expand the span showing the `list-traces` MCP call.
- **Visual anchors to highlight:** 
  - The structured failure summary generated from past traces (e.g., "Previous Cigna denials failed because they lacked MCG criteria references").
  - Switch to the Phoenix `Prompts` view to show the human-approved prompt/playbook patch for v3.

**Narrative:** *"This isn't just a monitoring dashboard. This is the agent's brain. It queried its own past failures via Phoenix MCP, deduced why it was failing, and proposed a patch that we approved."*

### 2. Held-Out Chart (The "MVP Lift")
**Duration:** ~30 seconds (Demo arc: 2:10–2:40 "Held-out chart")

**What to show:**
- The Phoenix `Datasets` or `Evals` aggregate view.
- Filter to a 6-case held-out benchmark showing the jump from v1 to v3.
- **Visual anchors to highlight:**
  - The `composite_score` lifting by ~24%.
  - Stable safety and hallucination scores.

**Narrative:** *"By reading its own traces, the single agent lifted its success rate by 24% across 6 held-out cases, without sacrificing safety or hallucinating."*

---
**Total guaranteed Phoenix screen time:** ~70 seconds. 
