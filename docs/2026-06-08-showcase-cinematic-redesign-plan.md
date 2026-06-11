# /showcase — Cinematic Redesign Plan

**Date:** 2026-06-08
**Owner:** Design (handoff doc — another agent will build on a separate machine)
**Scope:** Visual + motion layer of `/showcase` only. **Do NOT touch `/appeal`.**
**Status:** Plan only. No code in this session (parallel agent active — avoid conflicts).

---

## 0. Read this first — non-negotiable constraints

This is a **rebuild of the visual layer of `/showcase`**, not a rewrite of its logic.

### 0.1 Audience reframe (this changes the rules)

`/showcase` is **for hackathon judges and the demo recording** — *not* for patients. This is the opposite surface from `/appeal`:

| | `/appeal` (patient) | `/showcase` (judge / demo) |
|---|---|---|
| Audience | Stressed person who got a denial | Arize judges, Devpost viewers |
| Emotional target | Calm, dignified, low-friction | Delight, spectacle, "this is real and ambitious" |
| May name the tech? | **No** (no "AI", "Phoenix", "Gemini", "ADK") | **Yes** — judges *want* the machine shown |
| Palette | Warm light parchment | **Dark, dramatic, luminous** |
| Motion | Restrained, meditative | Cinematic, choreographed, theatrical at peaks |

So the consumer-voice rules in `docs/design-brief.md` §4 (no AI language, no exclamation marks, no jargon) **apply to `/appeal`, not here.** On `/showcase` we are allowed — encouraged — to say *Phoenix memory*, *judge panel*, *held-out benchmark*, *GEPA optimizer*, *human-in-the-loop*. Still dignified: no emoji spam, no "🚀", no hype-bro copy. Confident, precise, cinematic.

### 0.2 Preserve the data layer EXACTLY

The build agent must keep these untouched in behavior. Only their **presentation** changes. (Locations: `frontend/src/app/showcase/page.tsx`.)

- All four `useEffect` hooks: initial load (`listCases`/`getShowcaseManifest`/`getRollbackTarget`), case-selection fetch (`getShowcase(sel)`), the **10-second `runSession` polling loop** with its terminal-status guard, and the rollback-refresh effect.
- Handlers, unchanged signatures and call order: `startQuick` → `startQuickRun()`, `startSerious` → `startSeriousRun()`, `cancelCurrentRun` → `cancelRun()`, `approveCurrentRun` → `approveRun()`, `rejectCurrentRun` → `rejectRun()`, `rollbackLatestRun` → `rollbackRun()`.
- The `seriousUnlocked` gate logic (`runSession?.run_type === "quick" && status === "successful"`).
- All terminal-status handling (`successful | failed | cancelled | rejected | needs_approval | rolled_back`).

**Do not refactor data fetching, do not change the data-source seam, do not change polling cadence.** Wrap the existing state in new presentational components; do not move the state.

### 0.3 Remove the case pills

The pill row (`<CasePicker>` rendered at `page.tsx:156`, defined in `components/showcase/CasePicker.tsx`) is removed from this page. **But `sel` / `setSel` / `bundle` still drive the Versus / Diff / Counterfactual panels** — so we keep that state and replace the *picker UI* with a single cinematic "featured case" presentation plus a quiet, in-flow case cycler (see §6, Act IV). Do not delete the state; delete the pill component usage and give case-switching a new, non-pill home.

---

## 1. Creative direction

### 1.1 Three directions I evaluated (internal)

**A — "Obsidian Observatory" (living system).** Near-black control-room. Data rendered as *light*: a single luminous accent, telemetry in mono, editorial serif headlines. The learning loop is presented as an organism you watch breathe and then ignite. Memorable shot: a grid of red verdict cells flipping to green like a constellation coming online. Risk: needs disciplined restraint or it reads "gamer RGB."

**B — "Instrument / Blueprint."** Swiss, graph-paper grid, hairline schematics, monospace-forward, an architecture diagram that draws itself. Maximum engineering credibility. Risk: cold and *academic* — exactly the dryness the brief says to overcome.

**C — "Aurora / Editorial Film."** Big type, slow camera pans, soft volumetric glows over black, film grain, vast negative space. Beautiful on camera. Risk: drifts into the banned cliché-AI gradient look (purple/pink "leveraging AI" vibe) if not policed.

### 1.2 Chosen direction (2–3 sentences)

**I'm building "Obsidian Observatory" as the spine, with C's cinematic restraint for pacing and one B-style self-drawing schematic reserved for the architecture beat.** A dark, near-black instrument where the product's data *is* the light — one disciplined luminous accent (a cooled, electrified evolution of Heuristics' sage), telemetry mono, and serif display headlines — so the dry backend reads as a living system the judge watches breathe, ignite, and improve. This records beautifully because high-contrast dark + a single accent + light-as-data compresses cleanly on video, hides screen noise, and makes each "wow" moment (verdict cells flipping red→green, the memory-off dimming, the lift counter ticking) land without any post editing.

### 1.3 The one-sentence concept

> **"Watch a system teach itself."** The page is an observatory: you arrive on a quiet, breathing machine; you trigger a learning run; you watch evidence arrive as light; you make the call (approve / reject); and you see the same case become measurably better — then you cut the system's memory and watch quality fall, proving the memory was doing the work.

---

## 2. Design system (dark)

We **derive a dark theme from the existing oklch tokens** (`frontend/src/styles/tokens.css`) rather than inventing a parallel system. Add a `[data-theme="showcase-dark"]` (or a `.showcase` scope) token block; do not mutate the global/light tokens used by `/appeal`.

### 2.1 Surfaces (near-black, warm-cool neutral — not pure #000)

| Token | oklch | Use |
|---|---|---|
| `--sc-bg` | `oklch(16% 0.012 250)` | Page base — deep blue-graphite, never `#000` (banding on video) |
| `--sc-bg-raised` | `oklch(19% 0.013 250)` | Cards, the "instrument" panels |
| `--sc-bg-sunken` | `oklch(13% 0.010 250)` | Wells, the verdict-grid backdrop |
| `--sc-bg-overlay` | `oklch(20% 0.013 250 / 0.72)` | Glass overlays, sticky nav |
| `--sc-hairline` | `oklch(100% 0 0 / 0.08)` | Default 1px borders |
| `--sc-hairline-strong` | `oklch(100% 0 0 / 0.16)` | Emphasis borders, active states |

A faint **vertical gradient** on `--sc-bg` (top `18%` → bottom `14%` lightness) gives the room depth. Optional: a single, very soft radial "key light" behind the hero headline, accent-tinted at ~6% — this is the only glow on the page; keep it disciplined (the anti-reference is cliché AI gradients).

### 2.2 Text

| Token | oklch | Use |
|---|---|---|
| `--sc-text` | `oklch(96% 0.005 250)` | Primary — soft white, not pure white |
| `--sc-text-2` | `oklch(74% 0.008 250)` | Secondary / body |
| `--sc-text-3` | `oklch(58% 0.010 250)` | Captions, mono labels, telemetry |
| `--sc-text-on-accent` | `oklch(16% 0.012 250)` | Ink on the luminous accent |

### 2.3 Accent system (one luminous accent + two semantic signals)

The signature move: **one** accent, used as *light*. Push the existing sage toward a luminous, slightly cooled green so it glows on black.

| Token | oklch | Use |
|---|---|---|
| `--sc-accent` | `oklch(78% 0.16 165)` | The light. Active state, fills, the "improved" side, success |
| `--sc-accent-dim` | `oklch(62% 0.13 165)` | Resting accent, lines |
| `--sc-accent-glow` | `oklch(80% 0.17 165 / 0.45)` | Box-shadow / drop-shadow glow only |
| `--sc-warn` | `oklch(72% 0.15 55)` | Regression banner, "memory off" decay (warm amber) |
| `--sc-deny` | `oklch(64% 0.17 25)` | DENY verdict cells, failure (clay-red, from existing clay) |

**Contrast strategy:** the page is 90% low-chroma graphite + soft white. Chroma appears *only* where meaning lives — an accent fill, a DENY cell, a regression banner. Because color is rare, every colored pixel reads as signal. This is what makes the verdict grid flipping red→green feel like an event.

**Verdict semantics (carry over, recolor for dark):** APPROVE = `--sc-accent` (green light), DENY = `--sc-deny` (red). On dark these read like a live status board.

### 2.4 Typography

Reuse the repo's families (already self-hosted via `next/font`): **Source Serif 4** (display), **Inter** (body), **JetBrains Mono** (telemetry).

- **Display (Source Serif 4):** hero `clamp(3rem, 6vw, 5.5rem)`, weight 600, `letter-spacing: -0.02em`, `line-height: 1.05`. Editorial, confident. This is the cinematic voice.
- **Section headers (Source Serif 4):** `2rem–2.75rem`, weight 600.
- **Body (Inter):** 1.0625rem / `line-height: 1.6`, `--sc-text-2`. Tight, modern, never wordy.
- **Telemetry / labels (JetBrains Mono):** `0.8125rem`, `letter-spacing: 0.04em`, **uppercase** for labels, `--sc-text-3`. This is the "instrument" voice — session IDs, stage names, percentages, scores, deltas. Mono-on-dark is what sells "real system."

**Type pairing logic:** serif headline = the *story* ("Watch a system teach itself"), mono = the *machine* (`SESSION 0xA4F · STAGE measure_before · 14/20`). The contrast between the two voices is the whole personality. Inter is the connective tissue between them.

### 2.5 Spacing, grid, radius, depth

- **Spacing:** keep the repo's 4px log scale. Showcase runs *more generous* — section padding `py-28` to `py-40` on desktop. Negative space is part of the cinema.
- **Grid:** 12-col, `max-w-[1200px]` container, 24px gutters. **Use asymmetry deliberately** — hero text left-weighted with the living glyph offset right; the Versus panel is a true 50/50 split (the only symmetric moment, because the comparison *demands* symmetry).
- **Radius:** `--sc-r-card: 16px`, `--sc-r-chip: 999px`, `--sc-r-cell: 3px` (verdict cells stay crisp). Slightly larger radii than `/appeal` to feel premium on dark.
- **Borders:** hairlines do the structural work (`--sc-hairline`). On dark, a 1px hairline + a subtle inner highlight (`box-shadow: inset 0 1px 0 oklch(100% 0 0 / 0.04)`) gives panels a milled-metal edge.
- **Depth / shadow:** shadows are nearly invisible on dark; instead use **luminosity for elevation** — raised panels are lighter (`--sc-bg-raised`), active panels gain an accent glow ring. Reserve real drop-shadow for one element: the floating run-control dock.

### 2.6 Material language

The page should feel **"obsidian glass over a living circuit."**

- **Panels:** matte graphite glass — `backdrop-blur(20px)` over `--sc-bg-overlay`, 1px hairline, inner top highlight. Cool, premium, slightly translucent so the background key-light bleeds through faintly.
- **The accent:** *luminous* — wherever the accent appears it carries a soft `--sc-accent-glow` drop-shadow, like backlit signage. This is the only "glow" budget; spend it on meaning.
- **Verdict cells:** crisp, almost tactile tiles — flat fill, 1px darker border, micro inner shadow. They should feel like physical status lamps.
- **Text:** soft, never harsh white — luminous but calm.

Net feel: **matte + dark + sharp**, punctuated by **luminous + glassy** at the points of meaning. Restraint everywhere, radiance at the peaks.

---

## 3. Motion system

Three tiers. Most of the page is Tier 1. Tier 3 is rationed to ~4 moments.

### 3.1 Tier 1 — Subtle (ambient, always-on)

The resting state of the observatory. Continuous, low-amplitude, never demanding.
- The hero glyph **breathes** (slow scale/opacity, ~4s loop).
- Live telemetry text has a soft cursor blink; numbers ease, never snap.
- Hairlines have a barely-perceptible accent shimmer that travels once on section enter.
- **Easing:** `cubic-bezier(0.22, 1, 0.36, 1)` (calm out-expo). **Durations:** 240–520ms (reuse repo motion budget).

### 3.2 Tier 2 — Narrative (reveals, transitions, scroll)

Movement that *clarifies* progression. Used for section entrances, the dashboard assembling, stage-to-stage transitions.
- Sections enter with a **12–16px upward translate + fade + slight blur-in** (`filter: blur(8px)→0`), staggered children (60–80ms).
- State transitions (idle→running→needs_approval→successful) **morph in place** — the run-control dock re-composes; it does not page-jump.
- Scroll is the storyteller: each Act is a held beat, not a continuous river. Use **pin + release** so the page *stops*, delivers, then moves on. This is the antithesis of "scroll to see more."
- **Easing:** same out-expo; transitions 400–600ms.

### 3.3 Tier 3 — Theatrical (the "wow" peaks, ~4 total)

Reserved, expensive, deliberate. Each is a designed shot.
1. **Hero ignition** — on load, the glyph assembles from particles/strokes and the headline resolves (GSAP timeline).
2. **The run igniting** — when a quick run starts, the verdict grid lights up cell-by-cell as evidence "arrives," sweeping with the accent.
3. **The red→green flip** — at the before/after reveal, DENY cells cascade to APPROVE; the lift counter spins up. The single most important shot in the demo.
4. **Memory-off decay** — in the counterfactual, the accent light *drains* out of the panel, color desaturates, the score bar retreats — proving the memory was load-bearing.

**Rule:** never two Tier-3 moments on screen at once. Between peaks, return to Tier 1 calm. Contrast is the product.

### 3.4 Cross-cutting

- **Reduced motion:** honor `prefers-reduced-motion`. All Tier-3 moments degrade to a clean cross-fade to the end-state (the *information* never depends on motion). The verdict flip becomes an instant recolor; the counter shows final value.
- **Pacing for camera:** every theatrical beat is tuned to ~1.2–2.0s so a presenter can narrate over it without dead air or rushing. Build a `--sc-beat: 1.4s` token and derive timings from it.
- **Coherence:** one easing family, one accent, one breath rhythm. The hero glyph's breath rate, the telemetry blink, and the section-enter cadence should feel like the same heartbeat.

---

## 4. Framework / tool allocation

| Concern / section | Build with | Why |
|---|---|---|
| Page shell, routing, layout, responsive grid | **Next.js (App Router) + Tailwind v4** | Composition environment; nothing else touches structure |
| Section reveals, staggered children, state-driven UI (idle→running→approval), dock recomposition, tabs, hover variants | **framer-motion** | Variant/`AnimatePresence` model is perfect for the run state machine; declarative, ties to React state |
| Hero ignition timeline; scroll-pinned Acts; the red→green verdict cascade synced to scroll; architecture diagram drawing itself; finale orchestration | **GSAP + ScrollTrigger** | Frame-accurate timelines, pin/scrub, sequencing many layered tweens — framer can't choreograph multi-element scrubbed sequences as cleanly |
| Hero living glyph; the system "pulse" status orb; MCP on/off memory toggle; button press/ignite states; the breathing/idle loops; the lift gauge needle | **Rive** | Stateful, tactile, looping, input-driven micro-animation with crisp vector at any size and tiny payload; reacts to a single state input (e.g., `runStatus`, `memoryOn`) far more elegantly than hand-rolled SVG+JS |

**Stack philosophy recap:** Next.js+framer is the shell and 80% of motion. Rive owns the handful of *stateful, tactile, looping* elements. GSAP owns the ~5 *scrubbed/sequenced cinematic* moments. Do not let GSAP and framer fight over the same element — assign each element one owner.

---

## 5. Judge flow / narrative structure

The page is a **six-act film** the presenter scrolls through top to bottom while narrating. Each Act answers one judge question.

| Act | Judge question answered | Feeling | Tier |
|---|---|---|---|
| **I — Hook** | "What am I looking at?" | Arrival, intrigue | 3 (ignition) |
| **II — The Problem / Thesis** | "Why is this hard, why does it matter?" | Tension, clarity | 2 |
| **III — The Live Instrument (dashboard)** | "Is this real? Can it actually do it?" | Proof, control, suspense | 2→3 (run ignites) |
| **IV — Before / After (the payoff)** | "Did it actually get better?" | Payoff, delight | 3 (red→green) |
| **V — The Intelligence Layer (architecture + memory)** | "How does it work? Is it novel?" | Comprehension, "oh, that's clever" | 2→3 (memory-off decay) |
| **VI — Impact & Close** | "Why should this win?" | Conviction, resonance | 3 (finale) |

This maps to the live demo script in `docs/demo-cheatsheet-pm.md`: the presenter starts a quick check (Act III), watches pre/training/post fill, hits **needs approval**, approves, sees holdout improve (Act IV), then shows the memory-off counterfactual (Act V). The page choreography and the live backend run are the *same story*.

---

## 6. Section-by-section experience plan

> Copy below is the proposed new `/showcase` copy. It replaces the current headline ("This tool improves from its own observability.") with sharper, judge-facing language. Tune freely.

### ACT I — Hero ("The Observatory")

- **Purpose:** Establish in 3 seconds that this is a real, ambitious, self-improving system. Hook.
- **Layout:** Full-viewport, asymmetric. Left: eyebrow + serif headline + one-line subhead + a single quiet primary CTA ("Begin a live run" → smooth-scrolls/pins to Act III). Right/offset: the **living glyph** (Rive) — a slowly breathing form suggesting an eye/aegis/shield made of moving evidence. Bottom-left: a thin live telemetry strip (mono) that looks like a heartbeat readout.
- **Copy style:** Cinematic, declarative, confident.
  - Eyebrow (mono): `HEURISTICS · SELF-IMPROVING APPEAL ENGINE`
  - Headline (serif): **"Watch a system teach itself."**
  - Subhead (Inter): "Heuristics drafts insurance-denial appeals, grades its own work against a held-out benchmark, and rewrites its own playbook from what it learns. No hand-tuning. Below, it does it live."
- **Motion:** Tier 3 ignition on load — glyph assembles, headline resolves word-by-word (blur-in), telemetry strip starts streaming. Then settles to Tier 1 breathing.
- **Interaction:** CTA has a Rive ignite state on hover. Glyph subtly tracks cursor (parallax, ≤6px).
- **Register:** Theatrical → settles to quiet.
- **Feel:** "This is a finished, living product, and I'm about to see it work."

### ACT II — The Thesis ("Most agents are frozen")

- **Purpose:** Frame why self-improvement is the hard, valuable thing — without a dry "problem" slide.
- **Layout:** Pinned editorial beat. A large serif statement center-stage; on scroll, a contrast pair resolves: **"Static-prompt agents"** (a dim, motionless node) vs **"Heuristics"** (a node that pulses and rewrites itself). Minimal — two ideas, lots of black.
- **Copy:**
  - Statement (serif): **"Most AI agents never improve. They answer the same way on day one and day one thousand."**
  - Turn (serif, accent): **"Heuristics reads its own past evaluations before it drafts — and gets measurably better."**
  - Support (mono caption): `THESIS — if turning memory off doesn't degrade quality, the idea has failed. So we'll turn it off later and show you.`
- **Motion:** Tier 2. Scroll-driven: the static node stays grey/inert; the Heuristics node ignites and a thin accent line writes the word "learns." Foreshadows the memory-off proof.
- **Interaction:** None required (a held beat). Optional hover on the two nodes shows a one-line tooltip.
- **Register:** Immersive, quiet tension.
- **Feel:** "Okay — the claim is bold and falsifiable. Show me."

### ACT III — The Live Instrument (the dashboard / proof)

This is the existing functional core — **all preserved logic lives here.** It must look like a real control room.

- **Purpose:** Prove it works, live, with the judge watching. This is where `startQuickRun` etc. fire.
- **Layout:** A cohesive "instrument console":
  - **Top:** Mode header — serif "Human-approved learning" + mono sub `QUICK: {quick_train} TRAIN · {quick_holdout} HOLDOUT · SLICE {quick_slice}`.
  - **Left rail — Run controls (the floating dock):** two run cards (**Quick check**, **Serious pass** — locked until quick succeeds), plus the conditional **Roll back latest update**. The dock is the one element with a real drop-shadow; it can become sticky as Act III pins.
  - **Center — Run status panel:** the live state machine. Session id (mono), current **stage** as a large serif heading that morphs as stages advance (`measure_before` → `train_gepa` → `waiting_for_approval` → `promote` → `measure_after`), progress as an animated mono fraction + thin accent progress line, error/regression banners, and the **Approve / Reject** buttons that appear at `needs_approval`.
  - **Below — The Learning Matrix (signature widget):** the 6-box matrix (Demo / Serious columns × Pre-training / Training[before·after] / Post-training). Verdict cells are luminous status tiles that **light up as results arrive** and **flip red→green** across the training boundary.
- **Copy style:** Mono telemetry + short serif stage labels. Add a one-line "what's happening" caption under the stage heading, e.g. `Measuring held-out cases with the current prompt — no learning yet.` (sourced from the demo cheatsheet's stage table).
- **Motion:**
  - Idle → the console is calm, a slow status-orb pulse (Rive).
  - On **Run quick check**: Tier 3 ignition — the matrix wakes, the status orb shifts to "running," cells begin populating left-to-right as the poll returns data.
  - Stage changes **morph** the heading (crossfade + 8px rise); the progress line eases.
  - At **needs_approval**: everything calms, the Approve/Reject buttons rise in with a soft accent ring — a deliberate held beat ("human in the loop").
  - Approve → promotion stage animates; post-training column fills.
  - Regression → the amber banner slides in (Tier 2), never jarring.
- **Interaction:** All real. Buttons have Rive press/ignite states. Verdict cells show case id + verdict on hover (preserve existing title behavior, upgrade to a styled tooltip). Polling cadence unchanged (10s).
- **Register:** Proof + suspense. Theatrical only at ignition and the approval beat.
- **Feel:** "This is genuinely running. I'm watching a real system work and I get to make the call."

> **Demo-resilience note:** the backend run is slow (10s polling, minutes long). The page must look stunning *while waiting*. Design the running state to be inherently cinematic (streaming telemetry, breathing orb, cells trickling in) so dead time reads as suspense, not lag. Provide a tasteful skeleton/standby state, never a bare spinner.

### ACT IV — Before / After (the payoff)

- **Purpose:** The emotional climax — the same case, measurably better. Built from existing `bundle` (`VersusPanel` + `DiffCard`).
- **Layout:** The page's one symmetric moment — true 50/50 split. **Left: v1 (earlier draft).** **Right: v3 (improved draft).** Each side: a composite-quality gauge, a verdict lamp (DENY left → APPROVE right), and a letter excerpt. Between them, centered, the **lift counter**: `+{lift_relative_pct}%`. Below, the "What changed, and why" diff list animates in as evidence bullets.
  - **Case selection (replaces the pills):** present **one featured case** prominently (insurer · denial_type as a serif label, not a pill). Provide a quiet **cycler** — left/right chevrons or a slim "Next case" control in mono — that calls the existing `setSel`. Optionally a thin horizontal "filmstrip" of case dots beneath. The point: case-switching is in-flow and elegant, not a row of 10 pills competing for attention. **Keep `sel`/`getShowcase` logic intact.**
- **Copy:**
  - Section (serif): **"The same denial. Before and after it learned."**
  - Verdict labels (mono): `SIMULATOR VERDICT — DENY` → `SIMULATOR VERDICT — APPROVE`
  - Lift (mono, large): `MEASURED LIFT ON HELD-OUT CASES  +{x}%`
  - Diff header (serif): **"What changed, and why."**
  - Honest caveat for illustrative cases: keep the existing neutral note ("Illustrative for this case. Measured numbers shown where a run is recorded.").
- **Motion:** **Tier 3 — the red→green flip.** On scroll into view (GSAP ScrollTrigger): the left gauge fills to its (lower) value, the right gauge overtakes it, the verdict lamp flips DENY→APPROVE with an accent bloom, and the lift counter spins up to `+{x}%`. Diff bullets stagger in after. This is the shot the whole video is built around — tune it to `--sc-beat`.
- **Interaction:** Case cycler (real `setSel`). Hover a diff bullet to highlight the corresponding sentence in the excerpt (nice-to-have). "Open the underlying trace" link (keep `phoenix_url`) styled as a mono "inspect" affordance.
- **Register:** Theatrical, then satisfying stillness on the final numbers.
- **Feel:** "It actually got better. I can see it and the number proves it."

### ACT V — The Intelligence Layer (architecture + memory proof)

- **Purpose:** Explain *how* and prove novelty: the judge panel, the Phoenix-memory loop, GEPA, the human gate — and then the killer counterfactual.
- **Layout:** Two beats.
  - **V-a — The loop diagram (self-drawing schematic):** a horizontal pipeline that draws itself on scroll: `Draft → Judge panel (7 dimensions) → Phoenix memory → GEPA rewrites playbook → Human approves → Promote`. Nodes are matte panels; the connecting path writes in with the accent; small Rive icons mark each node. A callout on the Judge node: "Seven-dimension panel — two hard safety gates, five weighted scores. Six run as ADK agents." A callout on Phoenix: "It reads its own past traces before drafting."
  - **V-b — The counterfactual (memory on/off):** built from existing `CounterfactualCard` (`on_composite` / `off_composite`). Two gauges — **Memory on** vs **Memory off** — with a real, tactile **toggle (Rive)**. Flipping to "off" triggers Tier-3 decay: the accent light drains, color desaturates, the score bar retreats to the lower value. This *visually proves* the thesis from Act II.
- **Copy:**
  - Section (serif): **"How it gets better."**
  - Loop caption (Inter): "Heuristics grades every draft against a held-out benchmark, writes the result to its own memory, and an optimizer rewrites its playbook from the pattern of its past failures. A person approves before anything ships."
  - Counterfactual (serif): **"Switch off its memory, and quality drops."**
  - Support (Inter): "The agent reads its own past evaluations before it drafts. Take that memory away and the same case scores lower — the memory is doing real work, not decorating the system."
- **Motion:** V-a Tier 2 self-draw on scroll (GSAP). V-b Tier 3 decay on toggle (Rive state + framer for the bar). Never run both at once.
- **Interaction:** The memory toggle is the hero interaction here — make it feel mechanical and consequential (haptic-looking, audible-looking). Optional hover on each pipeline node reveals a one-line spec.
- **Register:** Comprehension, then a small theatrical proof.
- **Feel:** "I understand the mechanism, and they just *proved* it's load-bearing instead of asserting it."

### ACT VI — Impact & Close

- **Purpose:** Land the "why this wins" and leave a memorable final frame.
- **Layout:** Return to hero-like spareness. One big serif statement, a tight row of three anchored metrics (mono, count-up), the glyph returns (now "settled"/brighter), and a quiet end-card.
- **Copy:**
  - Statement (serif): **"99% of denied claims are never appealed. Heuristics is the part of the system that keeps getting better at the fight."**
  - Metrics (mono, count-up): e.g. `BENCHMARK QUALITY  0.40 → 0.75` · `JUDGE DIMENSIONS  7` · `HUMAN-APPROVED  ALWAYS`. (Use only numbers backed by the docs/runs; mark targets honestly.)
  - End-card (mono): `HEURISTICS · built on Google ADK + Gemini · observability by Arize Phoenix`
- **Motion:** Tier 3 finale — metrics count up in sequence, the glyph brightens and exhales once, a final accent hairline draws across the footer. Then full stillness (good final frame to end the recording on).
- **Interaction:** Minimal. Maybe the glyph responds once to hover. A quiet "Replay the run" affordance for second takes.
- **Register:** Theatrical resolve → stillness.
- **Feel:** "That was a real, ambitious, *finished* product. I remember it."

---

## 7. Microinteractions library

A coherent kit. Build the primitives once; reuse everywhere.

- **Buttons:** rest (matte, hairline) → hover (accent hairline + faint glow + 1px lift) → press (Rive ignite: a quick accent sweep across the label) → loading (label morphs to mono status, e.g. `STARTING…`) → done (brief accent bloom, no confetti). Active scale 0.97 (keep existing).
- **Cards / panels:** enter (blur-in + 12px rise, staggered). Hover (hairline brightens to `--sc-hairline-strong`, inner top-highlight intensifies). Active/selected (accent ring + raised luminosity).
- **Tabs (Demo/Serious columns act as tabs):** the active column carries the accent underline that *slides* between columns (framer `layoutId`); inactive is dimmed.
- **Toggles (memory on/off):** Rive, mechanical. The knob travels with weight; "off" drains color from the dependent panel. The most tactile control on the page.
- **Hover states:** universal rule — hover *adds light*, never moves layout. Accent edge + subtle glow. Cursor-proximity parallax only on the hero glyph.
- **Metric counters:** mono, ease-out count-up (GSAP or framer `useMotionValue`), with a 1-frame accent flash when they settle. Never linear; never instant (except reduced-motion).
- **Charts / gauges:** the composite-quality gauge fills with an eased sweep; a thin threshold tick remains static so the fill "reaches past" it. Verdict grid = the signature: cells fade/scale in as data arrives; flip animation on red→green is a per-cell stagger (cascade), not all-at-once.
- **State transitions (the run machine):** morph in place via `AnimatePresence` — the stage heading crossfades + rises; the dock recomposes; approval buttons rise with an accent ring. No layout jumps between states.
- **Loading / processing:** **never a bare spinner.** Use streaming mono telemetry + a breathing status orb (Rive) + cells trickling in. Standby (pre-run) = a calm skeleton with a slow shimmer.
- **Empty states:** the current "No live run started" becomes an inviting standby console — dim matrix outline, a single pulsing "Begin a live run" affordance, mono hint `AWAITING SESSION`.
- **Success moments:** dignified, not celebratory — an accent bloom + the number settling. (Matches product values: acknowledge, don't celebrate.)
- **Error / regression:** amber banner slides in calmly with the real message + code; the orb shifts to a warning hue. Honest, not alarming.
- **Also worth adding:** a persistent **mini "now playing" HUD** (sticky, top-right, mono) showing `STATUS · STAGE · N/M` during a run — so on video the current state is always legible even when the matrix is off-screen. A subtle **scroll progress** accent line at the very top tracking the six Acts.

---

## 8. Rive opportunities (build these in Rive)

For each: why Rive beats native framer/SVG here.

1. **Hero living glyph (the Heuristics "eye/shield").** Continuous breathing loop + cursor-reactive state + an "ignite" entrance + a "settled/brighter" finale state. *Why Rive:* one artboard with state-machine inputs (`breath`, `ignite`, `settle`) and cursor input — crisp vector at any size, tiny payload, smoother than orchestrating dozens of SVG keyframes in JS.
2. **System status orb / pulse.** Single input `runStatus` (idle | running | needs_approval | success | error) drives color, pulse rate, and shape. *Why Rive:* state-driven looping animation is exactly Rive's model; mapping one React state value to a rich animated loop is trivial and buttery vs. hand-rolled.
3. **Memory on/off toggle (Act V centerpiece).** A mechanical switch whose "off" state visibly drains light. *Why Rive:* tactile, weighty, state-perfect interaction with a single boolean input; the "decay" can be authored as a state transition, not coded.
4. **Primary button ignite state.** Accent sweep across the label on press. *Why Rive:* reusable, consistent, GPU-light micro-feedback that reads as "premium hardware" — more refined than a CSS pseudo-element.
5. **Lift gauge / needle (Act IV center).** A gauge that sweeps to `+{x}%`. *Why Rive:* a value-driven needle with overshoot/settle physics looks far better than an SVG arc tween, and accepts the percent as a number input.
6. **Pipeline node icons (Act V loop).** Small animated marks for Draft / Judge / Memory / Optimize / Approve / Promote that subtly come alive as the path reaches them. *Why Rive:* a set of tiny looping icons with an "active" input, consistent in weight — avoids the generic-Lucide tell the brief warns about.
7. **Verdict-cell flip (optional, if perf allows).** A reusable red→green cell with a `verdict` input and a satisfying flip. *Why Rive:* if there are dozens of cells, one shared Rive instance with per-cell inputs can be lighter and more uniform than many JS animations — **benchmark first**; if cell count is high, prefer CSS/GSAP for the cascade and keep Rive for the hero cells only.

*(That's 7 — comfortably in the 5–10 range. Items 1–5 are must-haves; 6–7 are upside.)*

---

## 9. GSAP + ScrollTrigger opportunities

For each: why GSAP, not framer.

1. **Hero ignition timeline.** Sequenced: glyph assembles → headline words resolve (blur-in, staggered) → telemetry strip starts → settle. *Why GSAP:* a precise multi-element timeline with fine offsets is what GSAP timelines are for; framer stagger is coarser.
2. **Act II/III scroll-pinning.** Pin the thesis beat and the dashboard while their content advances, then release. *Why GSAP ScrollTrigger:* pin + scrub + snap is GSAP's core competency; replicating robust pinning in framer is fragile.
3. **The red→green verdict cascade (Act IV).** Scroll-scrubbed (or triggered) per-cell flip + gauge race + counter spin, all on one timeline so they fire in lockstep. *Why GSAP:* synchronizing many elements on a single scrubbed timeline is exactly GSAP; this is the money shot and needs frame accuracy.
4. **The self-drawing architecture loop (Act V-a).** SVG path `drawSVG`-style reveal of the pipeline connectors as nodes activate on scroll. *Why GSAP:* path-length drawing synced to scroll progress is clean in GSAP and awkward in framer.
5. **Finale orchestration (Act VI).** Count-ups, glyph brighten/exhale, footer hairline draw — sequenced. *Why GSAP:* it's a closing *timeline*, multiple elements in a designed order.

**Where GSAP should NOT be used:**
- The run **state machine** (idle→running→approval→success). That's React-state-driven UI — use framer `AnimatePresence`/variants. GSAP fighting React re-renders here causes bugs.
- Hover/press feedback, tabs, card enters — framer (or Rive for the tactile ones).
- The breathing glyph, status orb, toggle — Rive.
- Anything that must re-run on every poll update — keep it declarative (framer), not imperative GSAP.

---

## 10. Next.js App Router + Tailwind v4 component plan

### 10.1 Page structure

Keep `frontend/src/app/showcase/page.tsx` as the **stateful container** — all hooks, handlers, polling, and state stay here unchanged. It becomes thin: it owns state and renders Act components, passing data/handlers down as props.

```
app/showcase/page.tsx                 // ← all existing state/effects/handlers PRESERVED; renders <ShowcaseFilm>
components/showcase/
  ShowcaseFilm.tsx                     // layout spine: orders the six Acts, owns scroll/GSAP context
  acts/
    ActHero.tsx                        // Act I  (Rive glyph, GSAP ignition)
    ActThesis.tsx                      // Act II (pinned)
    ActInstrument.tsx                  // Act III — wraps run controls + status + matrix (RECEIVES all handlers/session as props)
    ActBeforeAfter.tsx                 // Act IV — Versus/Diff + case cycler (receives bundle, sel, setSel)
    ActIntelligence.tsx               // Act V  — architecture loop + counterfactual toggle
    ActImpact.tsx                      // Act VI — metrics + finale
  console/
    RunControlDock.tsx                 // quick/serious/rollback cards (props: startQuick, startSerious, rollback…, seriousUnlocked)
    RunStatusPanel.tsx                 // refactor of existing — same props, new visuals
    LearningMatrix.tsx                 // refactor of existing — same data, luminous cells
    VerdictCell.tsx                    // the signature tile
    StatusHUD.tsx                      // sticky now-playing HUD
  versus/
    VersusPanel.tsx                    // restyle existing
    DiffCard.tsx                       // restyle existing
    CounterfactualCard.tsx             // restyle existing + Rive toggle
    CaseCycler.tsx                     // NEW — replaces CasePicker UI, drives setSel
  primitives/
    Gauge.tsx, MetricCounter.tsx, GlassPanel.tsx, MonoLabel.tsx, AccentLine.tsx
  rive/
    RiveGlyph.tsx, StatusOrb.tsx, MemoryToggle.tsx, RiveButton.tsx, LiftGauge.tsx
lib/
  motion/easings.ts                    // shared cubic-beziers, --sc-beat
  motion/useGsapContext.ts             // gsap.context + ScrollTrigger cleanup helper
styles/showcase.css                    // [data-theme="showcase-dark"] token block (scoped; does NOT touch /appeal)
```

**Critical:** `ActInstrument`, `RunControlDock`, `RunStatusPanel`, `LearningMatrix` are **presentational** — they receive the existing session object and handler callbacks as props. The state stays in `page.tsx`. This is how we "change only the visual layer."

### 10.2 Section hierarchy & sticky/pinned behavior

- `ShowcaseFilm` sets up a single `gsap.context()` (cleaned up on unmount) and registers ScrollTriggers for Acts I, II, III, IV, V-a, VI.
- Pin Act II (short pin) and Act III (pin while the run console is the focus). Use `ScrollTrigger.matchMedia` so pinning only engages ≥ `lg`.
- Act IV's red→green cascade fires on a ScrollTrigger `onEnter` (not scrub) so it plays as a clean shot at demo pace; reduced-motion → instant end state.

### 10.3 Variants organization (framer)

- Central `lib/motion/easings.ts` exports `EASE_OUT_EXPO`, `DUR`, `BEAT`, and shared `variants` (sectionEnter, staggerChildren, dockState, statusMorph).
- The run state machine uses one `variants` object keyed by `runSession?.status` so idle/running/needs_approval/success/error all morph through the same declarative system.

### 10.4 Breakpoints & responsiveness

- Design desktop-first (demo is recorded on desktop), but keep ≥ `md` graceful.
- `sm` (<640): stack everything single-column; matrix scrolls horizontally; disable pins; Tier-3 moments become simple fades. `md` (768): two-up where natural. `lg` (1024)+: full cinematic layout, pins active. `xl` (1280)+: the intended composition with generous gutters.
- Verdict matrix: cap cell size, allow internal scroll (preserve existing max-height behavior) so large cohorts never blow the layout.

### 10.5 Native vs embedded

- **Native (framer/Tailwind):** all layout, panels, gauges, counters, tabs, state morphs.
- **Embedded (Rive `.riv`):** glyph, status orb, memory toggle, button ignite, lift gauge, pipeline icons. Lazy-load Rive canvases (`dynamic(() => …, { ssr: false })`) and only mount when the Act is near viewport (IntersectionObserver) to protect first paint.
- **GSAP:** imperative, inside `useGsapContext`, scoped to refs — never animating React-controlled state nodes.

### 10.6 Performance / recording quality

- Lazy-mount Rive + heavy GSAP per-Act; unmount off-screen canvases to keep GPU free for smooth capture.
- Prefer `transform`/`opacity`/`filter` only (compositor-friendly); avoid layout-thrash animations.
- Cap blur layers (backdrop-blur is expensive — limit concurrent glass panels on screen).
- Respect `prefers-reduced-motion` globally via a single guard in `useGsapContext` + framer `MotionConfig reducedMotion="user"`.
- Target a locked 60fps on the demo machine; if a Tier-3 moment can't hold 60fps, simplify it (see §12).
- Keep `.riv` files small; subset fonts (already self-hosted). Pre-load the hero `.riv` and the first Act's assets.

---

## 11. Exact build prompts (hand to the next agent, section by section)

> Each prompt assumes the dark token block from §2 exists as `styles/showcase.css` and the shared motion helpers from §10. **Every prompt must preserve the data-layer contract in §0.2.** Copy is in §6; tune as needed.

### 11.1 Hero (Act I)

> Build `ActHero.tsx` — a full-viewport, asymmetric hero on `--sc-bg` with a faint single radial key-light (accent, ~6%) behind the headline. Left column (~58% width): a mono eyebrow `HEURISTICS · SELF-IMPROVING APPEAL ENGINE`, a Source-Serif-4 headline `clamp(3rem,6vw,5.5rem)` weight 600 reading "Watch a system teach itself.", an Inter subhead (see §6), and one primary CTA "Begin a live run" that smooth-scrolls to Act III. Right/offset column: mount `RiveGlyph` (breathing loop, cursor-reactive ≤6px parallax). Bottom-left: a thin JetBrains-Mono telemetry strip that streams faux-live readout lines. On mount, run a GSAP timeline (via `useGsapContext`): glyph `ignite` input fires, headline resolves word-by-word with `filter: blur(8px)→0` + 12px rise staggered 70ms, telemetry strip begins, then glyph settles to `breath`. Honor reduced-motion (show end state instantly). All motion uses `EASE_OUT_EXPO`. No layout shift; CTA hover triggers Rive ignite. Mobile: single column, glyph above, no parallax.

### 11.2 Thesis (Act II)

> Build `ActThesis.tsx` — a short scroll-pinned editorial beat (pin only ≥lg via `ScrollTrigger.matchMedia`). Center a serif statement "Most AI agents never improve…" then, on scroll progress, resolve a contrast pair: a dim grey inert node labeled "Static-prompt agents" and an accent node labeled "Heuristics" that ignites (Rive or CSS pulse) while a thin accent line writes the word "learns". Add the mono caption foreshadowing the memory-off test (see §6). Keep it 90% black/negative space — two ideas only. Tier-2 motion, `EASE_OUT_EXPO`, reduced-motion → static end state. No interaction required beyond optional hover tooltips.

### 11.3 Dashboard / Live Instrument (Act III)

> Build `ActInstrument.tsx` + `console/*` as a **presentational** wrapper around the EXISTING showcase state. It receives as props: `manifest`, `runSession`, `runErr`, `rollbackTarget`, `seriousUnlocked`, and the handlers `startQuick`, `startSerious`, `cancelCurrentRun`, `approveCurrentRun`, `rejectCurrentRun`, `rollbackLatestRun`. **Do not create new state or fetching here.** Compose: (a) `RunControlDock` — quick/serious/rollback cards, serious disabled unless `seriousUnlocked`, real handlers wired, Rive button ignite states, the dock gets the page's one real drop-shadow and becomes sticky while Act III is pinned (≥lg); (b) `RunStatusPanel` — restyle the existing logic: mono session id, the `current_stage` rendered as a large serif heading that morphs via framer `AnimatePresence` on change (crossfade + 8px rise) with a one-line plain caption per stage (use the stage→caption map from `docs/demo-cheatsheet-pm.md`), an eased mono progress fraction + thin accent progress line, amber regression banner on `regression_detected`, error box on `diagnostics.last_error`, and Approve/Reject buttons that rise in with an accent ring ONLY at `needs_approval`, Cancel while running; (c) `LearningMatrix` — restyle the existing 6-box matrix (Demo/Serious × Pre/Training[before·after]/Post) with `VerdictCell` luminous tiles (`--sc-accent` APPROVE / `--sc-deny` DENY) that fade+scale in as poll data arrives; preserve hover title (case id + verdict) as a styled tooltip; preserve internal scroll for large cohorts. Add `StatusOrb` (Rive, input = `runSession.status`) and a sticky `StatusHUD` (mono `STATUS · STAGE · N/M`). Running/standby states must be cinematic (streaming telemetry + breathing orb + trickling cells) — NEVER a bare spinner; provide a calm skeleton standby for the no-session state ("Begin a live run" / `AWAITING SESSION`). Keep the 10s polling untouched. Reduced-motion: cells recolor instantly, headings cross-fade. Use framer for all state morphs; do NOT use GSAP on this state machine.

### 11.4 Before / After (Act IV)

> Build `ActBeforeAfter.tsx` from the existing `bundle` (restyle `VersusPanel`, `DiffCard`; add `CaseCycler`). True 50/50 split: left = v1 (lower gauge, DENY lamp, excerpt), right = v3 (higher gauge, APPROVE lamp, excerpt), centered `LiftGauge` (Rive) showing `+{bundle.lift_relative_pct}%`. Below: "What changed, and why." diff bullets stagger in. **Replace the removed pill picker** with `CaseCycler` — a featured-case serif label (`{insurer} · {denial_type}`) + quiet mono prev/next controls (and optional dot filmstrip) that call the EXISTING `setSel`; keep `getShowcase(sel)` flow intact. On ScrollTrigger `onEnter` (not scrub), run the Tier-3 timeline: left gauge fills, right gauge overtakes, verdict lamp flips DENY→APPROVE with an accent bloom, `LiftGauge` needle sweeps to value, diff bullets stagger after — all tuned to `--sc-beat` (~1.4s). Preserve the illustrative-vs-measured caveat note and the `phoenix_url` "Open the underlying trace" link (styled as a mono "inspect" affordance). Reduced-motion → instant end state. This is the demo's money shot; make it frame-accurate.

### 11.5 Architecture / Intelligence (Act V)

> Build `ActIntelligence.tsx` in two beats. V-a: a horizontal self-drawing pipeline `Draft → Judge panel → Phoenix memory → GEPA optimizer → Human approval → Promote`; nodes are `GlassPanel`s with small Rive icons; connectors are an SVG path that draws in on scroll (GSAP path-length reveal) as each node activates. Callouts: on Judge — "Seven-dimension panel: two hard safety gates + five weighted scores. Six run as ADK agents."; on Phoenix — "It reads its own past traces before drafting." V-b: restyle the existing `CounterfactualCard` (`on_composite`/`off_composite`) as two `Gauge`s, "Memory on" vs "Memory off", controlled by a `MemoryToggle` (Rive, boolean input). Flipping to OFF triggers a Tier-3 decay: accent light drains from the panel, colors desaturate (CSS filter), the score bar retreats to `off_composite`. Keep the existing honest footnote about design-target figures. Section copy per §6. Never run V-a draw and V-b decay simultaneously. Reduced-motion: pipeline draws instantly; toggle swaps values without the decay animation.

### 11.6 Impact / Close (Act VI)

> Build `ActImpact.tsx` — return to hero-like spareness on `--sc-bg`. One serif statement ("99% of denied claims are never appealed…"), a tight row of three mono `MetricCounter`s that count up in sequence on enter (e.g. `BENCHMARK QUALITY 0.40 → 0.75`, `JUDGE DIMENSIONS 7`, `HUMAN-APPROVED ALWAYS` — only doc-backed numbers; mark targets honestly), and the `RiveGlyph` returning in a brighter "settled" state that exhales once. Finale GSAP timeline: counters sequence, glyph brightens, a footer accent hairline draws across, then full stillness (a clean final frame to stop recording on). Mono end-card `HEURISTICS · built on Google ADK + Gemini · observability by Arize Phoenix`. Optional quiet "Replay the run" control. Reduced-motion → show final values immediately.

---

## 12. Final polish checklist (for recording)

### Visual QA
- [ ] Background is deep graphite, never pure `#000` (check for banding on the recorded file, not just the monitor).
- [ ] Chroma appears only on meaning (accent fills, DENY cells, banners). Scan for any stray colored pixel.
- [ ] One glow budget honored — only the accent glows; no decorative gradients (re-check against the banned cliché-AI look).
- [ ] Hairlines crisp at the recording resolution; inner top-highlights visible on panels.
- [ ] Type hierarchy reads at video bitrate: serif headlines, mono telemetry, Inter body all legible when compressed.
- [ ] Verdict cells read clearly as red vs green for a colorblind viewer (shape/label backup on hover, not color alone).

### Motion QA
- [ ] One easing family everywhere; no default linear tweens leaked in.
- [ ] Only one Tier-3 moment on screen at a time; calm between peaks.
- [ ] No layout shift on hover (hover adds light, not movement).
- [ ] GSAP contexts clean up on unmount (no orphan ScrollTriggers when navigating away).
- [ ] `prefers-reduced-motion` path verified — every Tier-3 beat degrades to a clean end-state; information never depends on motion.
- [ ] Locked 60fps through each Tier-3 moment on the demo machine; drop the heaviest layer if not.

### Recording QA
- [ ] Sticky `StatusHUD` keeps `STATUS · STAGE · N/M` legible even when the matrix is scrolled off — so the run state is always on-camera.
- [ ] Running/standby states look intentional during the slow 10s-poll waits (suspense, not lag); no bare spinner anywhere.
- [ ] Each Act has a clean "hold" frame to land on while narrating; the finale ends on stillness.
- [ ] Tier-3 beats tuned to `--sc-beat` (~1.4s) so narration fits without dead air or rush.
- [ ] "Replay the run" / re-seed path works for clean second takes (and day-zero reset script is known: `backend/scripts/reset_to_day_zero.py`).

### Responsiveness QA
- [ ] ≥lg: full cinematic layout with pins. md: graceful two-up. sm: single column, pins off, Tier-3 → fades, matrix scrolls horizontally.
- [ ] No horizontal overflow at any breakpoint; verdict matrix never blows the layout (internal scroll preserved).
- [ ] Rive canvases lazy-mount near viewport and unmount off-screen.

### Demo pacing QA
- [ ] Page choreography matches the live backend script (cheatsheet §"Happy path"): start quick → pre/training fill → needs_approval beat → approve → post fills → before/after payoff → memory-off proof.
- [ ] The "human in the loop" approval beat is a deliberate pause, not a blip.
- [ ] Six Acts answer the six judge questions (§5) in order; nothing redundant.

### Data-layer integrity QA (must pass before merge)
- [ ] All four `useEffect`s, the 10s polling + terminal guard, and all six handlers behave identically to before (diff the network calls).
- [ ] `seriousUnlocked` gate, regression banner, rollback, approve/reject all still fire correctly.
- [ ] Case pills removed; `sel`/`setSel`/`getShowcase`/`bundle` preserved and now driven by `CaseCycler`.
- [ ] `/appeal` untouched (no shared component regressions; the dark token block is scoped and does not leak into the light theme).

### What to simplify if it starts feeling too busy
1. **Cut Tier-3 count from 4 → 3:** keep hero ignition, the red→green flip, and memory-off decay; drop the finale orchestration to a simple count-up.
2. **Drop scroll-scrubbing, keep triggered reveals:** `onEnter` plays are more reliable on camera than scrub and read just as cinematic.
3. **Reduce Rive set to the 3 must-haves:** glyph, status orb, memory toggle. Replace button-ignite/lift-gauge/pipeline-icons with CSS/framer.
4. **Flatten the architecture diagram** to a static elegant schematic with a single accent line, if the self-draw fights perf.
5. **Remove the radial key-light** if it ever reads as a generic gradient.
6. **Rule of thumb:** when in doubt, take *motion* out and add *contrast* (negative space + one luminous accent) — restraint is what reads as "expensive."

---

## Appendix — product facts to keep copy honest (from the docs)

- **What Heuristics is:** drafts insurance-denial appeals; self-improves by reading its own Phoenix evaluation traces and rewriting its playbook (GEPA), with a human approval gate. (`docs/product-soul.md`.)
- **Thesis (falsifiable, and we prove it):** if turning Phoenix memory off does *not* degrade quality, the core idea failed — so the counterfactual is the centerpiece. (`product-soul.md` §PMF.)
- **Quick vs serious run:** quick = small cohort (`quick_train`+`quick_holdout`, slice-scoped); serious = full pool, **locked until quick succeeds**. (`current-state.md`, `demo-cheatsheet-pm.md`.)
- **Run stages:** `queued → measure_before → train_gepa → waiting_for_approval(needs_approval) → promote → measure_after → successful`; can `fail/cancel/reject`; rollback restores the previous promoted prompt/playbook. (`demo-cheatsheet-pm.md`.)
- **Judge panel:** seven dimensions — J1 Safety + J2 Faithfulness are hard gates (PASS/FAIL, never averaged); J3 Grounding (30%), J4 Case-specific rebuttal (20%), J5 Evidence completeness (15%), J6 Appeal-vector capture (25%), J7 Persuasive coherence (10%); anchors 1/3/5 → 0.2/0.6/1.0. Recent build runs six of these as ADK `LlmAgent`s in a Workflow. (`docs/evals/2026-05-29-part-a-judge-panel-spec.md`, commit `7e0bc75`.)
- **MCP on/off:** Phoenix MCP memory lookup; `PHOENIX_MCP_ENABLED=false` returns `disabled` → the demo toggle. Load-bearing by design. (`current-state.md`.)
- **Impact framing (use factually):** ~99% of denied claims never appealed; target benchmark lift ~0.40 → ~0.75 on held-out cases. Mark any non-measured figure as a target. (`product-soul.md`.)
- **Tone for THIS page:** judge-facing — naming the stack (ADK, Gemini, Phoenix, judges, GEPA, held-out benchmark) is encouraged. The patient-voice rules in `design-brief.md` §4 apply to `/appeal`, **not** `/showcase`.
```
