# /showcase — Build Execution Plan (step-by-step, multi-agent handoff)

**Date:** 2026-06-09
**Companion to:** `docs/2026-06-08-showcase-cinematic-redesign-plan.md` (the design vision — read it first)
**Scope:** Build the visual + motion layer of `/showcase`. **Do NOT touch `/appeal`.**
**Execution model:** This plan is written for a *chain of agents*. Each agent picks up at the first unchecked step, completes it fully, verifies, commits, and updates the progress log (§Progress Log at the bottom).

---

## ⚠️ Rive policy (read before anything)

**Rive is the LAST, OPTIONAL phase (Phase 12). The site must look world-class WITHOUT it.**

- Do **not** search for open-source Rive projects. Do **not** try to build, author, or fix `.riv` files. Do **not** spend tokens on Rive until Phase 12, and only if explicitly told to proceed.
- Every animated element that *could* be Rive is built first as a **non-Rive fallback** (CSS / SVG / framer-motion). The fallback is the real product. Phase 12 is a drop-in swap behind a single boundary component (`RiveOrFallback`), nothing more.
- If Phase 12 never happens, the site is still finished and beautiful. Treat Phases 0–11 as the complete deliverable.

---

## How to use this plan (every agent reads this)

1. **Orient:** read the design doc (`...2026-06-08...`) and §0 of *this* doc.
2. **Find your start:** go to the Progress Log; start at the first `[ ]` step.
3. **One step = one focused unit.** Do the whole step. Don't skip ahead, don't bundle.
4. **Respect the guardrails** in each step (especially the data-layer preservation rules).
5. **Verify** using the step's acceptance criteria *before* claiming done.
6. **Commit** with the step's suggested message (only commit when the user has authorized commits; otherwise leave changes staged and note it).
7. **Update the Progress Log:** check the box, add one line on what you did / anything the next agent must know.
8. **Hand off cleanly:** leave `pnpm tsc && pnpm lint && pnpm test && pnpm build` green. Never hand off a red build.

**Global verification gate (run at the end of every phase):**
```bash
cd frontend
pnpm tsc --noEmit
pnpm lint
pnpm test
pnpm build
```
All four must pass. The build prerenders `/`, `/appeal`, `/showcase` — confirm all three still render.

---

## 0. Ground rules (apply to every step)

### 0.1 Data layer — preserve EXACTLY (non-negotiable)
In `frontend/src/app/showcase/page.tsx`, these must keep identical behavior; only their *presentation* changes:
- The four `useEffect`s: initial load (`listCases`/`getShowcaseManifest`/`getRollbackTarget`), case-select (`getShowcase(sel)`), the **10s `runSession` polling** with terminal-status guard, and the rollback-refresh effect.
- Handlers (unchanged names, signatures, call order): `startQuick→startQuickRun`, `startSerious→startSeriousRun`, `cancelCurrentRun→cancelRun`, `approveCurrentRun→approveRun`, `rejectCurrentRun→rejectRun`, `rollbackLatestRun→rollbackRun`.
- `seriousUnlocked` gate; all terminal statuses (`successful|failed|cancelled|rejected|needs_approval|rolled_back`).
- The data-source seam (`ds.*`, `getRunSession`, etc.). **Do not refactor fetching. Do not change polling cadence.**

**The pattern:** state and effects stay in `page.tsx` (the container). All new Act components are **presentational** — they receive data + handler callbacks as props.

### 0.2 Removals
- Remove the case-pill row (`<CasePicker>` usage at `page.tsx:156`). **Keep `sel`/`setSel`/`bundle`** — re-home case switching into the new `CaseCycler` (Phase 6). Do not delete `CasePicker.tsx` yet (delete in Phase 6 once `CaseCycler` replaces it and nothing else imports it).

### 0.3 Scope fences
- `/appeal` and `/` are untouched. Shared components used by `/appeal` must not regress — if you must change a shared component, branch it (`components/showcase/...`) instead of editing the shared one.
- The dark theme is **scoped** (`[data-theme="showcase-dark"]` on the showcase root) and must not leak into the light theme.

### 0.4 Copy & tone
- Use the copy from the design doc §6. This is a **judge/demo** surface — naming the stack (ADK, Gemini, Phoenix, judges, GEPA, held-out benchmark) is allowed and encouraged. The patient-voice rules in `design-brief.md` §4 apply to `/appeal`, not here.

### 0.5 Motion law
- One easing family (`EASE_OUT_EXPO`). One accent. Reduced-motion always degrades to a clean end-state (information never depends on motion). Max one Tier-3 moment on screen at a time.

---

## PHASE 0 — Setup, safety net, scaffolding

### Step 0.1 — Branch + dependencies
- **Goal:** isolated workspace; required libs present.
- **Do:**
  - Create branch `feat/showcase-cinematic` off `main` (if commits are authorized; otherwise work in place and note it).
  - Install (these will run on the build machine): `pnpm add gsap @gsap/react`. `framer-motion` is already present (`^12.40.0`). **Do NOT install any Rive package yet** — that's Phase 12.
- **Verify:** `pnpm install` clean; `pnpm build` green (baseline).
- **Commit:** `chore(showcase): branch + add gsap for cinematic layer`
- **Handoff note:** record the exact installed gsap version.

### Step 0.2 — Capture a baseline
- **Goal:** know what "working" means before changing anything.
- **Do:** Run the app (`pnpm dev`) and the backend if available; on `/showcase`, exercise the flow you can (at minimum: page loads, case bundle renders, "Run quick check" fires a request). Note current behavior in the Progress Log. If a backend isn't available, note that fixtures/demo-mode drive the page and record which.
- **Verify:** you can describe, from observation, what each button does today.
- **No commit** (observation only).

### Step 0.3 — Scaffold the folder structure (empty stubs)
- **Goal:** create the file tree so later steps just fill files.
- **Do:** create these as minimal stubs (exporting a placeholder that renders `null` or a TODO), per the design doc §10.1:
  ```
  components/showcase/ShowcaseFilm.tsx
  components/showcase/acts/{ActHero,ActThesis,ActInstrument,ActBeforeAfter,ActIntelligence,ActImpact}.tsx
  components/showcase/console/{RunControlDock,RunStatusPanel,LearningMatrix,VerdictCell,StatusHUD}.tsx
  components/showcase/versus/{VersusPanel,DiffCard,CounterfactualCard,CaseCycler}.tsx   // VersusPanel/DiffCard/CounterfactualCard may start as moves of existing ones
  components/showcase/primitives/{GlassPanel,MonoLabel,Gauge,MetricCounter,AccentLine}.tsx
  components/showcase/fx/{RiveOrFallback,LivingGlyph,StatusOrb,MemoryToggle,IgniteButton,LiftGauge,PipelineIcon}.tsx
  lib/motion/{easings,useGsapContext}.ts
  styles/showcase.css
  ```
- **Verify:** `pnpm tsc` green with stubs.
- **Commit:** `chore(showcase): scaffold component tree`

---

## PHASE 1 — Design system foundation (no Act work yet)

### Step 1.1 — Dark token block
- **Goal:** the scoped dark palette from design doc §2.
- **Files:** `styles/showcase.css` (imported by the showcase layout/root).
- **Do:** define all `--sc-*` tokens (surfaces, text, accent, warn, deny, hairlines, radii, `--sc-beat: 1.4s`) under `[data-theme="showcase-dark"]`. Add the faint vertical bg gradient and the optional single radial key-light as utility classes. Apply `data-theme="showcase-dark"` to the showcase page root only.
- **Verify:** showcase page renders on dark bg; `/appeal` unchanged (open both). No global token overridden.
- **Commit:** `feat(showcase): scoped dark token system`

### Step 1.2 — Motion helpers
- **Files:** `lib/motion/easings.ts`, `lib/motion/useGsapContext.ts`.
- **Do:**
  - `easings.ts`: export `EASE_OUT_EXPO` (cubic-bezier `0.22,1,0.36,1`), `DUR` (`{instant:120,quick:240,base:400,emph:520}`), `BEAT` (1400), and shared framer `variants` (`sectionEnter`, `staggerChildren`, `statusMorph`, `dockState`).
  - `useGsapContext.ts`: a hook wrapping `gsap.context()` + `ScrollTrigger` registration with cleanup on unmount, and a `reducedMotion` guard (reads `prefers-reduced-motion`; when set, timelines jump to end state). Wrap the app region in framer `MotionConfig reducedMotion="user"`.
- **Verify:** import both in a throwaway spot; `pnpm tsc` green. Confirm GSAP `ScrollTrigger` registers once (no duplicate-registration warnings).
- **Commit:** `feat(showcase): shared motion (easings + gsap context + reduced-motion)`

### Step 1.3 — Primitives
- **Files:** `primitives/*`.
- **Do (each is reduced-motion aware, uses tokens only):**
  - `GlassPanel` — matte graphite glass (backdrop-blur, hairline, inner top-highlight); `elevated` and `active` variants (active = accent ring + raised luminosity).
  - `MonoLabel` — JetBrains Mono, uppercase, letter-spaced, `--sc-text-3`.
  - `Gauge` — horizontal composite-quality bar (0–1), eased fill, optional static threshold tick, accent fill + glow.
  - `MetricCounter` — eased count-up (framer `useMotionValue` + `animate`), supports `a → b` display, 1-frame accent flash on settle, instant under reduced-motion.
  - `AccentLine` — a hairline that can "draw" (scaleX/clip) on reveal.
- **Verify:** drop all five into a temporary `/showcase` sandbox block, confirm they render and animate; remove the sandbox before commit. `pnpm build` green.
- **Commit:** `feat(showcase): UI primitives (GlassPanel, Gauge, MetricCounter, MonoLabel, AccentLine)`

### Step 1.4 — The RiveOrFallback boundary + all fallback FX (this is what makes Rive optional)
- **Goal:** every "could-be-Rive" element exists now as a great non-Rive component. Phase 12 only swaps internals.
- **Files:** `fx/*`.
- **Do:**
  - `RiveOrFallback.tsx` — a tiny component: `props = { rive?: ReactNode, fallback: ReactNode, enabled?: boolean }`. Renders `fallback` unless `enabled && rive` provided. A single env/const flag `SHOWCASE_RIVE_ENABLED = false` (constant in this file) gates all Rive globally. **Default false.**
  - Build each FX element as a **fallback-only** component now (the `rive` slot stays empty until Phase 12):
    - `LivingGlyph` — **fallback:** an SVG/CSS "aegis eye/shield" with a slow breath (scale+opacity, ~4s), an `ignite` entrance (stroke-draw + fade), a `settled` brighter state, and ≤6px cursor parallax. Accept `state: 'idle'|'ignite'|'settled'` prop.
    - `StatusOrb` — **fallback:** a CSS/SVG orb whose color + pulse rate are driven by `status` prop (`idle|running|needs_approval|success|error`), mapping to accent/warn/deny.
    - `MemoryToggle` — **fallback:** an accessible CSS toggle (real `<button role="switch">`) with a weighty knob travel; emits `onChange(on:boolean)`.
    - `IgniteButton` — **fallback:** a button with a CSS accent sweep on press/hover; wraps children + `onClick`.
    - `LiftGauge` — **fallback:** an SVG radial/needle gauge that sweeps to a `value` (percent) with overshoot+settle (framer spring).
    - `PipelineIcon` — **fallback:** small tuned SVG marks with an `active` state (per design doc, avoid raw-Lucide tell).
  - Each FX component: token-only styling, reduced-motion aware, `aria` correct (esp. `MemoryToggle`, `IgniteButton`).
- **Verify:** temporary sandbox renders all FX in their states; toggle/button are keyboard-operable; reduced-motion shows static states. Remove sandbox. `pnpm build` green.
- **Commit:** `feat(showcase): non-Rive FX layer + RiveOrFallback boundary (Rive disabled)`
- **Handoff note:** **From here, the whole site is built against these fallbacks. Rive is purely additive in Phase 12.**

---

## PHASE 2 — Safe extraction: container + presentational split (LOGIC-PRESERVING)

> This is the riskiest phase. Goal: restructure `page.tsx` into a thin container + Act components **with zero behavior change**. Do this as a pure refactor, verify identical behavior, *then* restyle in later phases.

### Step 2.1 — Extract presentational pieces without changing logic
- **Files:** `app/showcase/page.tsx`, `acts/*`, `console/*`, `versus/*`.
- **Do:**
  - Keep ALL state, effects, and handlers in `page.tsx`. Move only JSX into `ShowcaseFilm` + Act components, passing everything down as props. Initial pass: components render the *same markup/classes as today* (literal move) — no visual change yet.
  - Render order via `ShowcaseFilm`: Hero → Thesis → Instrument → BeforeAfter → Intelligence → Impact. (Thesis/Hero/Impact are new placeholders showing minimal content for now; Instrument/BeforeAfter wrap the *existing* markup verbatim.)
  - Existing `RunStatusPanel`/`LearningMatrix`/`VersusPanel`/`DiffCard`/`CounterfactualCard` logic: move into the new files **unchanged** (copy the function bodies; keep the same props they implicitly used).
  - Remove `<CasePicker>` from render; temporarily render the existing selection some minimal way (even a plain `<select>`) so case-switching still works until Phase 6. Keep `sel`/`setSel`.
- **Verify (critical):**
  - Diff the network behavior against the Step 0.2 baseline: every button fires the same request; polling still every 10s; approve/reject/cancel/rollback still work; `seriousUnlocked` still gates serious.
  - `pnpm tsc && pnpm lint && pnpm test && pnpm build` green. The firewall test still passes.
  - Visually it can look unchanged/rough — that's expected. **Behavior must be identical.**
- **Commit:** `refactor(showcase): split container/presentational, logic preserved (no visual change)`
- **Handoff note:** explicitly confirm in the log that all six handlers + polling verified identical.

---

## PHASE 3 — Act III: the Live Instrument (do the functional core FIRST)

> Style the load-bearing dashboard before the decorative acts, so the demo's working heart is solid early.

### Step 3.1 — RunControlDock
- **Files:** `console/RunControlDock.tsx`.
- **Props:** `manifest, seriousUnlocked, rollbackTarget, startQuick, startSerious, rollbackLatestRun`.
- **Do:** two `GlassPanel` run cards (Quick check / Serious pass), serious disabled unless `seriousUnlocked`; conditional "Roll back latest update" when `rollbackTarget`. Use `IgniteButton`. The dock is the one element with a real drop-shadow; make it sticky while Act III is the focus (≥lg). Mono sub-labels from manifest (`{quick_train} TRAIN · {quick_holdout} HOLDOUT · SLICE {quick_slice}`).
- **Verify:** buttons fire real handlers; disabled state correct; sticky works ≥lg, off <lg. Build green.
- **Commit:** `feat(showcase): RunControlDock`

### Step 3.2 — RunStatusPanel (state machine visuals)
- **Files:** `console/RunStatusPanel.tsx`.
- **Props:** `session, runErr, onCancel, onApprove, onReject` (same as today).
- **Do:**
  - Mono session id; `current_stage` as a large serif heading that **morphs** on change via framer `AnimatePresence` (crossfade + 8px rise).
  - One-line plain caption per stage (map from `docs/demo-cheatsheet-pm.md` stage table: `measure_before`→"Measuring held-out cases with the current prompt — no learning yet.", `train_gepa`→"Drafting, judging, and running the optimizer on training cases.", `waiting_for_approval`→"Proposed changes ready — you decide whether to ship them.", `promote`→"Promoting the approved changes.", `measure_after`→"Re-measuring held-out cases with the promoted prompt.").
  - Eased mono progress fraction + thin `AccentLine` progress bar (`completed_cases/total_cases`).
  - Amber regression banner on `regression_detected` (use `--sc-warn`, slide in calmly) with `regression_summary`.
  - Error box on `diagnostics.last_error` (message + code).
  - `StatusOrb` driven by `session.status`. Approve/Reject buttons rise in with accent ring ONLY at `needs_approval`; Cancel while non-terminal.
  - **Standby (no session):** a calm skeleton console — dim matrix outline + pulsing "Begin a live run" affordance + `AWAITING SESSION` mono hint. **Never a bare spinner.**
- **Verify:** drive through statuses (use demo fixtures or a mocked session) — idle→running→needs_approval→success and a failure/regression case all render correctly and morph without layout jump. Reduced-motion → instant. Build green.
- **Commit:** `feat(showcase): RunStatusPanel state-machine visuals`

### Step 3.3 — VerdictCell + LearningMatrix
- **Files:** `console/VerdictCell.tsx`, `console/LearningMatrix.tsx`.
- **Props (matrix):** `manifest, session` (same data as today).
- **Do:**
  - `VerdictCell` — luminous tile, `verdict: 'APPROVE'|'DENY'` → `--sc-accent`/`--sc-deny`, crisp border + micro inner shadow; fades+scales in on mount; hover shows styled tooltip (`{caseId}: {verdict}` — preserve existing info). Color is not the only signal (tooltip/label backup).
  - `LearningMatrix` — the 6-box matrix (Demo/Serious × Pre/Training[before·after]/Post). Cells populate as poll data arrives (stagger). Demo/Serious columns act as tabs with a sliding accent underline (framer `layoutId`); inactive dimmed. Preserve internal scroll for large cohorts.
  - Do **not** build the red→green *cascade* animation here yet beyond per-cell enter — the choreographed flip belongs to Act IV's money shot and the matrix's own "after" column reveal; keep matrix cells calm and data-accurate.
- **Verify:** with fixture/live data, cells reflect verdicts correctly; columns switch; large cohort scrolls; reduced-motion → instant fill. Build green.
- **Commit:** `feat(showcase): luminous LearningMatrix + VerdictCell`

### Step 3.4 — Assemble ActInstrument + StatusHUD
- **Files:** `acts/ActInstrument.tsx`, `console/StatusHUD.tsx`.
- **Do:** compose dock + status panel + matrix into the console layout (design doc §6 Act III). Add sticky `StatusHUD` (top-right, mono `STATUS · STAGE · N/M`) visible during a run. Running/standby states must read as cinematic suspense (streaming mono telemetry lines + StatusOrb + trickling cells).
- **Verify:** full Act III looks like a control room; all interactions live; HUD tracks state; polling untouched. Run the full global gate. 
- **Commit:** `feat(showcase): assemble ActInstrument + StatusHUD`

---

## PHASE 4 — Act I: Hero
- **Files:** `acts/ActHero.tsx`.
- **Do:** implement design doc §11.1 / §6 Act I. Full-viewport asymmetric layout; mono eyebrow; serif headline "Watch a system teach itself."; Inter subhead; `IgniteButton` CTA "Begin a live run" → smooth-scroll to Act III; `LivingGlyph` (fallback) offset right with cursor parallax; mono telemetry strip. GSAP ignition timeline on mount (glyph ignite → headline words blur-in stagger 70ms → telemetry starts → glyph settles). Reduced-motion → end state. Mobile single-column, no parallax.
- **Verify:** loads as a cinematic hook; CTA scrolls correctly; 60fps on ignition; reduced-motion clean. Build green.
- **Commit:** `feat(showcase): ActHero with GSAP ignition + living glyph (fallback)`

## PHASE 5 — Act II: Thesis
- **Files:** `acts/ActThesis.tsx`.
- **Do:** design doc §11.2 / §6 Act II. Short scroll-pinned editorial beat (pin ≥lg via `ScrollTrigger.matchMedia`); serif statement + the static-node-vs-Aegis-node contrast (the Aegis node ignites; `AccentLine` writes "learns"); mono foreshadow caption about the memory-off test. 90% negative space. Reduced-motion → static end. 
- **Verify:** pin engages/releases cleanly ≥lg, disabled <lg; no scroll jank; build green.
- **Commit:** `feat(showcase): ActThesis pinned beat`

## PHASE 6 — Act IV: Before/After (the money shot) + CaseCycler
- **Files:** `versus/VersusPanel.tsx`, `versus/DiffCard.tsx`, `versus/CaseCycler.tsx`, `acts/ActBeforeAfter.tsx`. Then delete `components/showcase/CasePicker.tsx` if unused.
- **Do:**
  - `CaseCycler` — **replaces the pills**; featured-case serif label `{insurer} · {denial_type}`, quiet mono prev/next controls (optional dot filmstrip) calling the existing `setSel`. Keep `getShowcase(sel)` flow intact.
  - `VersusPanel` — true 50/50: left v1 (lower `Gauge`, DENY lamp, excerpt), right v3 (higher `Gauge`, APPROVE lamp, excerpt); centered `LiftGauge` (fallback) → `+{lift_relative_pct}%`. Preserve the illustrative-vs-measured caveat note + `phoenix_url` "Open the underlying trace" link (styled as mono "inspect").
  - `DiffCard` — "What changed, and why." bullets stagger in.
  - **Money-shot timeline (GSAP ScrollTrigger `onEnter`, not scrub):** left gauge fills → right gauge overtakes → verdict lamp flips DENY→APPROVE with accent bloom → `LiftGauge` sweeps → diff bullets stagger. Tune to `--sc-beat`. Reduced-motion → instant end state.
- **Verify:** cycling cases swaps bundles via `setSel` (confirm `getShowcase` fires); the flip plays as one clean shot at demo pace; measured/illustrative caveat correct; trace link works. Build green; confirm nothing else imported `CasePicker` before deleting.
- **Commit:** `feat(showcase): ActBeforeAfter money-shot + CaseCycler (remove pills)`

## PHASE 7 — Act V: Intelligence (architecture + counterfactual)
- **Files:** `acts/ActIntelligence.tsx`, `versus/CounterfactualCard.tsx`, uses `fx/PipelineIcon`, `fx/MemoryToggle`.
- **Do:** design doc §11.5 / §6 Act V.
  - **V-a:** horizontal self-drawing pipeline `Draft → Judge panel → Phoenix memory → GEPA → Human approval → Promote`; nodes = `GlassPanel` + `PipelineIcon`; connectors = SVG path drawing in on scroll (GSAP path-length). Callouts: Judge — "Seven-dimension panel: two hard safety gates + five weighted scores. Six run as ADK agents."; Phoenix — "It reads its own past traces before drafting."
  - **V-b:** restyle `CounterfactualCard` (`on_composite`/`off_composite`) as two `Gauge`s controlled by `MemoryToggle` (fallback). OFF → Tier-3 decay (accent drains, desaturate via CSS filter, bar retreats to `off_composite`). Keep honest footnote.
  - Never run V-a draw + V-b decay simultaneously.
- **Verify:** pipeline draws on scroll; toggle is keyboard-accessible and the decay reads as meaningful; reduced-motion → instant. Build green.
- **Commit:** `feat(showcase): ActIntelligence (self-drawing loop + memory counterfactual)`

## PHASE 8 — Act VI: Impact / Close
- **Files:** `acts/ActImpact.tsx`.
- **Do:** design doc §11.6 / §6 Act VI. Spare layout; serif statement; three mono `MetricCounter`s count up in sequence on enter (only doc-backed numbers; mark targets honestly — e.g. `BENCHMARK QUALITY 0.40 → 0.75`, `JUDGE DIMENSIONS 7`, `HUMAN-APPROVED ALWAYS`); `LivingGlyph` returns brighter/"settled" and exhales once; finale GSAP timeline (counters → glyph brighten → footer `AccentLine` draw → stillness). Mono end-card `AEGIS · built on Google ADK + Gemini · observability by Arize Phoenix`. Optional "Replay the run" control. Reduced-motion → final values instantly.
- **Verify:** ends on a clean still frame; counters accurate; build green.
- **Commit:** `feat(showcase): ActImpact finale`

---

## PHASE 9 — Cross-cutting choreography & global polish

### Step 9.1 — Scroll spine + section reveals
- **Do:** in `ShowcaseFilm`, set up the single `gsap.context()` covering all Acts; add the top scroll-progress `AccentLine` tracking the six Acts; ensure each Act has the Tier-2 enter (blur-in + 12–16px rise + stagger). Verify pins (Act II, Act III) coexist without ScrollTrigger conflicts; all triggers `kill()` on unmount.
- **Verify:** scrubbing the whole page top→bottom is smooth; no orphaned triggers on route change; 60fps. Build green.
- **Commit:** `feat(showcase): global scroll spine + section reveals`

### Step 9.2 — Responsive pass
- **Do:** implement breakpoints (design doc §10.4): <640 single-column, pins off, Tier-3→fades, matrix horizontal scroll; 768 two-up where natural; 1024+ full cinematic with pins; 1280+ generous gutters. No horizontal overflow anywhere.
- **Verify:** test at 375 / 768 / 1024 / 1280 / 1440 widths. Build green.
- **Commit:** `feat(showcase): responsive pass`

### Step 9.3 — Reduced-motion + a11y sweep
- **Do:** confirm every Tier-3 beat degrades to end-state under `prefers-reduced-motion`; keyboard nav + visible focus on all controls; `MemoryToggle`/tabs/cycler have correct roles/labels; verdict color has non-color backup; contrast AA on dark.
- **Verify:** OS reduced-motion on → page fully usable, all info present, no motion-dependent meaning. Keyboard-only walkthrough completes the demo flow. Build green.
- **Commit:** `feat(showcase): reduced-motion + a11y sweep`

### Step 9.4 — Performance pass
- **Do:** lazy-mount heavy FX/GSAP per-Act via IntersectionObserver; unmount off-screen; cap concurrent backdrop-blur panels; ensure only transform/opacity/filter animate; preload hero assets + subset fonts.
- **Verify:** record a 60s screen capture scrolling the full page + running a quick check; confirm steady 60fps and no layout-shift jank in the capture (not just the live monitor). Build green.
- **Commit:** `perf(showcase): lazy-mount FX + compositor-only animations`

---

## PHASE 10 — Demo-resilience & recording readiness
- **Do:**
  - Make the running/standby states inherently cinematic during slow polls (streaming telemetry, breathing orb, trickling cells) — verify there's never visible "dead air."
  - Ensure a clean "hold" frame per Act for narration; finale ends on stillness.
  - Wire/confirm a "Replay the run" path for second takes; document the day-zero reset (`backend/scripts/reset_to_day_zero.py`) in the Progress Log for the presenter.
  - Confirm `StatusHUD` keeps state legible when matrix is off-screen.
- **Verify:** do a full dry-run recording following demo-cheatsheet §"Happy path" (start quick → pre/training fill → needs_approval beat → approve → post fill → before/after → memory-off). It should look finished with zero post-editing.
- **Commit:** `feat(showcase): demo-resilience + recording polish`

## PHASE 11 — Final QA gate (the design doc §12 checklist)
- **Do:** run the entire §12 checklist from the design doc (Visual / Motion / Recording / Responsiveness / Demo-pacing / Data-layer integrity). Fix anything that fails. Re-confirm the data-layer integrity items: all six handlers + polling identical to baseline; pills gone but `sel`/bundle preserved; `/appeal` untouched; dark tokens scoped.
- **Verify:** every checkbox in design-doc §12 passes; global gate green.
- **Commit:** `chore(showcase): final QA pass`
- **This is the complete, shippable product. Rive below is optional upside only.**

---

## PHASE 12 — Rive (OPTIONAL, LAST, only on explicit go)

> Do **not** start this unless the user explicitly says to, and supplies/approves `.riv` assets. The site is already done without it. **No searching for Rive open-source. No authoring/fixing `.riv`.** This phase is a pure swap behind `RiveOrFallback`.

### Step 12.1 — Enable the boundary
- **Do:** `pnpm add @rive-app/react-canvas`; flip `SHOWCASE_RIVE_ENABLED` handling so Rive renders only where a `.riv` asset is actually provided and loads successfully — **fallback remains the default and the automatic error path.** If a `.riv` fails to load, render the fallback (no broken UI, ever).
- **Verify:** with no assets present, page is byte-for-byte the Phase 11 experience. Build green.

### Step 12.2 — Swap, one element at a time (priority order)
- **Order (stop anytime — each is independent):** 1) `LivingGlyph`, 2) `StatusOrb`, 3) `MemoryToggle`, then optional 4) `IgniteButton`, 5) `LiftGauge`, 6) `PipelineIcon`.
- **Do per element:** pass the `.riv`-backed node into the `rive` slot of `RiveOrFallback`; map the same props/state inputs the fallback used (e.g. glyph `state`, orb `status`, toggle `on`). Keep the fallback intact as the failure path.
- **Verify per element:** Rive version matches the fallback's behavior/states; reduced-motion still honored; disabling the flag instantly restores the fallback; build green; 60fps maintained.
- **Commit (per element):** `feat(showcase): rive upgrade — <element> (fallback preserved)`

---

## Risks & how this plan defends against them
- **Breaking the live demo logic** → Phase 2 is a pure logic-preserving refactor verified against a baseline before any restyle; data-layer integrity is re-checked in Phase 11.
- **Rive being unavailable/paid** → Phases 0–11 never depend on it; `RiveOrFallback` makes it a no-op by default; fallbacks are the real components.
- **Slow backend making the demo look laggy** → Phase 3 + Phase 10 design the waiting states as suspense; HUD keeps state on-camera.
- **Over-busy / "too much motion"** → design doc §12 "what to simplify" is the escape hatch; one-Tier-3-at-a-time rule enforced in Phase 9.
- **Multi-agent drift** → every step has explicit files, guardrails, acceptance criteria, and a commit; the Progress Log carries context between agents.

---

## Progress Log (each agent appends one line per completed step)

> Format: `- [x] Step N.M — <what was done> — <anything the next agent must know>`

- [ ] 0.1 Branch + deps
- [ ] 0.2 Baseline captured
- [ ] 0.3 Scaffold tree
- [ ] 1.1 Dark tokens
- [ ] 1.2 Motion helpers
- [ ] 1.3 Primitives
- [ ] 1.4 RiveOrFallback + fallback FX
- [ ] 2.1 Container/presentational split (logic preserved) — MUST confirm handlers+polling identical
- [ ] 3.1 RunControlDock
- [ ] 3.2 RunStatusPanel
- [ ] 3.3 VerdictCell + LearningMatrix
- [ ] 3.4 ActInstrument + StatusHUD
- [ ] 4 ActHero
- [ ] 5 ActThesis
- [ ] 6 ActBeforeAfter + CaseCycler (pills removed)
- [ ] 7 ActIntelligence
- [ ] 8 ActImpact
- [ ] 9.1 Scroll spine
- [ ] 9.2 Responsive
- [ ] 9.3 Reduced-motion + a11y
- [ ] 9.4 Performance
- [ ] 10 Demo-resilience
- [ ] 11 Final QA — SHIPPABLE HERE
- [ ] 12 Rive (optional, only on explicit go)
```
