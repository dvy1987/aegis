# Heuristics demo — how it actually works

## Two surfaces (your model)

| Page | Who it's for | What runs |
|------|----------------|-----------|
| **Draft an appeal** (`/appeal`) | The **customer** (you, live) | **Real** backend every time — real letter, real librarian |
| **How Heuristics learns** (`/showcase`) | **Judges** — behind the scenes | **Recorded** v1 vs v3 evidence from your eval runs |

You play the customer on `/appeal`. You switch to `/showcase` to show judges what happened under the hood.

## Recording the Devpost video

1. Start the backend (`./scripts/dev.sh` or Cloud Run).
2. Open **Settings** → confirm **Connected** → **Save**.
3. On **Draft an appeal**: paste or pick a sample case → submit → real draft.
4. Switch nav to **How Heuristics learns** → pick the same case → show v1/v3 lift.
5. Screen-record that flow.

No “practice mode” on the customer path — if the backend is down, you get an error (honest).

## Settings (only if needed)

- **Service address** — where the backend lives.
- **Trusted source lookup** — on by default when connected; thin library → up to 5 trusted fetches.

---

## Phoenix projects (don't mix these up)

| What you're demoing | Open this Phoenix project | Why |
|---------------------|---------------------------|-----|
| **v1** — `/appeal`, showcase quick/serious runs | **`default`** | All v1 traces and showcase learning land here |
| **swarm** — 12-agent Part B | **`aegis-swarm`** | Swarm-only traces |

There is **no** Phoenix project called `aegis-swarm`. v1 and swarm use **different recorder classes** (`OtelPhoenixRecorder` vs `OtelSwarmTraceRecorder`) — they are not shared. Full detail: [decision-log.md §2026-06-07](memory/decision-log.md).

---

## Cloud Run flags (PM cheat sheet)

These are set in `backend/deploy-v1.sh` for `aegis-v1-api`. Full rationale: [decision-log.md §2026-06-07](memory/decision-log.md).

| Flag | Value | Plain English |
|------|-------|---------------|
| `--no-cpu-throttling` | on | **Most important.** After you click Start, the server says "OK" and keeps working in the background. Without this, Cloud Run turns CPU down between requests and the run looks frozen. |
| `--max-instances` | `1` | Only one server machine. Session progress is stored in a file on that machine — multiple machines would break polling. |
| `--min-instances` | `1` | Always keep one machine warm (no cold-start wait at demo time). |
| `--concurrency` | `1` | One web request at a time per machine — predictable CPU for long Gemini chains. |
| `--timeout` | `300s` | Any **single** HTTP request dies after 5 minutes. The whole learning run is **not** one request — the UI polls every 10 seconds while work continues in the background. |

**How the UI learns a run finished:** the backend does **not** push to the browser. The frontend asks "status?" every 10 seconds until the status stops changing.

**Redeploy reminder:** these flags only help in production after `./backend/deploy-v1.sh` has been run since they were added.

---

## Showcase run statuses — what the UI shows (demo script)

Two labels appear on `/showcase` during a live run:

1. **Run status** (badge, e.g. `running`, `needs approval`) — overall state of the session.
2. **Current stage** (large heading) — what the backend is doing right now.

The three matrix columns fill as results arrive: **Pre-training** (held-out baseline) · **Training** (before/after on train cases) · **Post-training** (held-out after you approve).

### Happy path — quick check

| Order | Run status | Current stage (UI heading) | What you see / what to say |
|-------|------------|----------------------------|----------------------------|
| 1 | `queued` | `queued` | You clicked **Run quick check**. Session id appears. Work starts in the background. |
| 2 | `running` | `measure before` | Measuring held-out cases with the **current** prompt (no learning yet). **Pre-training** column fills. |
| 3 | `running` | `measure before` | Same stage name — now measuring **training** cases before learning. **Training** column "before" side fills. |
| 4 | `running` | `train gepa` | Drafting + judging training cases, building Phoenix signal, running the optimizer. Progress: "N of M cases complete". |
| 5 | `running` | `measure after` | Re-measuring training cases with the **candidate** prompt/playbook (not promoted yet). **Training** column "after" side fills. |
| 6 | **`needs approval`** | **`waiting for approval`** | Learning loop done. **Approve update** / **Reject update** buttons appear. Polling stops. *"The system proposed changes — I decide whether to ship them."* |
| 7 | `running` | `promote` → `measure after` | You clicked **Approve update**. Changes go live; held-out cases re-measured. **Post-training** column fills. |
| 8 | **`successful`** | `measure after` (usually) | Run complete. **Run serious pass** unlocks. Amber banner if regression detected on holdout. |

### Your decision at `needs approval`

| You click | Run status after | What happened |
|-----------|------------------|---------------|
| **Approve update** | → `running` → `successful` | Proposed prompt/playbook changes are **promoted** to production, then holdout re-measured. |
| **Reject update** | `rejected` | Proposal **discarded**. Nothing promoted. |

### When things go wrong

| Run status | Current stage | UI | What it means |
|------------|---------------|-----|---------------|
| `failed` | `failed` | Error message + error code | Run stopped. If retryable, an agent can call the resume endpoint; completed stages are not redone. |
| `cancelled` | `cancelled` | Cancel button gone | You clicked **Cancel run**. No promotion possible. |
| `rejected` | `waiting for approval` | Approve/Reject gone | You rejected the proposal. |

**Rollback** (separate button): **Roll back latest update** restores the previous promoted prompt/playbook. It does not rewind an in-flight session — use after a successful quick run if you want to undo a promotion.

### Serious pass gate

**Run serious pass** stays disabled until a **quick** run reaches **`successful`** (you approved and holdout measurement finished).

### Demo talking beat (30 seconds)

1. *"I start a quick learning check — the UI returns immediately; work continues on the server."*
2. *"Pre-training is the baseline on held-out cases. Training shows before and after on the train set. The optimizer read Phoenix traces and proposed a patch."*
3. *"It pauses at needs approval — human in the loop. I approve; post-training shows held-out results with the promoted prompt."*
4. *"Only after quick succeeds can I run the serious pass."*
