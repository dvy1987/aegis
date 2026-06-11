# Tokens for Heuristics

**Archetype:** premium-consumer (health-shaded)
**Recipe basis:** premium-consumer (warm-paper variant) + Headspace/Calm motion budget
**Source files:** [`tokens.css`](./tokens.css), [`tokens.ts`](./tokens.ts)

These tokens will be copied into `frontend/src/styles/tokens.css` and `frontend/src/styles/tokens.ts` when the Next.js app is scaffolded (T1.2). They are checked in here first so the scaffold doesn't ship with Tailwind defaults baked in for even one commit.

---

## Color rationale

The neutral scale is **warm parchment**, not cool grey. Pure white is reserved only for raised cards (`--surface-secondary`); the page background is `#F8F5EE`-equivalent (`oklch(96% 0.015 85)`). This is the move that immediately separates Heuristics from generic SaaS — Tailwind's `slate`/`zinc`/`gray` are dead-giveaway tells, and pure white reads as cheap on a phone screen in a hospital lobby.

The accent system is **one** functional accent (`--accent-sage`, ~`#3F6A55`) and **one** warning (`--accent-clay`, ~`#A65A3F`). No brand palette of three. Sage carries authority without being clinical-blue or AI-purple. Clay shows up only on hard-deadline warnings — never decoratively. Status colors deliberately reuse the accent scale (success = sage, warning = clay) so the surface never feels like a Bootstrap admin.

`oklch()` is used as the source of truth for perceptual lightness consistency across the scale and for clean dark-mode hand-tuning.

## Typography rationale

The pairing is **Source Serif 4 (display) + Inter (body)**. The serif IS the brand voice — it carries the "we know what we're doing" authority that the design-brief calls for, in the lineage of Headspace / Apple Health / NYT. Inter is the body horse for paragraph and UI chrome work; it's neutral enough to let the serif speak.

This is the inverse of the Inter-everywhere vibecoded tell. Source Serif 4 is open-source (SIL OFL), self-hosted via `next/font` per AGENTS.md, no Google Fonts CDN flash. JetBrains Mono appears only on case numbers, dates, and claim IDs — never on body text or UI chrome.

The display scale (24 → 72px) is mobile-first; the 72px hero only fires at desktop breakpoints. Tracking is tightened (`-0.02em`) on display sizes, which the serif rewards.

## Motion rationale

Default duration is **400ms** with the **`cubic-bezier(0.2, 0.8, 0.2, 1)`** "Calm" easing curve. This is consciously slow for an AI product — most AI UIs feel snappy/twitchy at 120-180ms. We breathe instead. The duration budget (`--duration-quick` 240ms → `--duration-emphasized` 520ms) is the same range Calm and Headspace use, validated in their app stores. No motion under 180ms ships; no motion over 600ms either.

`prefers-reduced-motion: reduce` collapses every duration to 1ms — effectively no animation, just state change. Accessibility floor, not optional.

## Adaptations from the standard premium-consumer recipe

- **Health-shaded neutrals.** Recipe says off-white / warm dark; we cooled the warm dark slightly (oklch hue ~55–60) so it reads "clinical-without-cold" rather than "cozy".
- **Sage accent instead of jewel-tone.** Recipe says "saturated jewel tone"; we picked sage because the audience is stressed and ANY high-saturation color reads as urgency-manipulation here.
- **No three-color brand palette.** Pure premium-consumer often gets one accent + a secondary; we're stricter. One sage, one clay, neutrals. Status colors reuse those.
- **Tighter density on downstream surfaces.** Hero stays generous (premium-consumer move); the appeal-drafting flow trades whitespace for legibility because users will actually be reading on a phone in a high-cortisol moment.
- **`oklch` over `hsl`.** Better perceptual lightness control for a design system that lives or dies on tonal consistency.

## Banned defaults checked

- ✓ No `slate` / `zinc` / `gray` Tailwind base palette
- ✓ No Inter-only — Source Serif 4 carries display
- ✓ No purple → pink gradient anywhere
- ✓ No 9-step gray dump named gray-50 … gray-950 (we use a 10-step warm `--ink` scale, named for role not value)
- ✓ No `#000` or `#FFF` (pure black/white) anywhere
- ✓ No electric blue / electric purple
- ✓ No three-color brand palette
- ✓ No theatrical motion (durations stay 240–520ms; easing is calm)
- ✓ No box-shadow elevation as default; hairlines preferred
- ✓ Dark mode is hand-set, not auto-inverted

## Files

- [`./tokens.css`](./tokens.css) — CSS custom properties (`:root` + `[data-theme="dark"]`)
- [`./tokens.ts`](./tokens.ts) — typed JS exports for motion + spatial constants
- This file — rationale + audit

## Lint enforcement (to add at scaffold time)

When the Next.js app is scaffolded, the Tailwind config will:

1. Pull `--ink-*`, `--accent-*`, `--surface-*`, `--text-*`, `--border-*` directly from `tokens.css` via Tailwind v4 `@theme` directive.
2. Disable Tailwind's default color palette (`slate`, `zinc`, etc.) so they cannot be referenced from class names without a deliberate override.
3. Disable Tailwind's default font stacks; replace with `--font-display` / `--font-body` / `--font-mono`.
4. Add a Stylelint rule rejecting raw hex values in `*.tsx` / `*.css` files outside `tokens.css`.

## Handoff

Next: `icon-craft` consumes archetype + tokens to produce the icon strategy (Step 5 of `frontend-design`).
