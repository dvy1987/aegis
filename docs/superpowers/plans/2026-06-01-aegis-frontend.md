# Aegis Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the two-surface Aegis frontend — a calm consumer appeal-drafting flow (`/appeal`) and a judge-facing self-improvement showcase (`/showcase`) — behind one `DataSource` seam (demo default, live `/v1/appeal` via env flag), fully clickable offline.

**Architecture:** Next.js 16 App Router + Tailwind v4 (existing locked design tokens). A single `DataSource` interface has two implementations: `demo` (bundled fixtures from real recorded artifacts) and `live` (FastAPI). The consumer flow is a client-side state machine; the showcase renders recorded efficacy artifacts. The teacher answer key (`synthetic_provenance`) is never bundled into consumer fixtures — a firewall test enforces this.

**Tech Stack:** Next.js 16.2.6, React 19, TypeScript (strict), Tailwind v4, framer-motion, Zod (new — runtime fixture validation), Vitest (new — logic unit tests).

**Spec:** `docs/superpowers/specs/2026-06-01-aegis-frontend-design.md`

---

## Conventions (read once)

- Work from `frontend/`. Package manager: **pnpm** (lockfile present).
- Path alias: `@/*` → `frontend/src/*`.
- `cn(...)` helper at `@/lib/cn`. `Button` at `@/components/Button` (variants: primary|secondary|ghost). Tuned icons from `@/icons`.
- **Tokens only** — never raw Tailwind palette names (`slate`/`zinc`/`blue`/`purple`). Classes like `bg-surface-primary`, `text-text-secondary`, `text-display-lg`, `font-display`, `font-body` resolve via `@theme inline` in `globals.css`.
- **Copy rules (hard):** no exclamation marks; no "AI"/"Phoenix"/"Gemini"/"ADK" on `/` or `/appeal`; second person; verb-first; honest about odds; no manufactured urgency. (`/showcase` MAY name the mechanism.)
- **Motion:** Calm easing `cubic-bezier(0.2,0.8,0.2,1)`, 240–520ms; honor `prefers-reduced-motion`.
- Commit after each task with trailer:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- Commits run from repo root (`cd /bv3/aimbot/divya/buildmind-misc/aegis`); pnpm/test commands run from `frontend/`.

---

## File Structure

```
frontend/
  vitest.config.ts                      (new) vitest + jsdom
  src/
    lib/
      types.ts                          (new) TS mirrors of backend schemas + view types
      schema.ts                         (new) Zod schemas + parsers (runtime validation)
      data/
        source.ts                       (new) DataSource interface
        demo.ts                         (new) fixture-backed impl (default)
        live.ts                         (new) /v1/appeal impl
        index.ts                        (new) env-based selector
      fixtures/
        cases.ts                        (new) the 10 test-case summaries (student-safe)
        appeals/<case_id>.json          (new x10) AppealResponse-shaped + mirror block
        showcase/<case_id>.json         (new x10) v1/v3 + diff + counterfactual bundle
        showcase/_runs.ts               (new) imports recorded efficacy result.json
      flow/reducer.ts                   (new) consumer-flow state machine (pure)
    components/
      ui/{Field,TextArea,Disclaimer,ProgressHairline,StatusDot,Callout,ScoreMeter}.tsx  (new)
      flow/{IntakePanel,WorkingProgress,MirrorCard,DraftEditor,DecideBar}.tsx           (new)
      showcase/{CasePicker,VersusPanel,DiffCard,CounterfactualCard}.tsx                 (new)
      Nav.tsx                           (new) shared top nav
    app/
      page.tsx                          (modify) landing: link to /appeal + /showcase
      appeal/page.tsx                   (new) consumer flow host
      showcase/page.tsx                 (new) "How Aegis learns"
    __tests__/
      schema.test.ts                    (new)
      demo.test.ts                      (new)
      firewall.test.ts                  (new) no answer-key in consumer fixtures
      reducer.test.ts                   (new)
  tests-data/recorded/                  (new) copied result.json artifacts (build-time import)
```

---

## Phase 0 — Tooling

### Task 0: Add Vitest + Zod

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/vitest.config.ts`

- [ ] **Step 1: Install deps**

Run (from `frontend/`):
```bash
pnpm add zod && pnpm add -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom
```

- [ ] **Step 2: Add test script** — in `frontend/package.json` `"scripts"`, add:
```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 3: Create `frontend/vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  test: { environment: "jsdom", globals: true },
});
```

- [ ] **Step 4: Verify** — Run: `pnpm test`. Expected: "No test files found" (exit 0) or passes; no config error.

- [ ] **Step 5: Commit**
```bash
cd /bv3/aimbot/divya/buildmind-misc/aegis && git add frontend/package.json frontend/pnpm-lock.yaml frontend/vitest.config.ts && git commit -m "chore(frontend): add vitest + zod for logic tests and fixture validation

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Phase 1 — Types, validation, DataSource seam, fixtures

### Task 1: Types mirroring the backend contract

**Files:**
- Create: `frontend/src/lib/types.ts`

Mirrors `backend/app/aegis_v1/schemas.py` (`AppealResponse`, `SimulatorResult`, `FeatureScore`, `TraceMetadata`) + view-only types. `parsed_case`/`appeal_strategy` are optional (live API omits them — spec §6).

- [ ] **Step 1: Create `frontend/src/lib/types.ts`**

```ts
// Mirrors backend/app/aegis_v1/schemas.py — keep field names in sync.
export type Verdict = "APPROVE" | "DENY";
export type Anchor = 1 | 3 | 5;

export interface FeatureScore {
  feature: string;
  anchor: Anchor;
  weight: number;
  must_have: boolean;
  evidence: string;
}

export interface SimulatorResult {
  verdict: Verdict;
  score: number;       // 0..1
  threshold: number;   // e.g. 0.70
  feature_scores: FeatureScore[];
  gaps: string[];      // empty on APPROVE
  critique: string;
  rationale: string[];
}

export interface TraceMetadata {
  case_id: string;
  insurer: string;
  denial_type: string;
  plan_type: string;
  state: string;
  prompt_version: string;
  playbook_version: string;
  dataset_split: string;
  run_mode: "interactive" | "benchmark" | "autonomous_promotion";
}

export interface AppealRequest {
  denial_text: string;
  clinical_context: string;
  case_id: string;
}

// The live /v1/appeal response.
export interface AppealResponse {
  run_id: string;
  appeal_letter: string;
  outcome: SimulatorResult;
  risk_flags: string[];
  trace_metadata: TraceMetadata;
}

// Plain-English "here's what we heard" — present in demo fixtures, optional live (spec §6).
export interface MirrorBlock {
  insurer: string;
  what_was_denied: string;
  why_they_said_no: string;
  deadline_note: string;       // factual, no urgency
  strongest_angle: string;
}

// Demo fixtures add the side-rail material the live API doesn't return yet.
export interface AppealFixture extends AppealResponse {
  mirror: MirrorBlock;
  citations_used: { title: string; quote: string }[];
  missing_evidence_checklist: string[];
}

// Student-safe case summary for both pickers. NO answer-key fields.
export interface CaseSummary {
  case_id: string;
  insurer: string;
  denial_type: string;      // human label, e.g. "Medical necessity"
  headline: string;         // one calm line, e.g. "Wegovy denied as a plan exclusion"
  denial_letter_text: string;
  clinical_context: string;
}

// Showcase bundle for one case.
export interface ShowcaseBundle {
  case_id: string;
  measured: boolean;        // true = real recorded run; false = faithful stand-in
  v1: { composite: number; verdict: Verdict; letter_excerpt: string };
  v3: { composite: number; verdict: Verdict; letter_excerpt: string };
  lift_relative_pct: number;
  what_changed: string[];   // laundered reflection notes
  counterfactual: { on_composite: number; off_composite: number };
  phoenix_url?: string;
}
```

- [ ] **Step 2: Verify compile** — Run (from `frontend/`): `pnpm exec tsc --noEmit`. Expected: no errors.

- [ ] **Step 3: Commit**
```bash
cd /bv3/aimbot/divya/buildmind-misc/aegis && git add frontend/src/lib/types.ts && git commit -m "feat(frontend): types mirroring the appeal API contract

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 2: Zod schemas + runtime parsers

**Files:**
- Create: `frontend/src/lib/schema.ts`
- Test: `frontend/src/__tests__/schema.test.ts`

- [ ] **Step 1: Write the failing test** — `frontend/src/__tests__/schema.test.ts`

```ts
import { describe, it, expect } from "vitest";
import { parseAppealResponse, parseAppealFixture } from "@/lib/schema";

const valid = {
  run_id: "r1", appeal_letter: "Dear Cigna,", risk_flags: [],
  outcome: { verdict: "DENY", score: 0.66, threshold: 0.7, feature_scores: [], gaps: ["weak: grounding (anchor 3)"], critique: "", rationale: [] },
  trace_metadata: { case_id: "c1", insurer: "Cigna", denial_type: "medical_necessity", plan_type: "commercial", state: "unknown", prompt_version: "aegis_v1_weak", playbook_version: "cold-start", dataset_split: "interactive", run_mode: "interactive" },
};

describe("parseAppealResponse", () => {
  it("accepts a valid response", () => {
    expect(parseAppealResponse(valid).outcome.verdict).toBe("DENY");
  });
  it("rejects an invalid verdict", () => {
    expect(() => parseAppealResponse({ ...valid, outcome: { ...valid.outcome, verdict: "MAYBE" } })).toThrow();
  });
});

describe("parseAppealFixture", () => {
  it("requires the mirror block", () => {
    expect(() => parseAppealFixture(valid)).toThrow();
  });
});
```

- [ ] **Step 2: Run test to verify it fails** — Run: `pnpm test schema`. Expected: FAIL (module not found).

- [ ] **Step 3: Implement `frontend/src/lib/schema.ts`**

```ts
import { z } from "zod";

const anchor = z.union([z.literal(1), z.literal(3), z.literal(5)]);
const verdict = z.enum(["APPROVE", "DENY"]);

export const featureScoreSchema = z.object({
  feature: z.string(), anchor, weight: z.number(),
  must_have: z.boolean(), evidence: z.string().default(""),
});

export const simulatorResultSchema = z.object({
  verdict, score: z.number(), threshold: z.number(),
  feature_scores: z.array(featureScoreSchema).default([]),
  gaps: z.array(z.string()).default([]),
  critique: z.string().default(""), rationale: z.array(z.string()).default([]),
});

export const traceMetadataSchema = z.object({
  case_id: z.string(), insurer: z.string(), denial_type: z.string(),
  plan_type: z.string(), state: z.string(), prompt_version: z.string(),
  playbook_version: z.string(), dataset_split: z.string(),
  run_mode: z.enum(["interactive", "benchmark", "autonomous_promotion"]),
});

export const appealResponseSchema = z.object({
  run_id: z.string(), appeal_letter: z.string(),
  outcome: simulatorResultSchema, risk_flags: z.array(z.string()).default([]),
  trace_metadata: traceMetadataSchema,
});

export const mirrorBlockSchema = z.object({
  insurer: z.string(), what_was_denied: z.string(), why_they_said_no: z.string(),
  deadline_note: z.string(), strongest_angle: z.string(),
});

export const appealFixtureSchema = appealResponseSchema.extend({
  mirror: mirrorBlockSchema,
  citations_used: z.array(z.object({ title: z.string(), quote: z.string() })).default([]),
  missing_evidence_checklist: z.array(z.string()).default([]),
});

// Reject any teacher answer-key field leaking into a consumer fixture (firewall INV-2).
export const FORBIDDEN_FIXTURE_KEYS = [
  "synthetic_provenance", "appeal_difficulty", "exploitable_weaknesses",
  "strong_defenses", "critic_verdicts", "intended_flaw_types",
];

export function parseAppealResponse(x: unknown) { return appealResponseSchema.parse(x); }
export function parseAppealFixture(x: unknown) { return appealFixtureSchema.parse(x); }
```

- [ ] **Step 4: Run test to verify it passes** — Run: `pnpm test schema`. Expected: PASS (3 tests).

- [ ] **Step 5: Commit**
```bash
cd /bv3/aimbot/divya/buildmind-misc/aegis && git add frontend/src/lib/schema.ts frontend/src/__tests__/schema.test.ts && git commit -m "feat(frontend): zod schemas + parsers for appeal contract

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 3: Case summaries fixture (student-safe, all 10)

**Files:**
- Create: `frontend/src/lib/fixtures/cases.ts`
- Test: `frontend/src/__tests__/firewall.test.ts`

The 10 test cases, **only** student-visible fields (case_id, insurer, denial_type label, headline, denial_letter_text, clinical_context). Source `denial_letter_text` + `clinical_context` verbatim from `eval/cases/drafts/test_case_*.json`; **never copy `synthetic_provenance`**.

- [ ] **Step 1: Write the failing firewall test** — `frontend/src/__tests__/firewall.test.ts`

```ts
import { describe, it, expect } from "vitest";
import { CASES } from "@/lib/fixtures/cases";
import { FORBIDDEN_FIXTURE_KEYS } from "@/lib/schema";

describe("firewall: consumer fixtures carry no teacher answer key", () => {
  it("has all 10 test cases", () => {
    expect(CASES).toHaveLength(10);
    expect(new Set(CASES.map((c) => c.case_id)).size).toBe(10);
  });
  it("contains no forbidden answer-key keys anywhere", () => {
    const blob = JSON.stringify(CASES);
    for (const k of FORBIDDEN_FIXTURE_KEYS) expect(blob).not.toContain(k);
  });
  it("every case has the student-visible fields", () => {
    for (const c of CASES) {
      expect(c.denial_letter_text.length).toBeGreaterThan(20);
      expect(c.insurer).toBeTruthy();
      expect(c.headline).toBeTruthy();
    }
  });
});
```

- [ ] **Step 2: Run test to verify it fails** — Run: `pnpm test firewall`. Expected: FAIL (module not found).

- [ ] **Step 3: Implement `frontend/src/lib/fixtures/cases.ts`**

For each of `test_case_01..10`, read its JSON from `eval/cases/drafts/`, copy ONLY `denial_letter_text` and `clinical_context` (verbatim), set `insurer`, map `denial_type` to a human label ("Medical Necessity"→"Medical necessity", "Prior Authorization"→"Prior authorization"), and write a one-line calm `headline`. Pattern (full file lists all 10):

```ts
import type { CaseSummary } from "@/lib/types";

export const CASES: CaseSummary[] = [
  {
    case_id: "test_case_03_cigna_mednec",
    insurer: "Cigna",
    denial_type: "Medical necessity",
    headline: "Wegovy denied as a plan exclusion",
    denial_letter_text:
      "Dear Member,\n\nWe have reviewed your provider's request for Semaglutide (Wegovy). We are denying this request because it does not meet Cigna's coverage criteria.\n\nWhile Wegovy is FDA-approved for weight management, your specific employer-sponsored pharmacy benefit plan has a strict exclusion for all weight-loss medications. Additionally, you do not have a diagnosis of Type 2 Diabetes, which would be required for coverage of similar GLP-1 medications (like Ozempic) under your medical benefit. Therefore, this request is denied as a plan exclusion and is not medically necessary.",
    clinical_context:
      "Patient has struggled with weight and is on the verge of developing full-blown Type 2 Diabetes. The doctor prescribed Wegovy to prevent the onset of diabetes. The denial relies on a hard employer plan exclusion for 'weight loss drugs', forcing an appeal to argue the preventative medical necessity rather than cosmetic weight loss.",
  },
  // ... the other 9 test cases, same shape, sourced verbatim from eval/cases/drafts/test_case_*.json
];
```

- [ ] **Step 4: Run test to verify it passes** — Run: `pnpm test firewall`. Expected: PASS (3 tests).

- [ ] **Step 5: Commit**
```bash
cd /bv3/aimbot/divya/buildmind-misc/aegis && git add frontend/src/lib/fixtures/cases.ts frontend/src/__tests__/firewall.test.ts && git commit -m "feat(frontend): student-safe case summaries for all 10 test cases + firewall test

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 4: Appeal fixtures (demo outputs, all 10)

**Files:**
- Create: `frontend/src/lib/fixtures/appeals/<case_id>.json` (×10)
- Test: extend `frontend/src/__tests__/firewall.test.ts`

Each is an `AppealFixture` (AppealResponse + mirror + side-rail). Where a recorded draft exists (`eval/efficacy_runs/*/drafts/v2/<case_id>*`), adapt its `appeal_letter` verbatim and set `outcome` consistent with the recorded simulator/score; otherwise author a faithful letter grounded ONLY in that case's denial+clinical text. `outcome.verdict`/`score`/`threshold` realistic (threshold 0.7). **No answer-key fields.**

- [ ] **Step 1: Add a fixture-validation test** — append to `firewall.test.ts`:

```ts
import { CASES } from "@/lib/fixtures/cases";
import { parseAppealFixture, FORBIDDEN_FIXTURE_KEYS } from "@/lib/schema";

describe("appeal fixtures", () => {
  it("one valid fixture per case, no answer key", async () => {
    for (const c of CASES) {
      const mod = await import(`@/lib/fixtures/appeals/${c.case_id}.json`);
      const fix = parseAppealFixture(mod.default);
      expect(fix.trace_metadata.case_id).toBe(c.case_id);
      const blob = JSON.stringify(mod.default);
      for (const k of FORBIDDEN_FIXTURE_KEYS) expect(blob).not.toContain(k);
    }
  });
});
```

- [ ] **Step 2: Run test to verify it fails** — Run: `pnpm test firewall`. Expected: FAIL (fixtures missing).

- [ ] **Step 3: Author the 10 fixtures.** Example `frontend/src/lib/fixtures/appeals/test_case_03_cigna_mednec.json`:

```json
{
  "run_id": "demo_test_case_03_cigna_mednec",
  "appeal_letter": "Dear Cigna Appeals Review,\n\nI am writing to appeal the denial of Semaglutide (Wegovy) for [Member Name], dated [date]. The denial cites a pharmacy-benefit exclusion for weight-loss medications and the absence of a Type 2 Diabetes diagnosis. This appeal asks you to review the request as preventive medical care, not weight management.\n\nThe prescribing physician documents pre-diabetes with a documented progression risk toward Type 2 Diabetes. Wegovy was prescribed to prevent that onset — a recognized medical purpose distinct from cosmetic weight loss. The plan's exclusion addresses weight-loss treatment; it does not speak to preventive treatment of a metabolic condition with imminent clinical risk.\n\nThe denial also conflates two separate grounds — a contractual exclusion and a medical-necessity judgment. We ask that the medical-necessity determination be reviewed on its own record, with the attached clinical notes.\n\nWe request a full clinical review and reversal. Please confirm receipt and the deadline for any further submission.\n\nThis letter is a draft for your review.",
  "outcome": {
    "verdict": "DENY",
    "score": 0.66,
    "threshold": 0.7,
    "feature_scores": [
      { "feature": "grounding", "anchor": 3, "weight": 0.3, "must_have": false, "evidence": "Cites the plan exclusion and clinical context, but no policy document quoted." },
      { "feature": "appeal_vector_capture", "anchor": 3, "weight": 0.25, "must_have": true, "evidence": "Names the preventive-care vector but does not fully separate the contractual ground." }
    ],
    "gaps": ["weak: grounding (anchor 3)", "weak: appeal_vector_capture (anchor 3)"],
    "critique": "Strong preventive-care framing; would be stronger with a quoted plan provision and a cleaner split of the two denial grounds.",
    "rationale": ["Strong preventive-care framing; would be stronger with a quoted plan provision and a cleaner split of the two denial grounds."]
  },
  "risk_flags": ["Plan exclusion is a hard contractual barrier; outcome is uncertain."],
  "trace_metadata": {
    "case_id": "test_case_03_cigna_mednec", "insurer": "Cigna", "denial_type": "medical_necessity",
    "plan_type": "commercial", "state": "unknown", "prompt_version": "aegis_v1_weak",
    "playbook_version": "cold-start", "dataset_split": "interactive", "run_mode": "interactive"
  },
  "mirror": {
    "insurer": "Cigna",
    "what_was_denied": "Coverage for Semaglutide (Wegovy).",
    "why_they_said_no": "They point to a plan exclusion for weight-loss medications, and note there is no Type 2 Diabetes diagnosis.",
    "deadline_note": "Check your letter for the appeal deadline and file before that date.",
    "strongest_angle": "This was prescribed to prevent diabetes, not for weight loss — that is preventive medical care, which the exclusion does not cover."
  },
  "citations_used": [
    { "title": "Plan denial letter", "quote": "strict exclusion for all weight-loss medications" }
  ],
  "missing_evidence_checklist": [
    "Recent labs showing pre-diabetes (A1c)",
    "Physician note stating the preventive purpose",
    "The plan's medical-necessity criteria, if you can obtain them"
  ]
}
```

Repeat for the other 9, each grounded in its own case. Cases `01–04` have recorded per-case v1/v2 scores (Run #1) — keep their `outcome.score` consistent with those.

- [ ] **Step 4: Run test to verify it passes** — Run: `pnpm test firewall`. Expected: PASS.

- [ ] **Step 5: Commit**
```bash
cd /bv3/aimbot/divya/buildmind-misc/aegis && git add frontend/src/lib/fixtures/appeals/ frontend/src/__tests__/firewall.test.ts && git commit -m "feat(frontend): demo appeal fixtures for all 10 cases (answer-key-free)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 5: Showcase fixtures + recorded artifacts

**Files:**
- Create: `frontend/tests-data/recorded/efficacy_run1.json` (copy of `eval/efficacy_runs/2026-05-31/result.json`)
- Create: `frontend/src/lib/fixtures/showcase/<case_id>.json` (×10)
- Create: `frontend/src/lib/fixtures/showcase/_runs.ts`

- [ ] **Step 1: Copy the recorded run** (build-time import; keeps numbers truthful)
```bash
mkdir -p frontend/tests-data/recorded && cp eval/efficacy_runs/2026-05-31/result.json frontend/tests-data/recorded/efficacy_run1.json
```

- [ ] **Step 2: Create `_runs.ts`** exposing the recorded aggregate:
```ts
import run1 from "../../../tests-data/recorded/efficacy_run1.json";
export const RUN1 = run1 as {
  baseline_composite: number; optimized_composite: number; lift_relative_pct: number;
  per_case: Record<string, { v1: number; v2: number }>;
};
export const COUNTERFACTUAL = { on_composite: 0.88, off_composite: 0.42 }; // design-target; labeled in UI
```

- [ ] **Step 3: Author one `ShowcaseBundle` JSON per case.** For cases `01–04` set `measured: true` and use `RUN1.per_case[case_id]` numbers (v1/v3 composites, +20.5% relative). For `05–10` set `measured: false` (faithful stand-in). `what_changed` = laundered reflection bullets (no answer key). Example `test_case_03_cigna_mednec.json`:
```json
{
  "case_id": "test_case_03_cigna_mednec", "measured": true,
  "v1": { "composite": 0.66, "verdict": "DENY", "letter_excerpt": "We believe this treatment is medically necessary and should be covered..." },
  "v3": { "composite": 0.88, "verdict": "APPROVE", "letter_excerpt": "This appeal asks you to review the request as preventive medical care, not weight management..." },
  "lift_relative_pct": 20.5,
  "what_changed": [
    "Earlier drafts asserted necessity without naming the specific appeal vector.",
    "The improved version names the strongest vector for this slice and separates the contractual ground from the clinical one."
  ],
  "counterfactual": { "on_composite": 0.88, "off_composite": 0.42 },
  "phoenix_url": ""
}
```

- [ ] **Step 4: Verify build-time import** — Run (from `frontend/`): `pnpm exec tsc --noEmit`. Expected: no errors (JSON resolves; `resolveJsonModule` is on by Next default — if not, add to tsconfig).

- [ ] **Step 5: Commit**
```bash
cd /bv3/aimbot/divya/buildmind-misc/aegis && git add frontend/tests-data/recorded/ frontend/src/lib/fixtures/showcase/ && git commit -m "feat(frontend): showcase bundles + recorded efficacy artifact (cases 01-04 measured)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 6: DataSource interface + demo impl + selector

**Files:**
- Create: `frontend/src/lib/data/source.ts`, `demo.ts`, `index.ts`
- Test: `frontend/src/__tests__/demo.test.ts`

- [ ] **Step 1: Write the failing test** — `frontend/src/__tests__/demo.test.ts`

```ts
import { describe, it, expect } from "vitest";
import { demoSource } from "@/lib/data/demo";

describe("demoSource", () => {
  it("lists 10 cases", async () => {
    expect(await demoSource.listCases()).toHaveLength(10);
  });
  it("drafts an appeal for a known case", async () => {
    const r = await demoSource.draftAppeal({ denial_text: "x", clinical_context: "", case_id: "test_case_03_cigna_mednec" });
    expect(r.outcome.verdict === "APPROVE" || r.outcome.verdict === "DENY").toBe(true);
    expect(r.appeal_letter.length).toBeGreaterThan(50);
  });
  it("returns a showcase bundle", async () => {
    const s = await demoSource.getShowcase("test_case_03_cigna_mednec");
    expect(s.lift_relative_pct).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails** — Run: `pnpm test demo`. Expected: FAIL (module not found).

- [ ] **Step 3: Implement `source.ts`**
```ts
import type { AppealRequest, AppealFixture, CaseSummary, ShowcaseBundle } from "@/lib/types";

export interface DataSource {
  listCases(): Promise<CaseSummary[]>;
  draftAppeal(req: AppealRequest): Promise<AppealFixture>;
  getShowcase(caseId: string): Promise<ShowcaseBundle>;
}
```

- [ ] **Step 4: Implement `demo.ts`**
```ts
import type { DataSource } from "./source";
import type { AppealRequest, AppealFixture, ShowcaseBundle } from "@/lib/types";
import { CASES } from "@/lib/fixtures/cases";
import { parseAppealFixture } from "@/lib/schema";

const FALLBACK = "test_case_03_cigna_mednec";

export const demoSource: DataSource = {
  async listCases() { return CASES; },
  async draftAppeal(req: AppealRequest): Promise<AppealFixture> {
    const id = CASES.some((c) => c.case_id === req.case_id) ? req.case_id : FALLBACK;
    const mod = await import(`@/lib/fixtures/appeals/${id}.json`);
    return parseAppealFixture(mod.default);
  },
  async getShowcase(caseId: string): Promise<ShowcaseBundle> {
    const id = CASES.some((c) => c.case_id === caseId) ? caseId : FALLBACK;
    const mod = await import(`@/lib/fixtures/showcase/${id}.json`);
    return mod.default as ShowcaseBundle;
  },
};
```

- [ ] **Step 5: Implement `index.ts`**
```ts
import type { DataSource } from "./source";
import { demoSource } from "./demo";

export function getDataSource(): DataSource {
  if (process.env.NEXT_PUBLIC_AEGIS_MODE === "live") {
    // lazy import keeps the live client out of the demo bundle
    const { liveSource } = require("./live") as typeof import("./live");
    return liveSource;
  }
  return demoSource;
}
```

- [ ] **Step 6: Run test to verify it passes** — Run: `pnpm test demo`. Expected: PASS (3 tests).

- [ ] **Step 7: Commit**
```bash
cd /bv3/aimbot/divya/buildmind-misc/aegis && git add frontend/src/lib/data/ frontend/src/__tests__/demo.test.ts && git commit -m "feat(frontend): DataSource seam + demo impl + env selector

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 7: Live DataSource impl

**Files:**
- Create: `frontend/src/lib/data/live.ts`

Calls `/v1/appeal`; `listCases`/`getShowcase` reuse bundled artifacts (showcase is always recorded evidence). Live API lacks `mirror`/`citations` (spec §6) — synthesize a light `mirror` from `trace_metadata`.

- [ ] **Step 1: Implement `live.ts`**
```ts
import type { DataSource } from "./source";
import type { AppealRequest, AppealFixture } from "@/lib/types";
import { parseAppealResponse } from "@/lib/schema";
import { demoSource } from "./demo";

const BASE = process.env.NEXT_PUBLIC_AEGIS_API ?? "http://localhost:8001";

export const liveSource: DataSource = {
  listCases: demoSource.listCases,
  getShowcase: demoSource.getShowcase,
  async draftAppeal(req: AppealRequest): Promise<AppealFixture> {
    const res = await fetch(`${BASE}/v1/appeal`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) throw new Error(`appeal failed: ${res.status}`);
    const data = parseAppealResponse(await res.json());
    return {
      ...data,
      mirror: {
        insurer: data.trace_metadata.insurer,
        what_was_denied: "See the denial letter you provided.",
        why_they_said_no: "Summarized from your letter.",
        deadline_note: "Check your letter for the appeal deadline and file before that date.",
        strongest_angle: data.outcome.critique || "Review the draft below.",
      },
      citations_used: [],
      missing_evidence_checklist: [],
    };
  },
};
```

- [ ] **Step 2: Verify compile** — Run: `pnpm exec tsc --noEmit`. Expected: no errors.

- [ ] **Step 3: Commit**
```bash
cd /bv3/aimbot/divya/buildmind-misc/aegis && git add frontend/src/lib/data/live.ts && git commit -m "feat(frontend): live /v1/appeal DataSource with graceful mirror fallback

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Phase 2 — UI primitives

### Task 8: UI primitives (Field, TextArea, Disclaimer, ProgressHairline, StatusDot, Callout, ScoreMeter)

**Files:**
- Create: `frontend/src/components/ui/{Field,TextArea,Disclaimer,ProgressHairline,StatusDot,Callout,ScoreMeter}.tsx`

All token-only, a11y-correct. No tests (presentational; verified by build + render).

- [ ] **Step 1: `StatusDot.tsx`** — the signature sage dot.
```tsx
import { cn } from "@/lib/cn";
export function StatusDot({ tone = "sage", className }: { tone?: "sage" | "clay"; className?: string }) {
  return <span aria-hidden className={cn("inline-block h-1.5 w-1.5 rounded-full",
    tone === "sage" ? "bg-accent-sage" : "bg-accent-clay", className)} />;
}
```

- [ ] **Step 2: `Disclaimer.tsx`** — verbatim safety line (PRD §21 short form).
```tsx
export function Disclaimer({ className }: { className?: string }) {
  return (
    <p className={`font-body text-sm text-text-tertiary ${className ?? ""}`}>
      This is a draft for your review. It is not legal or medical advice. A person should read it before you file.
    </p>
  );
}
```

- [ ] **Step 3: `TextArea.tsx`** and **`Field.tsx`** — labeled inputs, 56px min tap target, visible focus ring (`focus-visible:outline-2 outline-accent-sage`).
```tsx
// TextArea.tsx
import { forwardRef, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/cn";
export const TextArea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string; hint?: string }>(
  function TextArea({ label, hint, id, className, ...rest }, ref) {
    const tid = id ?? rest.name ?? "ta";
    return (
      <div className="flex flex-col gap-2">
        <label htmlFor={tid} className="font-body text-sm text-text-secondary">{label}</label>
        {hint && <p className="font-body text-sm text-text-tertiary">{hint}</p>}
        <textarea id={tid} ref={ref}
          className={cn("min-h-40 w-full rounded-md bg-surface-secondary border border-border-default p-4 font-body text-base text-text-primary",
            "focus-visible:outline-2 focus-visible:outline-accent-sage placeholder:text-text-muted", className)}
          {...rest} />
      </div>
    );
  });
```
`Field.tsx` mirrors this for single-line `<input>`.

- [ ] **Step 4: `ProgressHairline.tsx`** — thin top rule with a sage segment (no numbers/circles).
```tsx
export function ProgressHairline({ ratio }: { ratio: number }) {
  const pct = Math.max(0, Math.min(1, ratio)) * 100;
  return (
    <div className="h-px w-full bg-border-subtle" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}>
      <div className="h-px bg-accent-sage transition-[width] duration-[400ms] ease-[cubic-bezier(0.2,0.8,0.2,1)]" style={{ width: `${pct}%` }} />
    </div>
  );
}
```

- [ ] **Step 5: `Callout.tsx`** (hairline-bordered note; `tone` sage|clay|neutral) and **`ScoreMeter.tsx`** (a labeled 0–1 bar against a threshold marker; used on showcase + verdict). ScoreMeter:
```tsx
import { cn } from "@/lib/cn";
export function ScoreMeter({ score, threshold, label }: { score: number; threshold?: number; label?: string }) {
  return (
    <div className="flex flex-col gap-1">
      {label && <span className="font-body text-sm text-text-secondary">{label}</span>}
      <div className="relative h-2 w-full rounded-pill bg-surface-tertiary">
        <div className="h-2 rounded-pill bg-accent-sage" style={{ width: `${Math.round(score * 100)}%` }} />
        {threshold != null && <div className="absolute top-[-2px] h-3 w-px bg-border-strong" style={{ left: `${Math.round(threshold * 100)}%` }} aria-hidden />}
      </div>
      <span className="font-mono text-xs text-text-tertiary">{score.toFixed(2)}{threshold != null ? ` · threshold ${threshold.toFixed(2)}` : ""}</span>
    </div>
  );
}
```

- [ ] **Step 6: Verify** — Run (from `frontend/`): `pnpm exec tsc --noEmit && pnpm lint`. Expected: no errors.

- [ ] **Step 7: Commit**
```bash
cd /bv3/aimbot/divya/buildmind-misc/aegis && git add frontend/src/components/ui/ && git commit -m "feat(frontend): token-only UI primitives (Field, TextArea, Disclaimer, ProgressHairline, StatusDot, Callout, ScoreMeter)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Phase 3 — Consumer flow (`/appeal`)

### Task 9: Flow state machine (pure reducer, TDD)

**Files:**
- Create: `frontend/src/lib/flow/reducer.ts`
- Test: `frontend/src/__tests__/reducer.test.ts`

States: `intake → working → mirror → draft → decide`. Pure; no async.

- [ ] **Step 1: Write the failing test** — `frontend/src/__tests__/reducer.test.ts`
```ts
import { describe, it, expect } from "vitest";
import { flowReducer, initialFlow } from "@/lib/flow/reducer";

const fix = { run_id: "r", appeal_letter: "Dear Cigna", outcome: { verdict: "DENY", score: 0.66, threshold: 0.7, feature_scores: [], gaps: [], critique: "", rationale: [] }, risk_flags: [], trace_metadata: {} as any, mirror: {} as any, citations_used: [], missing_evidence_checklist: [] };

describe("flowReducer", () => {
  it("starts at intake", () => { expect(initialFlow.step).toBe("intake"); });
  it("submit → working", () => {
    const s = flowReducer(initialFlow, { type: "SUBMIT", req: { denial_text: "x", clinical_context: "", case_id: "c" } });
    expect(s.step).toBe("working");
    expect(s.req?.denial_text).toBe("x");
  });
  it("result → mirror, holds the fixture", () => {
    const s = flowReducer({ ...initialFlow, step: "working" }, { type: "RESULT", result: fix as any });
    expect(s.step).toBe("mirror");
    expect(s.result?.appeal_letter).toBe("Dear Cigna");
  });
  it("advances mirror→draft→decide and edits the letter", () => {
    let s = flowReducer({ ...initialFlow, step: "mirror", result: fix as any }, { type: "ADVANCE" });
    expect(s.step).toBe("draft");
    s = flowReducer(s, { type: "EDIT_LETTER", letter: "edited" });
    expect(s.result?.appeal_letter).toBe("edited");
    s = flowReducer(s, { type: "ADVANCE" });
    expect(s.step).toBe("decide");
  });
  it("RESET returns to intake", () => {
    expect(flowReducer({ ...initialFlow, step: "decide" }, { type: "RESET" }).step).toBe("intake");
  });
});
```

- [ ] **Step 2: Run test to verify it fails** — Run: `pnpm test reducer`. Expected: FAIL (module not found).

- [ ] **Step 3: Implement `reducer.ts`**
```ts
import type { AppealRequest, AppealFixture } from "@/lib/types";

export type FlowStep = "intake" | "working" | "mirror" | "draft" | "decide";
export interface FlowState { step: FlowStep; req?: AppealRequest; result?: AppealFixture; error?: string; }
export const initialFlow: FlowState = { step: "intake" };

const ORDER: FlowStep[] = ["intake", "working", "mirror", "draft", "decide"];

export type FlowAction =
  | { type: "SUBMIT"; req: AppealRequest }
  | { type: "RESULT"; result: AppealFixture }
  | { type: "ERROR"; error: string }
  | { type: "EDIT_LETTER"; letter: string }
  | { type: "ADVANCE" }
  | { type: "RESET" };

export function flowReducer(state: FlowState, action: FlowAction): FlowState {
  switch (action.type) {
    case "SUBMIT": return { step: "working", req: action.req };
    case "RESULT": return { ...state, step: "mirror", result: action.result, error: undefined };
    case "ERROR": return { ...state, step: "intake", error: action.error };
    case "EDIT_LETTER":
      return state.result ? { ...state, result: { ...state.result, appeal_letter: action.letter } } : state;
    case "ADVANCE": {
      const i = ORDER.indexOf(state.step);
      return { ...state, step: ORDER[Math.min(i + 1, ORDER.length - 1)] };
    }
    case "RESET": return initialFlow;
    default: return state;
  }
}
```

- [ ] **Step 4: Run test to verify it passes** — Run: `pnpm test reducer`. Expected: PASS (5 tests).

- [ ] **Step 5: Commit**
```bash
cd /bv3/aimbot/divya/buildmind-misc/aegis && git add frontend/src/lib/flow/reducer.ts frontend/src/__tests__/reducer.test.ts && git commit -m "feat(frontend): consumer-flow state machine (pure reducer)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 10: Flow components

**Files:**
- Create: `frontend/src/components/flow/{IntakePanel,WorkingProgress,MirrorCard,DraftEditor,DecideBar}.tsx`

Each is a presentational component with the props below. Copy must follow the copy rules. Verified by build/lint + render in Task 11.

- [ ] **Step 1: `IntakePanel.tsx`** — props `{ cases: CaseSummary[]; onSubmit(req): void }`. A serif heading "Tell us what happened.", a `TextArea` (label "Paste the denial letter", name `denial_text`), a sample-case picker (`<select>` or button list of `cases`, fills the textarea), an optional `TextArea` (label "Anything your doctor said or wrote", name `clinical_context`, hint "Optional."), and a primary `Button` "Draft the appeal". On submit, build `{ denial_text, clinical_context, case_id }` (case_id = picked case id or `"interactive_case"`).

- [ ] **Step 2: `WorkingProgress.tsx`** — props `{}`. Cycles three calm lines on a timer (honor `prefers-reduced-motion` — if reduced, show static "Working on your appeal…"): "Reading your denial…" → "Drafting your appeal…" → "Almost done." Uses `ProgressHairline` with rising ratio. No spinner.

- [ ] **Step 3: `MirrorCard.tsx`** — props `{ mirror: MirrorBlock; onContinue(): void }`. Serif heading "Here's what we heard.", then labeled plain-English lines: what was denied, why they said no, the deadline note (factual), and "The strongest angle we see" highlighted in a sage `Callout`. Primary `Button` "See the draft".

- [ ] **Step 4: `DraftEditor.tsx`** — props `{ result: AppealFixture; onEdit(letter): void; onContinue(): void }`. Two-column on desktop, single-column mobile: left = editable letter (`<textarea>` bound to `result.appeal_letter`, calls `onEdit`); right rail = `ScoreMeter` for `outcome.score`/`threshold` with an honest label ("Transparent proxy — not a prediction of your insurer."), the `verdict` as a `StatusDot` + word, `outcome.gaps` rendered as "What would make this stronger", `citations_used`, `missing_evidence_checklist`, `risk_flags` (clay `Callout`), and `Disclaimer`. Primary `Button` "I'm ready to decide".

- [ ] **Step 5: `DecideBar.tsx`** — props `{ result: AppealFixture; onRestart(): void }`. Copy/Download (.txt, .md) buttons (client-side Blob download), "A person should read this before you file.", deadline restated, a ghost `Button` "Start another draft". No celebration, no filing.

- [ ] **Step 6: Verify** — Run: `pnpm exec tsc --noEmit && pnpm lint`. Expected: no errors.

- [ ] **Step 7: Commit**
```bash
cd /bv3/aimbot/divya/buildmind-misc/aegis && git add frontend/src/components/flow/ && git commit -m "feat(frontend): consumer-flow components (intake, working, mirror, draft, decide)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 11: `/appeal` page (wire the flow)

**Files:**
- Create: `frontend/src/app/appeal/page.tsx`

- [ ] **Step 1: Implement the client page** — `"use client"`, `useReducer(flowReducer, initialFlow)`, `getDataSource()` from `@/lib/data`. On `SUBMIT`: dispatch SUBMIT, then `await draftAppeal(req)` → dispatch RESULT (or ERROR). Render `ProgressHairline` (ratio by step index) at top, then the component for `state.step`. Load `cases` via `listCases()` in an effect for the IntakePanel. framer-motion crossfade + 8–12px upward translate between steps; honor reduced-motion.

```tsx
"use client";
import { useEffect, useReducer, useState } from "react";
import { flowReducer, initialFlow } from "@/lib/flow/reducer";
import { getDataSource } from "@/lib/data";
import type { CaseSummary } from "@/lib/types";
import { Nav } from "@/components/Nav";
import { ProgressHairline } from "@/components/ui/ProgressHairline";
import { IntakePanel } from "@/components/flow/IntakePanel";
import { WorkingProgress } from "@/components/flow/WorkingProgress";
import { MirrorCard } from "@/components/flow/MirrorCard";
import { DraftEditor } from "@/components/flow/DraftEditor";
import { DecideBar } from "@/components/flow/DecideBar";

const STEP_RATIO = { intake: 0.1, working: 0.35, mirror: 0.6, draft: 0.85, decide: 1 } as const;

export default function AppealPage() {
  const [state, dispatch] = useReducer(flowReducer, initialFlow);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const ds = getDataSource();
  useEffect(() => { ds.listCases().then(setCases); }, []); // eslint-disable-line

  async function submit(req: Parameters<typeof ds.draftAppeal>[0]) {
    dispatch({ type: "SUBMIT", req });
    try { dispatch({ type: "RESULT", result: await ds.draftAppeal(req) }); }
    catch { dispatch({ type: "ERROR", error: "Something's not working on our side. Try again." }); }
  }

  return (
    <div className="min-h-dvh bg-surface-primary text-text-primary">
      <Nav />
      <ProgressHairline ratio={STEP_RATIO[state.step]} />
      <main className="mx-auto max-w-(--container-prose) px-6 md:px-12 py-16 md:py-24">
        {state.error && <p className="mb-6 font-body text-sm text-status-error">{state.error}</p>}
        {state.step === "intake" && <IntakePanel cases={cases} onSubmit={submit} />}
        {state.step === "working" && <WorkingProgress />}
        {state.step === "mirror" && state.result && <MirrorCard mirror={state.result.mirror} onContinue={() => dispatch({ type: "ADVANCE" })} />}
        {state.step === "draft" && state.result && <DraftEditor result={state.result} onEdit={(l) => dispatch({ type: "EDIT_LETTER", letter: l })} onContinue={() => dispatch({ type: "ADVANCE" })} />}
        {state.step === "decide" && state.result && <DecideBar result={state.result} onRestart={() => dispatch({ type: "RESET" })} />}
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Verify build + manual** — Run: `pnpm build`. Expected: success. Then `pnpm dev`, visit `/appeal`, walk intake→decide with the sample case. Expected: each step renders, letter is editable, download works.

- [ ] **Step 3: Commit**
```bash
cd /bv3/aimbot/divya/buildmind-misc/aegis && git add frontend/src/app/appeal/page.tsx && git commit -m "feat(frontend): /appeal consumer flow page wired to DataSource

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Phase 4 — Showcase (`/showcase`)

### Task 12: Showcase components

**Files:**
- Create: `frontend/src/components/showcase/{CasePicker,VersusPanel,DiffCard,CounterfactualCard}.tsx`

- [ ] **Step 1: `CasePicker.tsx`** — props `{ cases: CaseSummary[]; selected: string; onSelect(id): void }`. A horizontal/wrapping list of selectable chips labeled `insurer · denial_type`; selected chip carries a `StatusDot`. Keyboard-navigable (`role="radiogroup"`).

- [ ] **Step 2: `VersusPanel.tsx`** — props `{ bundle: ShowcaseBundle }`. Two columns "Earlier draft" / "Improved draft": each shows `letter_excerpt`, a `ScoreMeter` (composite), and verdict `StatusDot`. Below: the `lift_relative_pct` stated as evidence ("+20.5% on held-out cases"), and if `!bundle.measured` a neutral `Callout`: "Illustrative for this case — measured numbers shown for cases with a recorded run."

- [ ] **Step 3: `DiffCard.tsx`** — props `{ whatChanged: string[] }`. Serif heading "What changed, and why." + the laundered bullets.

- [ ] **Step 4: `CounterfactualCard.tsx`** — props `{ on: number; off: number }`. Two ScoreMeters (memory on vs off) + line "With its memory switched off, quality drops." + a labeled note that the off-number is a design target where not measured.

- [ ] **Step 5: Verify** — Run: `pnpm exec tsc --noEmit && pnpm lint`. Expected: no errors.

- [ ] **Step 6: Commit**
```bash
cd /bv3/aimbot/divya/buildmind-misc/aegis && git add frontend/src/components/showcase/ && git commit -m "feat(frontend): showcase components (case picker, versus, diff, counterfactual)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 13: `/showcase` page ("How Aegis learns")

**Files:**
- Create: `frontend/src/app/showcase/page.tsx`

- [ ] **Step 1: Implement** — `"use client"`. Default selected case `test_case_03_cigna_mednec`. Load `listCases()`; on select, `getShowcase(id)` → render thesis line (serif) + `CasePicker` + `VersusPanel` + `DiffCard` + `CounterfactualCard` + a Phoenix link-out (`ArrowUpRightIcon`, rendered only if `phoenix_url`). This surface MAY use the words "learns"/"memory"/"observability" — but still no "Gemini"/"ADK" branding.
```tsx
"use client";
import { useEffect, useState } from "react";
import { getDataSource } from "@/lib/data";
import type { CaseSummary, ShowcaseBundle } from "@/lib/types";
import { Nav } from "@/components/Nav";
import { CasePicker } from "@/components/showcase/CasePicker";
import { VersusPanel } from "@/components/showcase/VersusPanel";
import { DiffCard } from "@/components/showcase/DiffCard";
import { CounterfactualCard } from "@/components/showcase/CounterfactualCard";

export default function ShowcasePage() {
  const ds = getDataSource();
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [sel, setSel] = useState("test_case_03_cigna_mednec");
  const [bundle, setBundle] = useState<ShowcaseBundle | null>(null);
  useEffect(() => { ds.listCases().then(setCases); }, []); // eslint-disable-line
  useEffect(() => { ds.getShowcase(sel).then(setBundle); }, [sel]); // eslint-disable-line
  return (
    <div className="min-h-dvh bg-surface-primary text-text-primary">
      <Nav />
      <main className="mx-auto max-w-(--container-app) px-6 md:px-12 py-16 md:py-24 flex flex-col gap-16">
        <h1 className="font-display text-display-lg font-semibold tracking-tight max-w-2xl">This agent improves from its own observability.</h1>
        <CasePicker cases={cases} selected={sel} onSelect={setSel} />
        {bundle && <><VersusPanel bundle={bundle} /><DiffCard whatChanged={bundle.what_changed} /><CounterfactualCard on={bundle.counterfactual.on_composite} off={bundle.counterfactual.off_composite} /></>}
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Verify build + manual** — Run: `pnpm build`, then `pnpm dev`, visit `/showcase`, switch cases. Expected: numbers change; cases 01–04 show measured, others labeled illustrative.

- [ ] **Step 3: Commit**
```bash
cd /bv3/aimbot/divya/buildmind-misc/aegis && git add frontend/src/app/showcase/page.tsx && git commit -m "feat(frontend): /showcase 'How Aegis learns' page

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Phase 5 — Landing, nav, polish

### Task 14: Shared Nav + landing cross-links

**Files:**
- Create: `frontend/src/components/Nav.tsx`
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: `Nav.tsx`** — `Wordmark` left; right links "Draft an appeal" (`/appeal`) and "How Aegis learns" (`/showcase`). `<nav aria-label="Primary">`. Reuse landing header styling.

- [ ] **Step 2: Modify `page.tsx`** — replace the inline header with `<Nav />`; point the hero "Start a draft" `Button` at `/appeal` (wrap in `<Link>`); add a quiet footer link to `/showcase` labeled "How this gets better over time". Keep all existing copy/hero — no exclamation marks.

- [ ] **Step 3: Verify** — Run: `pnpm build && pnpm lint`. Expected: success. `pnpm dev`: landing → both surfaces reachable.

- [ ] **Step 4: Commit**
```bash
cd /bv3/aimbot/divya/buildmind-misc/aegis && git add frontend/src/components/Nav.tsx frontend/src/app/page.tsx && git commit -m "feat(frontend): shared nav + landing cross-links to both surfaces

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 15: a11y, reduced-motion, responsive, copy audit

**Files:**
- Modify: any component needing fixes found in audit.

- [ ] **Step 1: Reduced-motion** — confirm `WorkingProgress` and page transitions short-circuit under `prefers-reduced-motion: reduce` (tokens already zero durations; verify framer-motion respects `useReducedMotion()`).

- [ ] **Step 2: Keyboard + focus** — tab through `/appeal` and `/showcase`: every interactive element reachable, visible sage focus ring, `CasePicker` arrow-key navigable.

- [ ] **Step 3: Copy audit** — grep the user-facing surfaces for violations:
```bash
cd frontend && grep -rniE "!|\bAI\b|Phoenix|Gemini|ADK|🚀|awesome|let's go" src/app/page.tsx src/app/appeal src/components/flow src/components/ui || echo "clean"
```
Expected: `clean` (note: `/showcase` is allowed "learns/observability" but still no "Gemini/ADK"; audit it separately for those two only).

- [ ] **Step 4: Responsive** — check 375px and 1280px widths on all three routes; reading column ≤ 64ch; no horizontal scroll.

- [ ] **Step 5: Full verify** — Run (from `frontend/`): `pnpm test && pnpm exec tsc --noEmit && pnpm lint && pnpm build`. Expected: all green.

- [ ] **Step 6: Commit**
```bash
cd /bv3/aimbot/divya/buildmind-misc/aegis && git add -A frontend/ && git commit -m "fix(frontend): a11y, reduced-motion, responsive, and copy audit pass

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 16: Update docs

**Files:**
- Modify: `docs/memory/current-state.md`, `docs/memory/project-index.md`
- Create: `frontend/README.md` section or note on `NEXT_PUBLIC_AEGIS_MODE`

- [ ] **Step 1:** Record the two-surface frontend (demo default, live via `NEXT_PUBLIC_AEGIS_MODE=live` + `NEXT_PUBLIC_AEGIS_API`), the firewall test, and the spec/plan paths in `current-state.md` + a `project-index.md` handoff row.

- [ ] **Step 2: Commit**
```bash
cd /bv3/aimbot/divya/buildmind-misc/aegis && git add docs/ frontend/README.md && git commit -m "docs: record two-surface frontend build + demo/live data modes

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (completed by plan author)

**Spec coverage:**
- Two surfaces (spec §1) → Tasks 11, 13, 14. ✓
- Consumer arc intake→working→mirror→draft→decide (§2) → Tasks 9, 10, 11. ✓
- Data mapping + Mirror gap (§2.2, §6.1) → Tasks 1, 7, 10 (MirrorCard + live fallback). ✓
- Showcase sections v1/v3, diff, counterfactual, Phoenix link (§3) → Tasks 5, 12, 13. ✓
- DataSource seam, demo default, live flag (§4.1) → Tasks 6, 7. ✓
- Type fidelity / no false-green (§4.2) → Tasks 1, 2, 4 (zod validation at author time). ✓
- Firewall: no answer key in consumer bundle (case files carry it) → Tasks 3, 4 (firewall test). ✓
- All 10 cases selectable; 05–10 labeled stand-ins (§6.2, PM steer) → Tasks 3, 4, 5, 12 (`measured` flag). ✓
- Quality bar a11y/motion/copy (§4.3) → Task 8 (primitives) + Task 15 (audit). ✓
- Out-of-scope honored (§5): no auth/persistence/PDF/analytics/promotion UI → none added. ✓

**Placeholder scan:** No "TBD/TODO". Fixture-authoring tasks (3,4,5) specify exact source files, the exact shape, a complete worked example, and a validation gate (zod parse + firewall test) — not placeholders.

**Type consistency:** `AppealFixture`/`ShowcaseBundle`/`CaseSummary`/`FlowState` defined in Task 1 and used unchanged in Tasks 6, 7, 9, 10, 12, 13. `getDataSource()`, `demoSource`, `liveSource`, `flowReducer`, `initialFlow` names consistent across tasks. ✓

**Known follow-up (not blocking):** extending `AppealResponse` to return `parsed_case` + `appeal_strategy` is a backend change (spec §6.1 option b); this plan ships option (a) and notes it.
