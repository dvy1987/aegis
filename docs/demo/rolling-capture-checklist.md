# Rolling Demo Capture Checklist — Aegis

> **Why this exists:** The demo's entire story is "the agent got better over time." You cannot fake that at the end. You need to record the *weak* version while it still exists, because by Day 19 the prompt will have been patched 4-8 times and the weak output will be gone. This checklist tells you exactly when to hit record, what windows to open, and what to capture.

---

## How to Record (the basics)

**Tool:** Use Mac's built-in screen recorder (Command+Shift+5 → "Record Selected Portion") or install OBS/Loom.

**Two windows you'll always have open side-by-side:**
- **Left:** The Aegis app (your Next.js frontend — currently `http://localhost:3000`, later a Cloud Run URL)
- **Right:** Phoenix Cloud dashboard (`https://app.arize.com` — log in with your Arize account)

**What "record" means:** Start screen recording. Do the steps below. Stop recording. Save the file to `docs/demo/raw/` with the day number and a short description.

**File naming:** `day3-v1-first-run.mp4`, `day5-v1-vs-v2-eval.mp4`, etc.

---

## Capture Schedule

### Day 3 — First v1 Run (CRITICAL — cannot be recreated later)

**Why:** This is the only time the deliberately weak agent will exist. After Day 5, the prompt gets patched and v1 outputs are gone forever.

**Before you record, open these:**
1. Browser left tab: `http://localhost:3000` (Aegis app — the workbench page, once built)
2. Browser right tab: `https://app.arize.com` → log in → open Phoenix project **`default`** (v1 / Part A traces — not `aegis-hackathon`, which is swarm-only)

**What to record (2-3 minutes):**

| Step | Where | What you see | What to narrate/say |
|---|---|---|---|
| 1. Load a case | Aegis app (left) | Pick a Cigna medical-necessity case from the selector | "Loading a Cigna denial case" |
| 2. Hit "Draft Appeal" | Aegis app (left) | The agent processes the case | (wait for output) |
| 3. Show the v1 appeal | Aegis app (left) | A generic, weak appeal letter — no insurer-specific language, no plan citations | "This is v1. Generic. No Cigna-specific tactics." |
| 4. Show eval scores | Aegis app (left) | Low composite score (expected ~0.40-0.55) | "Composite score is low." |
| 5. Show simulator result | Aegis app (left) | Simulator says DENY | "The simulator says this would be denied." |
| 6. Switch to Phoenix | Phoenix (right) | Click "Traces" → find the trace for this run → expand it | "Here's the trace of what the agent did." |
| 7. Show the trace | Phoenix (right) | Scroll through the tool calls the agent made | "You can see every step it took." |

**Save as:** `docs/demo/raw/day3-v1-first-run.mp4`

---

### Day 5 — v1 vs v2 Eval Comparison

**Why:** This is the first proof that learning works. The eval score delta is the "does this actually improve?" evidence.

**Before you record, open these:**
1. Aegis app (left)
2. Phoenix Cloud (right) → click "Experiments"

**What to record (2 minutes):**

| Step | Where | What you see | What to say |
|---|---|---|---|
| 1. Open Experiments | Phoenix (right) | The v1 experiment run and the v2 experiment run side by side | "Two experiments — v1 was our weak agent, v2 is hand-tuned." |
| 2. Show score comparison | Phoenix (right) | v2 composite score is higher than v1 | "v2 scores measurably higher." |
| 3. Switch to Aegis | Aegis app (left) | Load same case, show v2 appeal output | "The v2 appeal cites plan language." |
| 4. Show simulator flip | Aegis app (left) | Simulator now says APPROVE (or closer to it) | "The simulator outcome improved." |

**Save as:** `docs/demo/raw/day5-v1-vs-v2-eval.mp4`

---

### Day 7 — MVP Full Walkthrough (SAFETY-NET DEMO)

**Why:** If everything after Day 7 fails, this footage can be edited into a complete 3-minute demo. This is your backup submission video.

**Before you record, open these:**
1. Aegis app (left)
2. Phoenix Cloud (right) → Experiments view

**What to record (3-4 minutes):**

| Step | Where | What you see | What to say |
|---|---|---|---|
| 1. v1 appeal | Aegis app (left) | Load hero case, show v1 weak appeal | "This is where we started." |
| 2. v1 scores + simulator | Aegis app (left) | Low composite, simulator DENY | "Weak score. Simulator denies." |
| 3. Phoenix traces | Phoenix (right) | Show the MCP query inside the trace — the agent asked Phoenix about past failures | "The agent looked up its own past failures." |
| 4. Approved patch | Aegis app (left) | Show the prompt/playbook change that was approved | "We approved this patch." |
| 5. v3 appeal | Aegis app (left) | Same case, now with strong appeal citing plan language | "After learning, the appeal is specific." |
| 6. v3 scores + simulator | Aegis app (left) | Higher composite (~0.75), simulator APPROVE | "Score jumped. Simulator approves." |
| 7. Benchmark chart | Aegis app (left) or Phoenix (right) | v1 vs v3 across all held-out cases | "Improvement is consistent." |

**Save as:** `docs/demo/raw/day7-mvp-full-walkthrough.mp4`

---

### Day 10 — Swarm First Run

**Why:** Shows the multi-agent decomposition working. The fan-out of researchers is visually compelling.

**Before you record, open these:**
1. Aegis app (left) — should now show agent status/progress
2. Phoenix Cloud (right) → Traces

**What to record (2 minutes):**

| Step | Where | What you see | What to say |
|---|---|---|---|
| 1. Load case | Aegis app (left) | Case goes into the swarm | "Now it's a team of agents." |
| 2. Show agent activity | Aegis app (left) | Multiple agents working in parallel (Triage, Researchers, Strategist, Drafter) | "9 agents working in parallel." |
| 3. Switch to Phoenix | Phoenix (right) | Open the trace — show the waterfall of multiple agent spans | "Each agent has its own trace span." |
| 4. Learning Coordinator | Phoenix (right) | If the Learning Coordinator has run, show its first patch proposal | "The Learning Coordinator proposed its first patch." |

**Save as:** `docs/demo/raw/day10-swarm-first-run.mp4`

---

### Day 14 — Benchmark Improvement Arc

**Why:** This is the "learning loop is the protagonist" beat. The chart showing composite score climbing across versions is the demo's emotional peak.

**Before you record, open these:**
1. Aegis app (left) — v1→v_current comparison chart
2. Phoenix Cloud (right) → Experiments + Prompts

**What to record (2 minutes):**

| Step | Where | What you see | What to say |
|---|---|---|---|
| 1. Version timeline | Phoenix (right) → Prompts | The list of prompt versions v1 through v_current | "8 versions of the prompt." |
| 2. Prompt diff | Phoenix (right) | Click v1 vs v8, show the diff | "Here's what changed — insurer-specific MHPAEA citations." |
| 3. Experiment scores | Phoenix (right) → Experiments | Composite score climbing version by version | "Each version gets better." |
| 4. Benchmark chart | Aegis app (left) | The full benchmark results chart | "Consistent improvement across all cases." |
| 5. Safety stable | Aegis app (left) or Phoenix (right) | Safety gate PASS across all versions | "And safety never regressed." |

**Save as:** `docs/demo/raw/day14-benchmark-arc.mp4`

---

### Day 17 — Counterfactual (MIC DROP)

**Why:** The "disable Phoenix MCP → quality collapses" beat. This proves Phoenix is load-bearing, not decorative.

**Before you record, open these:**
1. Aegis app (left)
2. Phoenix Cloud (right) — not needed for this beat, but keep open for visual continuity

**What to record (1-2 minutes):**

| Step | Where | What you see | What to say |
|---|---|---|---|
| 1. Run with Phoenix ON | Aegis app (left) | Normal run, good score, simulator APPROVE | "With Phoenix MCP enabled, the agent works well." |
| 2. Toggle Phoenix OFF | Aegis app (left) or backend env | Set `PHOENIX_MCP_ENABLED=false`, re-run same case | "Now I disable Phoenix." |
| 3. Show collapse | Aegis app (left) | Same case, but now generic appeal, low score, simulator DENY | "Without Phoenix, the agent forgets everything it learned." |

**Save as:** `docs/demo/raw/day17-counterfactual.mp4`

---

### Days 18-19 — Final Assembly (NOT first recording)

By this point, all raw footage exists. Days 18-19 are for editing and voiceover:

1. Write a 3-minute voiceover script using the captured footage as clips
2. Stitch clips together in iMovie, DaVinci Resolve, or similar
3. Record voiceover on top
4. Export at 1080p
5. Save as `docs/demo/aegis-final.mp4`

---

## Quick Reference: What the Aegis App Needs to Show

For the recordings to work, the Aegis frontend must have these surfaces built by the relevant day:

| Surface | Needed by | Shows |
|---|---|---|
| Case selector | Day 3 | Pick a denial case to process |
| Appeal output view | Day 3 | The drafted appeal letter text |
| Eval score panel | Day 5 | Composite score + per-dimension breakdown |
| Simulator outcome | Day 5 | APPROVE or DENY from the transparent simulator |
| v1/v3 toggle | Day 6 | Side-by-side comparison of two versions |
| Agent status/progress | Day 10 | Which agents are running (swarm mode) |
| v1→v_current chart | Day 14 | Improvement over time chart |
| Phoenix deep-links | Day 6+ | Click through to the Phoenix trace for any run |

## Quick Reference: Simulator Outcome in the UI

**Yes, the UX shows the simulator outcome.** Per PRD FR8 and FR10, the Aegis frontend must display the simulator's APPROVE or DENY verdict alongside the eval scores. This is a core demo element:

- v1 appeal → simulator says DENY
- v3 appeal → simulator says APPROVE

The simulator is a transparent two-step process (LLM feature extraction + deterministic scoring per `eval/simulator_rules.json`). The UI should show:
- The APPROVE/DENY verdict
- The feature extraction (10 features marked Y/N)
- A link to the published rules file for transparency

This flip from DENY to APPROVE is one of the most visually compelling moments in the demo.

---

## Raw Footage Folder

Create `docs/demo/raw/` and store all unedited captures there. Do not delete raw footage after editing — you may need to re-edit.
