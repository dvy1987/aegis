# Archetype: premium-consumer (health-shaded)

**Feels like:** One Medical × Headspace, with Calm's motion budget and Apple Health's typographic restraint.
**Why this archetype:** Heuristics talks to a person in distress about a stressful, jargon-heavy event. Premium-consumer is the only archetype that buys both authority and warmth without slipping into clinical/enterprise coldness or chatbot delight. Health-shaded means cooler-leaning paper neutrals, a single grounded accent, and motion that breathes rather than performs.

## Typography
- Display: **Source Serif 4** (or Tiempos / GT Sectra fallback), 600 weight, 32 / 44 / 56 / 72 px. Tight tracking on display sizes (-0.02em). The serif carries authority — this is the "we know what we're doing" voice.
- Body: **Inter** (next/font, self-hosted) at 16–18 px / line-height 1.55. Used for paragraphs, form fields, and UI chrome.
- Small / metadata: 13–14 px, 0.01em tracking, `--text-muted` color.
- Mono (rare, only for case numbers, dates, claim IDs): **JetBrains Mono** at 13–14 px.
- Pairing rationale: Two families, used confidently. The serif speaks; the sans listens. This is the Headspace / Apple Health move and is the inverse of the Inter-everywhere vibecoded tell.

## Color
- **Background story (light):** warm paper, NEVER pure white. Surface = `#F8F5EE` (warm parchment), with `#FFFFFF` reserved for raised cards. Borders are 1px hairlines at ~6% black, not grey panels.
- **Background story (dark):** warm dark, NEVER cool slate. Surface = `#15161A` with `#1B1D22` for raised cards. Avoids the "VS Code" feeling.
- **Foreground:** off-black `#1A1A1A` (light) / off-white `#EDE7DA` (dark). Never pure `#000` or `#FFF`.
- **Accent strategy:** ONE accent — **`--accent-sage` `#3F6A55`** (a grounded, confidence-bearing green-grey, evoking medicinal calm). Used only on primary actions, the signature dot/hairline, and the active-state in the workflow stepper. A second muted **`--accent-clay` `#A65A3F`** appears ONLY on warnings and hard-deadline countdowns — never decoratively.
- **Neutral scale:** 9 stops from parchment to ink, named `--ink-0` … `--ink-9`. Tailwind defaults (`slate`, `zinc`, `gray`) are forbidden and will be enforced via lint.
- **Anti-defaults (banned in this build):** purple, pink, electric blue, any hex starting with `#7C3AED` / `#EC4899` / `#3B82F6` (Tailwind primary defaults), pure-white surfaces, pure-black text, gradient hero backgrounds, three-color brand palettes, "trust blue" generic insurance navy.

## Motion
- **Duration budget:** 240–520ms. Default 400ms. No animation under 180ms (which reads snappy/AI). No animation over 600ms unless it's a deliberate page-fade.
- **Easing curve:** `cubic-bezier(0.2, 0.8, 0.2, 1)` (Calm-style, our project default), and `cubic-bezier(0.32, 0.72, 0, 1)` (Apple-style) for press-down microinteractions.
- **Character:** restrained, breathing, weighty. Motion is the product saying "I heard you" — not "look at me".
- **Page transitions:** crossfade + 8–12px upward translate. No slides. No 3D.
- **Microinteractions:** button press = 0.97 scale 1 frame, returning at 240ms ease-out. Hover lifts use shadow + 1px translateY only.
- **Loading:** prefer text-progress ("Reading your denial…" → "Drafting…" → "Almost done."). If a spinner is unavoidable, it is a slow 1.6s rotation, hairline, almost meditative.
- **`prefers-reduced-motion: reduce`** is honored everywhere. No exceptions.

## Density
**Generous.** Hero takes 75–80vh with one headline and minimal furniture. Reading column maxes at 64ch. Form fields use 56px tap targets. Whitespace is doing real work — anxiety-reduction work.

## Icon stance
**Mixed:** **tuned Lucide** as the base set + **6–10 bespoke SVGs** for the high-trust surfaces (denial, appeal, draft letter, deadline, evidence, doctor, insurer, status indicators). Per design-brief §6 and `icon-craft` skill.
- Stroke weight: 1.5px on 24px optical size; 1.25px on 16px.
- Corner radius: 1.5px on stroke caps and joins.
- Color: never the accent — icons are `--ink-7` until interactive.
- The bespoke set lives on the hero, the workflow stepper, empty/success states, and is the Heuristics "signature recurring element" (per design-brief).

## Layout signatures
- **Type-only hero.** No illustration, no product video. A single calm sentence in serif display, a one-line subhead in body sans, one quiet primary CTA. Asymmetric — text aligned at the optical-left of a 12-col grid, breathing top.
- **Hairline rules** (1px at ~6% black) instead of card chrome wherever possible. Sectioning by air, not by box.
- **Single-column reading flow** for the appeal-drafting surface. No sidebar. Progress is shown at the top as a thin progress hairline, not a stepper component with numbered circles.
- **A signature dot** (`--accent-sage`, 6px) marks the active step — recurs across stepper, status indicators, draft section markers.
- **Edge-to-edge full-bleed** photography or muted illustration ONLY when used; we will probably ship without imagery for v1 and let typography carry the weight.

## Reference sites (visit these before building)
1. **headspace.com** — serif/sans pairing, calm motion, single-accent restraint, stress-aware copy tone.
2. **onemedical.com** — paper neutrals, hairline rules, "clinical without cold", form-field treatment, generous whitespace.
3. **calm.com** — motion duration, easing curves, the "breathing" pacing of micro-animations.
4. **apple.com/health** — type-only hero, typography hierarchy as primary information design tool.
5. **maven.com** (Maven Clinic) — warm health authority, photography-meets-illustration restraint.

## Adaptations for Heuristics (specific to this product)
- **Stress-aware density.** Slightly tighter than pure premium-consumer — a person on a phone in a hospital lobby needs to see content sooner. Hero remains generous; downstream surfaces (appeal-drafting flow) trade some whitespace for legible information.
- **Dignified, not delightful.** Premium-consumer often shades into "joy". Heuristics cannot. No celebratory micro-animations on success. Acknowledgement, not confetti.
- **Authority via typography, not chrome.** No "trust badges", no insurer logos as social proof, no rating stars. The serif display + paper background do the credibility work.
- **Mobile-first.** Most users land on a phone after a doctor's visit. All layouts are designed mobile-first; desktop is the second pass.
- **Accessibility floor is the design floor.** WCAG 2.2 AA minimum on all token combinations — verified at token-generation time, not retroactively.

## Anti-patterns (do NOT do these even if instinct says to)
- ❌ Inter-on-everything. The serif display IS the brand voice; do not let the body type swallow it.
- ❌ Purple, pink, electric-blue, or any "AI-product" color cue. We are not advertising the AI.
- ❌ Card grids of features with icons (b2b-productivity move). Sectioning is by air and hairlines.
- ❌ Stock illustrations of multi-ethnic smiling people in hospital corridors (per design-brief §8 veto list).
- ❌ Chatbot bubbles, "AI assistant" framing, sparkle icons, sparkle gradients.
- ❌ Three-color brand palette. One sage accent + one clay warning. That's it.
- ❌ Numbered-circle steppers, progress percentages, "X% complete" gamification. Use a hairline progress rule.
- ❌ Theatrical motion. No bouncing CTAs, no parallax-on-scroll, no marquee-text. Everything breathes.
- ❌ Pre-built shadcn defaults dropped in unmodified — every shadcn component must be customised against these tokens before it ships.
- ❌ Tailwind default palette names in source (`bg-slate-900`, `text-zinc-500`). Tokens only.

---

**Handoff:** `design-tokens-craft` consumes this file as Step 4 of the `frontend-design` orchestrator.
