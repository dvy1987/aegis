# Aegis Frontend — Design Spec

**Date:** 2026-06-01
**Author:** Session 26 (Claude) + PM
**Status:** Draft for PM review
**Supersedes:** the single-page landing scaffold (kept and refined, not discarded)

---

## 0. Summary

The frontend today is one well-made landing page with a locked, excellent design
system (`.design/aegis/`, `frontend/src/styles/tokens.css`). What's missing is the
**product** behind it. This spec defines a reimagined frontend with **two surfaces in
one design language**:

- **`/` + `/appeal` — The Product.** The calm consumer flow a stressed person uses to
  turn a denial letter into a drafted appeal. Never names the AI.
- **`/showcase` — "How Aegis learns".** The judge-facing proof that the agent improves
  from its own observability (the Arize thesis). Names the mechanism openly.

Both read data through **one `DataSource` abstraction**: a bundled **demo mode**
(default — fully clickable offline from real recorded artifacts) and a **live mode**
(`/v1/appeal`) flipped by a single env flag.

### Locked decisions (PM, 2026-06-01)

1. **Scope:** build **both** surfaces.
2. **Data:** demo + live behind one `DataSource` layer; demo is default.
3. **Intake:** **paste with light guided assist** (paste denial letter / pick sample
   case + optional clinical-context field). Not a multi-step wizard.
4. **Demo fixtures:** use **real recorded outputs where they exist**
   (`eval/efficacy_runs/*`, `eval/cases/*`); author faithful, clearly-marked stand-in
   fixtures for any test case lacking a recorded run, in the exact `AppealResponse`
   shape. Every one of the 10 test cases must be selectable and look complete, because
   **the PM will pick one or more test cases live for the demo.**
5. **Showcase name:** **"How Aegis learns"** at route `/showcase`.

---

## 1. Why two surfaces (the central architectural decision)

The product serves two audiences whose needs conflict:

| | `/` + `/appeal` — The Product | `/showcase` — How Aegis learns |
|---|---|---|
| **For** | A stressed person at 11pm | Hackathon judges |
| **Job (function)** | Reduce anxiety; produce a readable draft | Prove Phoenix is structurally load-bearing |
| **Names the AI / Phoenix / Gemini?** | **Never** (design-brief §8 veto) | **Yes** — that is the entire point |
| **Tone** | Calm, dignified, plain-language | Confident, evidentiary, still calm |

The design brief forbids exposing the AI/learning-loop inside the consumer flow; the
Arize judging thesis *requires* showing exactly that. A single blended surface would
violate the brief on one side and starve the thesis on the other. So: two surfaces,
shared tokens/type/motion/restraint, different purpose. This is "form follows function"
applied honestly.

Both surfaces inherit the existing archetype (`.design/aegis/ARCHETYPE.md`): premium
consumer-health, Source Serif display + Inter body, warm-parchment + single sage accent,
Calm motion (240–520ms), hairlines over card chrome, type-only restraint. No new visual
language is invented; the gap is product, not aesthetics.

---

## 2. Surface A — the consumer flow

A single forward motion, not a stepper. Implemented as a client-side state machine
under `/appeal` (landing `/` keeps its hero and links into it). The states mirror the
design-brief emotional arc (§5) and map to the real backend contract.

### 2.1 States

```
Land  (existing hero — kept, lightly refined; "Start a draft" → /appeal)
  │
  ▼
Intake      Paste the denial letter, or pick a sample case. Optional field:
            "anything your doctor said or wrote." Light helper text, not a
            form march. → assembles { denial_text, clinical_context, case_id }.
  │  submit
  ▼
Working     Text-progress, no spinner: "Reading your denial…" →
            "Drafting your appeal…" → "Almost done." (honors reduced-motion)
  ▼
Mirror      Plain-English "here's what we heard": insurer, what was denied,
(Understand) why they said no, the deadline (factual), the strongest angle.
            Built from parsed_case + appeal_strategy. Reduces the swirl
            before the letter appears.
  ▼
Draft       The appeal letter, readable and editable inline. Quiet side rail:
(Produced)   citations used · evidence still needed · risk flags · the required
            safety disclaimer (verbatim, PRD §21). The simulator verdict is
            shown HONESTLY as a transparent rule-based proxy — never "you'll win."
  ▼
Decide      Copy / download (.txt, .md). "A person should read this before you
(In control) file." Deadline restated factually. No filing. No urgency. No
            celebration on success — acknowledgement only (brief §4).
```

### 2.2 Data mapping (consumer flow ⇄ backend)

Request (`POST /v1/appeal`, `AppealRequest`): `{ denial_text, clinical_context, case_id }`.

Response (`AppealResponse`): `{ run_id, appeal_letter, outcome, risk_flags, trace_metadata }`,
where `outcome` is a `SimulatorResult` (`verdict` APPROVE/DENY, `score`, `threshold`,
`feature_scores[]`, `gaps[]`, `critique`).

- **Mirror** uses `trace_metadata` (insurer, denial_type) + a parsed summary. *Note:*
  the live `/v1/appeal` response does not currently return the full `parsed_case` or
  `appeal_strategy`; the Mirror step renders from what's available and the demo fixtures
  include a richer `mirror` block. **Interface gap flagged in §6.**
- **Draft** renders `appeal_letter` (editable) + `risk_flags` + safety disclaimer. The
  side-rail "citations used / evidence needed" come from the demo fixture's
  `appeal_package_draft`; live mode shows what the API returns and hides what it doesn't.
- **Verdict** renders `outcome.verdict` + `outcome.score` vs `outcome.threshold` +
  `outcome.gaps` as plain-English "what would make this stronger," framed as a proxy.

### 2.3 Copy & tone (non-negotiable, design-brief §4)

No "AI", "Phoenix", "Gemini", "ADK" anywhere on `/` or `/appeal`. No exclamation marks.
No emoji beyond a status dot. Verb-first, second person, plain English. Honest about
odds. No manufactured urgency. Safety disclaimer present on the Draft and Decide states.

---

## 3. Surface B — `/showcase` ("How Aegis learns")

The judge-facing proof, in the same calm language (deliberately not a busy dashboard).

### 3.1 Sections (top to bottom)

1. **Thesis** — one serif line: *"This agent improves from its own observability."*
2. **Case picker** — all 10 test/holdout cases, labeled `insurer · denial_type`
   (e.g. "Cigna · medical necessity"). The selected case drives every section below.
   **This is the surface the PM demos from.**
3. **v1 vs v3, side by side** — the two drafts, two composite scores, two simulator
   verdicts, the measured **held-out lift** (e.g. +20.5% on `appeal_vector_capture`,
   from `eval/efficacy_runs/2026-05-31/result.json`), shown as evidence not a brag.
4. **What changed & why** — the laundered reflection/diff: what the agent learned about
   *this* slice. No answer-key leakage (firewall respected — fixtures are already
   laundered).
5. **The counterfactual (mic-drop)** — "Phoenix off → quality collapses," using the
   recorded `counterfactual` numbers (`on_composite` vs `off_composite`).
6. **Link to Phoenix** — the real trace link where creds allow; otherwise a labeled
   placeholder.

### 3.2 Data sources (all recorded artifacts — truthful, offline-safe)

- `eval/efficacy_runs/2026-05-31/result.json` (Run #1: v1 0.73 → v2 0.88, +20.5%)
- `eval/efficacy_runs/2026-06-01-round2/result.json` (offline-ceiling finding)
- `eval/efficacy_runs/2026-06-01-metaprompt-ab/result.json` (A/B finding)
- Recorded counterfactual output (on vs off composite)
- Per-case drafts/scores from `eval/cases/*` + efficacy run dirs

The showcase reads these as bundled JSON; nothing is fabricated. Where a number is a
design target rather than a measured result, it is labeled as such.

---

## 4. Architecture

```
frontend/src/
  app/
    page.tsx              landing (kept; "Start a draft" → /appeal; adds /showcase nav link)
    appeal/page.tsx       consumer flow — client state machine intake→working→mirror→draft→decide
    showcase/page.tsx     "How Aegis learns"
    layout.tsx            (exists) fonts + globals
  lib/
    data/
      source.ts           DataSource interface (single seam)
      demo.ts             reads bundled fixtures (default, offline)
      live.ts             calls /v1/appeal (NEXT_PUBLIC_AEGIS_MODE=live)
      index.ts            picks impl from env; demo is default
    fixtures/
      cases/              one JSON per test case (the 10), AppealResponse-shaped + mirror block
      runs/               copies/symlinks of the efficacy + counterfactual artifacts
    types.ts              TS mirrors of AppealResponse / SimulatorResult / ParsedCase / cases
  components/
    flow/                 IntakePanel, WorkingProgress, MirrorCard, DraftEditor, DecideBar
    showcase/             CasePicker, VersusPanel, ScoreMeter, DiffCard, CounterfactualCard
    ui/                   Button (exists), Wordmark (exists), Disclaimer, Field, TextArea,
                          ProgressHairline, StatusDot, Callout
  styles/                 tokens.css (exists), globals.css (exists)
  icons/                  (exists) tuned Lucide wrapper + bespoke set
```

### 4.1 The DataSource seam

```ts
interface DataSource {
  listCases(): Promise<CaseSummary[]>;            // the test cases for both pickers
  draftAppeal(req: AppealRequest): Promise<AppealResponse>;   // consumer flow
  getShowcase(caseId: string): Promise<ShowcaseBundle>;       // v1/v3 + diff + counterfactual
}
```

- `demo.ts` resolves from `lib/fixtures/*` — works with zero backend, zero creds.
- `live.ts` calls the FastAPI backend for `draftAppeal`; `listCases`/`getShowcase` read
  the same bundled artifacts (showcase is always evidence, never live-generated).
- `index.ts` selects by `NEXT_PUBLIC_AEGIS_MODE` (`demo` default, `live` opt-in). No
  component imports a concrete impl — they take the interface. Demo↔live are drop-in.

### 4.2 Type fidelity (no false-green drift)

`lib/types.ts` mirrors `backend/app/aegis_v1/schemas.py` (`AppealResponse`,
`SimulatorResult`, `FeatureScore`, `ParsedCase`, `TraceMetadata`) field-for-field.
Demo fixtures validate against these types at author time so a later live wiring can't
silently diverge. Where the live API omits a field the UI wants (see §6), the type marks
it optional and the UI degrades gracefully.

### 4.3 Quality bar (inherited, enforced)

- shadcn-style primitives **hand-tuned to tokens** — never dropped in raw.
- Tailwind default palette names (`slate`/`zinc`/`blue`/`purple`) forbidden in source.
- Calm motion; `prefers-reduced-motion: reduce` honored everywhere.
- WCAG 2.2 AA contrast on every token pair used; full keyboard nav; visible focus.
- Mobile-first; reading column ≤ 64ch; 56px tap targets on fields.
- No exclamation marks; no AI/Phoenix/Gemini words on `/` or `/appeal`.

---

## 5. Out of scope (YAGNI)

- Accounts / auth / multi-tenant.
- Persistence beyond the device (no DB; draft lives in client state only).
- PDF upload/parsing (paste only for v1 — backend takes text).
- Analytics / tracking.
- Learning-proposal *approval* UI (promotion is a credentialed backend action; the
  showcase displays the recorded result, it does not drive promotion).
- Inventing new visual tokens — the design system is locked.

---

## 6. Known interface gaps (flagged, not silently worked around)

1. **Mirror data:** `/v1/appeal` returns `appeal_letter` + `outcome` + `risk_flags` +
   `trace_metadata`, but **not** the full `parsed_case` or `appeal_strategy` the Mirror
   step wants. Options for the plan: (a) demo fixtures carry a richer `mirror` block and
   live mode renders a lighter Mirror from `trace_metadata`; or (b) extend
   `AppealResponse` to include `parsed_case` + `appeal_strategy`. **Recommend (a) for
   this build, note (b) as a backend follow-up** so we don't block the frontend on a
   backend change.
2. **Showcase per-case coverage:** not all 10 test cases have a recorded v1/v3 efficacy
   run. Plan must author faithful, clearly-labeled stand-in bundles for the uncovered
   cases so any pick looks complete, while the cases that *do* have real runs are marked
   as measured.
3. **Live `listCases`:** there's no backend endpoint listing benchmark cases; both modes
   read the bundled case list. Acceptable — the case set is static.

---

## 7. Build order (for the implementation plan)

1. Tokens/Tailwind wiring sanity + `ui/` primitives (Field, TextArea, Disclaimer,
   ProgressHairline, StatusDot, Callout) tuned to tokens.
2. `lib/types.ts` + `DataSource` seam + `demo.ts` + fixtures for the 10 cases.
3. Consumer flow `/appeal` state machine + `flow/` components.
4. `/showcase` + `showcase/` components reading recorded artifacts.
5. Landing `/` refinement + cross-links + nav.
6. `live.ts` wiring (behind env flag) + graceful degradation for §6 gaps.
7. a11y + reduced-motion + responsive pass; `next build`/`lint` green.

Each step is independently verifiable offline (demo mode), so the whole build is
reviewable without creds.
