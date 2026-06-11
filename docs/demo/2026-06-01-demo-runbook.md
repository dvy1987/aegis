# Heuristics Demo Runbook

**Date:** 2026-06-01 · **Status:** working doc for the PM
**Purpose:** Step-by-step, from where we are now to a demo you can show live and record for submission.

This is the "run the demo from current reality" doc. It complements — does not replace:
- [`rolling-capture-checklist.md`](rolling-capture-checklist.md) — when to hit record during the build
- [`phoenix-shotlist.md`](phoenix-shotlist.md) — Phoenix UI shots
- PRD [§9 (MVP demo)](../prd/PRD.md) and [§16 (full-plan demo)](../prd/PRD.md) — the narrative beats

---

## 0. The one decision that shapes everything: demo-mode vs live

There are two ways to demo, and they need very different amounts of work.

| | **Track A — Demo mode** | **Track B — Live thesis** |
|---|---|---|
| **What runs** | The frontend alone, serving bundled real-case fixtures + the recorded efficacy run | Frontend + FastAPI backend calling Gemini/Vertex, Phoenix MCP reads |
| **Creds needed** | **None** | GCP ADC + `PHOENIX_API_KEY` (+ Phoenix MCP auth fix) |
| **Runs on this box today?** | **Yes** | No — no creds here |
| **Shows the consumer product** | ✅ fully | ✅ fully |
| **Shows v1→v3 improvement** | ✅ as recorded evidence (honestly labeled) | ✅ generated live |
| **Shows "Phoenix off → quality collapses" live** | ✅ as recorded numbers | ✅ live toggle |
| **Risk during a live demo** | Near zero (static, deterministic) | Cold starts, rate limits, latency, a bad draft |

**Recommendation:** record and present from **Track A (demo mode)**. It is honest (every number on `/showcase` is a real recorded efficacy result, and illustrative cases are labeled as such), it never fails live, and it shows the entire product. Use **Track B only if** you want the video to show a draft being generated in real time and a live Phoenix trace — and only once creds are on a box. The two are not mutually exclusive: you can record the consumer flow + showcase from Track A, and splice in one live-generation clip from Track B if/when creds land.

The rest of this doc is sequenced: **Part 1 gets you a clickable demo today (Track A). Parts 2–5 add the live thesis, the video, hosting, and submission.**

---

## Part 1 — Get a clickable demo running today (Track A, no creds)

- [ ] **1.1 Get the branch.** The frontend lives on `feat/frontend-two-surface` (not yet merged).
  ```bash
  cd /bv3/aimbot/divya/buildmind-misc/aegis
  git checkout feat/frontend-two-surface
  ```
- [ ] **1.2 Install + run.**
  ```bash
  cd frontend
  pnpm install
  pnpm dev          # serves http://localhost:3000 — demo mode is the default
  ```
- [ ] **1.3 Sanity check the three routes** in a browser:
  - `http://localhost:3000/` — landing
  - `http://localhost:3000/appeal` — the consumer flow
  - `http://localhost:3000/showcase` — "How Heuristics learns"
- [ ] **1.4 Pick your demo cases** (see Part 6 for selection guidance). All 10 test cases are selectable; cases `test_case_01..04` have **measured** v1/v3 numbers on `/showcase`.
- [ ] **1.5 Walk it once end-to-end** before recording (the scripts are in Parts 2–3).

That's the whole prerequisite for a demo. No backend, no creds, no deploy.

---

## Part 2 — The consumer-flow walkthrough (Surface A: `/appeal`)

The story here is a stressed person turning a denial into a draft. Keep narration calm and plain — the product never says "AI".

| Beat | Screen | What you do / show | Say (suggested) |
|---|---|---|---|
| 1. Land | `/` | The calm hero. One sentence, one CTA. | "A denial isn't a final answer. This helps you draft the appeal." |
| 2. Start | click **Start a draft** → `/appeal` | Intake screen. | "You paste the denial letter, or start from an example." |
| 3. Intake | `/appeal` | Click a sample case chip (e.g. your chosen case); the denial text fills in. Add a clinical note if you like. | "Here's a real-style denial." |
| 4. Working | — | Calm text-progress: "Reading your denial… → Drafting… → Almost done." | (let it breathe) |
| 5. Mirror | — | The plain-English "here's what we heard": who denied it, why, the deadline, the strongest angle. | "It reflects back what it heard, in plain English." |
| 6. Draft | — | The editable letter + the side rail: proxy verdict, what would make it stronger, evidence to gather, the safety disclaimer. | "A real, editable letter — and an honest, transparent proxy of how it might land. Never a promise." |
| 7. Decide | — | Copy / download. The "a person should read this before you file" line. | "You take it from here. It files nothing for you." |

**Tone guardrails while narrating:** no "AI/Phoenix/Gemini", no exclamation, don't promise a win.

---

## Part 3 — The self-improvement proof (Surface B: `/showcase`)

This is the Arize judging beat: the agent improves from its own observability.

| Beat | Screen | What you do / show | Say (suggested) |
|---|---|---|---|
| 1. Thesis | `/showcase` | The header line + the case picker. | "This is how the tool gets better — from its own evaluation history." |
| 2. Pick a case | case picker | Choose a **measured** case (01–04). | "Same denial, two versions of the system." |
| 3. Before/after | Versus panel | Two drafts, two composite scores, two simulator verdicts; the measured lift (+20.5% held-out). | "The earlier draft scored lower and was denied; the improved one cites the case and clears the bar." |
| 4. What changed | Diff card | The laundered "what changed and why" bullets. | "It learned the strongest angle for this kind of case." |
| 5. Mic drop | Counterfactual card | Memory-on vs memory-off scores. | "Switch off its memory and quality drops — the memory is load-bearing, not decoration." |

**Honesty note to keep you safe with judges:** on `/showcase`, cases 01–04 are real recorded results; 05–10 are clearly labeled illustrative, and the memory-off number is labeled a design target where not yet measured. Don't claim otherwise on camera.

---

## Part 4 — (Optional) the live thesis (Track B) — what unlocks it

Only needed if you want live generation / a live Phoenix trace in the video. Blocked until creds are on a box. In order:

- [ ] **4.1 Put creds on a box.** GCP ADC (`gcloud auth application-default login`) + `PHOENIX_API_KEY` (and the Phoenix env: `PHOENIX_HOST`, `PHOENIX_PROJECT`, `PHOENIX_CLIENT_HEADERS`). See `docs/memory/current-state.md` (Session 25) for the exact creds boundary and the Phoenix MCP-auth fix still owed (Tier 1 Task 0).
- [ ] **4.2 Run the backend.**
  ```bash
  cd backend
  uv run uvicorn app.main_v1:app --host 0.0.0.0 --port 8001
  # health: curl localhost:8001/health  → {"ok":true}
  ```
- [ ] **4.3 Point the frontend at it.**
  ```bash
  cd frontend
  NEXT_PUBLIC_AEGIS_MODE=live NEXT_PUBLIC_AEGIS_API=http://localhost:8001 pnpm dev
  ```
  Now `/appeal` calls `POST /v1/appeal` and drafts a real letter. (`/showcase` still reads recorded artifacts — the proof is always recorded evidence.)
- [ ] **4.4 Capture one live clip** following [`rolling-capture-checklist.md`](rolling-capture-checklist.md) + [`phoenix-shotlist.md`](phoenix-shotlist.md): a live draft + the Phoenix trace + the `PHOENIX_MCP_ENABLED=false` counterfactual.
- [ ] **4.5 Live-Mirror caveat:** the live API doesn't yet return `parsed_case`/`appeal_strategy`, so the Mirror step is lighter in live mode. If the Mirror is on camera, either demo that beat from Track A, or do the small backend follow-up to return those fields (noted in the frontend spec §6.1).

---

## Part 5 — Record the video + submit

- [ ] **5.1 Decide the spine** — recommended 3-minute arc (maps to PRD §9):
  1. 0:00–0:20 Hook + the problem (one stat, factual).
  2. 0:20–1:10 Consumer flow (Part 2) — land → draft → decide.
  3. 1:10–2:20 `/showcase` (Part 3) — before/after + what changed.
  4. 2:20–2:50 Counterfactual (memory off → collapse).
  5. 2:50–3:00 Close: "It improves from its own observability. Open source, Apache 2.0."
- [ ] **5.2 Record** with the consumer flow on the left; for Track B beats, Phoenix on the right (per the capture checklist). Save raw clips to `docs/demo/raw/`.
- [ ] **5.3 Edit** to ~3:00, add a calm voiceover, export 1080p → `docs/demo/aegis-final.mp4`.
- [ ] **5.4 Host the app** (so judges can click it):
  - Stack-locked target is **Cloud Run** (PRD §19). Demo mode needs no backend, so a single Next.js container serving demo mode is enough for a clickable URL. Build + deploy the `frontend/` container, or use your existing dev-launcher/Cloud Run setup.
  - Quick alternative for a click-through link: any Node host running `pnpm build && pnpm start` in demo mode. (Confirm with the stack lock before relying on a non-Cloud-Run host for the official submission.)
- [ ] **5.5 Submission deliverables** (PRD §20):
  - [ ] Hosted project URL
  - [ ] Public GitHub repo, **Apache 2.0** in the About section
  - [ ] ~3-min video
  - [ ] Devpost form, track = **Arize**
  - [ ] Disclaimers present in UI/repo/video (PRD §21) — the consumer Draft/Decide steps already carry the short disclaimer.

---

## Part 6 — Pre-demo checklist + case selection + fallbacks

**Case selection (the PM picks live):**
- For the **consumer flow**, pick a case that lands as APPROVE so the arc feels resolved — e.g. `test_case_01_uhc_mednec` or `test_case_02_aetna_priorauth` (both APPROVE in demo). Or deliberately show an honest harder one.
- For **`/showcase`**, pick a **measured** case with the strongest arc — `test_case_03_cigna_mednec` (Wegovy) goes v1 0.66 / DENY → v3 0.88 / APPROVE, the most compelling before/after, and it's the default.
- A clean pairing: consumer flow on case 01 (feels good), showcase on case 03 (strongest learning arc). Or keep one case across both for continuity.

**Pre-demo checklist (run 10 min before):**
- [ ] `pnpm dev` up; all three routes load.
- [ ] Your chosen cases selected and walked once.
- [ ] Browser zoom set, notifications off, window sized for recording.
- [ ] If Track B: backend `/health` returns ok; one warm-up draft done (avoid cold start on camera).

**Fallbacks:**
- Backend flaky / creds missing → demo entirely in Track A (this is the recommended default anyway).
- A live draft comes out weak on camera → cut to the recorded `/showcase` evidence; never argue with a bad live output.
- Hosting not ready → record the video from localhost; the hosted URL can follow.

---

## Open decisions for the PM

1. **Track A only, or splice in a Track B live clip?** (Recommend A-only unless creds + time are comfortable.)
2. **Which case(s)** for consumer flow vs showcase (Part 6 has a recommendation).
3. **Merge `feat/frontend-two-surface` to `main`?** It's verified (17 tests, build green) but unmerged and unpushed by design.
4. **Do the small backend follow-up** (return `parsed_case`/`appeal_strategy`) so the live Mirror matches the demo Mirror? Only matters if the Mirror is shown in Track B.
