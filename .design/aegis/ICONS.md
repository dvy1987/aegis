# Icons for Aegis

**Strategy:** mixed — **tuned Lucide subset (functional)** + **bespoke SVGs (signature surfaces)**
**Source:** Lucide React (heavily tuned) + ~8 hand-drawn SVGs designed at the size used
**Weight:** stroke 1.5 px on 24 px optical, 1.25 px on 16 px
**Sizes used:** 16 px (inline), 20 px (controls), 24 px (nav, buttons), 32 px (workflow stepper / hero)
**Grid:** 24 × 24 (with 16 × 16 redraw for any icon used at 16 px — never scale-down)
**Corner radius:** 1.5 px on stroke caps and joins (not the default 0)
**Color:** `--ink-7` until interactive; `--accent-sage` only on the active stepper-dot and primary actions

---

## Why mixed (not custom-svg-only or tuned-Lucide-only)

Per design-brief §6 and the AGENTS.md frontend rule, defaulting to Lucide-everywhere is the second-biggest vibecoded tell after Inter-on-purple-gradient. But fully-custom for every UI affordance (chevrons, close-X, search) is over-engineering for a 20-day hackathon.

The split:

- **Tuned Lucide** carries the functional, low-trust UI affordances (chevrons, close, search, copy, download, edit, check, x, info, alert-triangle, arrow-up-right). These are retuned (stroke, optical size, corner radius) at component-import time so they never look like Lucide's default style.
- **Bespoke SVGs** carry the high-trust, brand-visible surfaces — the hero, the workflow stepper, empty-states, success-states, and the status indicators that fire at emotionally-charged moments. These are the "signature recurring elements" the design-brief calls for.

## Tuning rules for Lucide subset

When importing any Lucide icon, the wrapping React component:

1. Sets `strokeWidth={1.5}` (24 px) or `strokeWidth={1.25}` (16 px). Never the default `2`.
2. Sets `strokeLinecap="round"` and `strokeLinejoin="round"`.
3. Sets `size` explicitly — 16 / 20 / 24 / 32 only.
4. Wraps with `aria-hidden="true"` if decorative; `<title>` slot for meaningful icons.
5. Color via `currentColor` so token-driven CSS controls everything.

Any deviation requires a comment justifying the override. Stylelint rule will reject `strokeWidth={2}` on Lucide imports in `.tsx` files.

## Bespoke SVG inventory (8 icons)

Drawn at the size they're used. SVG source committed to `public/icons/` at scaffold time; React components emitted to `src/icons/` from the same source.

| Name | Size | Use | Notes |
|---|---|---|---|
| `denial` | 32 / 24 | hero, empty-state | A folded letter with a single hairline tear; soft, not violent |
| `appeal` | 32 / 24 | workflow stepper, hero | Same letter, unfolded, with a small sage check at the seal |
| `draft-letter` | 24 | drafting surface | Letter outline with three horizontal hairlines for body |
| `deadline` | 24 / 16 | timeline, status-line | Calendar tile with a single sage dot on the date — never an alarm clock |
| `evidence` | 24 | citations panel | Stacked sheets with one peeking out, a hairline rule on each |
| `doctor` | 24 | "ask your doctor" CTA | A paper with a stethoscope curve — abstract, no human figure |
| `insurer` | 24 | "filed with" surface | Building shape with a hairline-rule horizon, no logo grid |
| `signature-dot` | 6 / 8 | active step / status / section markers | The `--accent-sage` 6 px dot — Aegis's recurring signature element |

### Bespoke SVGs to NOT draw (banned)

- ❌ Any human figure with a face — premium-consumer-health archetype rejects stock-figure illustration.
- ❌ Any icon for "AI", "brain", "spark", "magic-wand", "gradient-orb". The product never advertises that it is AI.
- ❌ Sand-timer / hourglass for deadlines — manufactures urgency.
- ❌ Trophy / medal / star for success — celebratory, against design-brief tone.
- ❌ Insurer logos as glyphs — both legal and tonal violation.

## Implementation plan (executes at scaffold time T1.2)

1. SVG sources committed to `public/icons/<name>.svg` (raw, optimisable).
2. React wrapper at `src/icons/<Name>.tsx` for each (typed `IconProps = { size?: 16|20|24|32; className?: string; title?: string }`).
3. Lucide tuning HOC at `src/icons/lucide.tsx` that wraps any Lucide import with the rules above.
4. Storybook page (`src/icons/__icons__.stories.tsx`) showing the full inventory side-by-side with type at the same weight, used as the visual audit per design-tokens-craft handoff.
5. Stylelint rule rejecting `strokeWidth="2"` and raw Lucide imports outside `src/icons/`.

## Audit (when build runs)

- [ ] All icons match the body-type weight (Inter 400/500) — visually verified side-by-side
- [ ] All icons share grid (24/16), stroke (1.5/1.25), corner radius (1.5)
- [ ] No mixing of icon libraries beyond Lucide (no Heroicons, no Tabler, no Feather)
- [ ] Decorative icons have `aria-hidden="true"`; meaningful icons have `<title>` or `aria-label`
- [ ] No default Lucide drop-in present anywhere (lint-enforced)
- [ ] No banned bespoke icon present (design-review skill check)

## Files (deliverable at scaffold)

- `frontend/public/icons/<8 bespoke>.svg`
- `frontend/src/icons/index.ts`
- `frontend/src/icons/lucide.tsx`
- `frontend/src/icons/<Name>.tsx` × 8
- `.design/aegis/ICONS.md` — this file

## Handoff

`frontend-design` Step 6 (Build) — Next.js scaffold (T1.2). The bespoke SVGs are drawn during the build pass; the strategy and inventory above are the contract.
