# Heuristics — Design Brief

**Purpose:** the single source of truth for design, copy, and UX decisions. Read this before opening Figma, writing a component, or drafting any copy that a user will see.

**Status:** Draft v1 — approved by PM 2026-05-25 (Session 2). Will be refined when the [`frontend-design`](file:///c%3A/Users/reall/Building_Apps/aegis/.agents/skills/frontend-design/SKILL.md) skill chain runs.

---

## 1. Why design matters for Heuristics (the non-negotiable framing)

UX is a **first-class citizen** of this product — not a wrapper around the agent, not a hackathon afterthought. Three reasons:

1. **The hackathon Design criterion** is 1 of 4 top-line judging categories (alongside Technical Implementation, Potential Impact, Quality of Idea). A polished consumer-product UI separates Heuristics from the inevitable wall of dev-tool demos.
2. **The user is stressed.** They just received a denial — for themselves, a parent, a child. They are scared, confused, often financially squeezed. **An AI-shaped product that adds friction or feels cold makes that worse, not better.** Trust collapses on the first screen.
3. **Portfolio.** Heuristics is a portfolio piece. A clickable demo URL will outlive the hackathon. Visitors who scroll past the README and click the link should land on something that looks like a real consumer product, not a prototype.

**Operational implication:** any time a design choice trades polish for speed, the default is *polish*. We push back schedule, not quality. (Per PM directive 2026-05-25.)

---

## 2. Archetype

**Premium consumer health.**

### Reference feels (study these before designing)

- **Headspace** — calm; restrained motion; soft authority; serif-display + clean sans body; muted earth-tone palette with one warm accent
- **Maven Clinic** — warm, modern health product; high-information density done humanely; chunky illustrations balanced with genuine restraint
- **One Medical** — clinical without being cold; lots of white space; high-quality typography hierarchy; "we know what we're doing" confidence without machismo
- **Calm** — masterful use of motion (long durations, soft easing); breath as design metaphor; restraint with color
- **Apple Health** — typography hierarchy as a primary information design tool; restraint as a value
- **Stripe Atlas** (selectively) — for the "this is serious infrastructure but I trust it" feeling on the more administrative screens

### Anti-references (do NOT design like these)

- Classical insurance portals (Aetna.com, Cigna.com) — cold, jargon-heavy, hostile
- Epic / Cerner / enterprise health software — clinical/intimidating
- Typical chatbot UIs ("Hi! I'm your AI assistant 🤖") — destroys trust instantly
- Generic SaaS dashboard look (Tailwind UI defaults / Material-out-of-the-box) — vibecoded tell
- Crypto-bro health-app aesthetics (purple/pink gradients, "leveraging AI" copy) — wrong audience, wrong tone

---

## 3. Tech stack (for designers and engineers)

| Layer | Choice | Why |
|---|---|---|
| Framework | **Next.js** (App Router) | Portfolio-recognizable; ecosystem maturity; SSR for landing page SEO |
| Styling | **Tailwind CSS** + custom design tokens (CSS variables) | Speed + control; tokens prevent default-Tailwind look |
| Component library | **shadcn/ui** (copied into repo, then heavily customized) | Not a dependency — we own the components and tune them |
| Motion | **framer-motion** | Industry standard; supports the calm-easing curves we need |
| Icons | **Lucide React** as base, with **custom-tuned subset** — see §6 | Avoid the "Lucide everywhere" vibecoded tell |
| Typography hosting | self-hosted via next/font (no Google Fonts CDN flash) | Performance + privacy |
| Backend | Python ADK agent exposed via FastAPI | Two Cloud Run services, one frontend, one agent |
| Deployment | Google Cloud Run | Per AGENTS.md stack lock |

### Status of AGENTS.md framework rule

Currently AGENTS.md says: *"Streamlit frontend. Do not switch to Next.js / React — UI is not where this submission wins."* — this rule is **superseded by PM decision 2026-05-25.** AGENTS.md must be updated in the upcoming `project-setup` rewrite to reflect the new stack and the new framing of UX as a first-class pillar.

---

## 4. Tone of voice (the copy non-negotiables)

This product talks to a person who is scared, confused, and possibly furious at their insurer. Every word matters.

### Core voice rules

- **Human, plain-English, dignified.** Reads like a smart friend explaining a hard thing over coffee, not like marketing or a chatbot.
- **No insurance jargon** ("EOB", "PA", "step therapy", "in-network", "out-of-pocket maximum") unless immediately translated in the same sentence.
- **No AI marketing language.** Never say "AI", "intelligent", "powered by GenAI", "I'm an AI assistant", "leveraging Gemini", "let me help you with that today!". The product *is* AI, but the copy never advertises it.
- **No exclamation marks.** None. Not one.
- **No "Awesome!", "Got it!", "Let's go!"** — these read as a chatbot trying to be enthusiastic about a denial letter.
- **No emoji** except in carefully chosen, restrained, intentional cases (a single dot on a status indicator is OK; a 🚀 anywhere is grounds for rewrite).
- **Verb-first sentences. Concrete nouns.** No abstract "experiences" or "journeys" or "solutions".
- **Use "person" instead of "human"** when referring to a reviewer or reader. "Human" reads slightly clinical/AI-ish; "person" reads warmer. (PM directive 2026-05-25.)
- **Use second person ("you", "your")**, not third ("the user", "your patient"). Direct address respects the reader.
- **Don't promise what we can't deliver.** Never say "we'll win your appeal" or "your appeal is guaranteed". Half of all appeals lose. Be honest.
- **Don't manufacture urgency.** No "File now! Time is running out!". The denial deadline is real and on a date the user already knows; if Heuristics surfaces it, surface the date factually, not as pressure.

### Anti-examples (do NOT write these)

- ❌ "Let's get started on your appeal journey! 🚀"
- ❌ "I'm an AI assistant trained on insurance policies to help you appeal denials."
- ❌ "Powered by Gemini 3 and Google ADK."
- ❌ "Awesome! I've drafted your appeal in seconds."
- ❌ "You're not alone in your healthcare journey."
- ❌ "Leveraging artificial intelligence to fight back."
- ❌ "Empowering patients to take control."

### Examples (yes write these)

- ✓ "A denial isn't a final answer. Most appeals win."
- ✓ "Tell us what happened. We'll draft the appeal."
- ✓ "This is a draft. A person should read it before you file."
- ✓ "You're filing on your own behalf. We can make this easier — we can't make this go away."
- ✓ "Filing an appeal takes about thirty minutes. Most people we've helped finish in one sitting."
- ✓ "You have until [date] to file. That's [N] days."
- ✓ "We don't store your medical records. The draft lives only on this device."

### Copy patterns for common surfaces

**Error states:** "Something's not working on our side. Try again, or come back later — your progress is saved."
*(Never: "Oops! 😅 Something went wrong! Click here to retry!")*

**Empty states:** "No appeals yet. When you start one, it'll show here."
*(Never: "It's a little quiet around here…")*

**Success states:** Acknowledge, don't celebrate. "Your appeal is saved as a draft."
*(Never: "🎉 Amazing! Appeal drafted!")*

**Loading states:** Specific, calm. "Reading your denial letter…" → "Drafting your appeal…" → "Almost done."
*(Never: spinners with no context, never "Please wait…")*

---

## 5. Emotional arc the user moves through

The user shouldn't think about steps. They should feel a single forward motion. Internally though, design for this arc:

1. **Land — calm.** Hero copy that names the problem without dramatizing it. No marketing, no promises. A single quiet call to action.
2. **Begin — small.** Ask one question at a time. Each question is short and doable. Show progress without making it feel like a form.
3. **Understand — clarified.** As the user shares the denial, the product mirrors back what it heard in plain English. Reduces the swirl in their head.
4. **Draft — produced.** A real, readable appeal letter appears. Written like a person, not a template. They can see and edit every sentence.
5. **Decide — in-control.** The user chooses to download, edit, share with a doctor, or come back later. No pressure to file inside the product. (Crucially: Heuristics does NOT file with insurers — that's a scope hard rule and also a trust feature.)
6. **Leave — better.** Even if they don't file today, they leave with: a draft, a deadline, a sense that this is possible.

---

## 6. Iconography

**The problem:** every AI-generated UI uses the same 24px stroke-1.5 outline Lucide icons. It is the second-biggest vibecoded tell after Inter-on-purple-gradient (per [`icon-craft`](file:///c%3A/Users/reall/Building_Apps/aegis/.agents/skills/icon-craft/SKILL.md) skill brief).

**The plan:**
- Use Lucide as the base set (good coverage, reasonable defaults).
- **Tune the entire used subset**: standardize on a single optical size, a single stroke weight that matches our typography weight, a single corner-radius rule.
- Replace ~6–10 critical icons with custom SVGs designed specifically for Heuristics (denial, appeal, draft letter, deadline, evidence, doctor, insurer, win, lose). These appear in the hero, the workflow steps, and the empty/success states — the highest-trust surfaces.
- Never use the Lucide raw on a hero or call-to-action.

Defer detailed icon-system spec to a `frontend-design` → `icon-craft` skill run.

---

## 7. Motion principles (framer-motion)

- **Long durations, soft easing.** Default transition: 400ms, `easeOut` or custom cubic-bezier `cubic-bezier(0.2, 0.8, 0.2, 1)`. Calm, not snappy.
- **Motion serves comprehension, not decoration.** Use it to explain that something appeared/loaded/moved — never to perform.
- **Page transitions:** crossfade with slight upward translate (8–12px). No slides, no fancy 3D.
- **Microinteractions:** subtle. A button that confirms-tap with a 1-frame scale-down (0.97 → 1) is enough.
- **Loading:** prefer text-based progress ("Reading…" → "Drafting…") over spinners. If a spinner is needed, it's slow and almost meditative — not a frantic dotted circle.
- **Reduce-motion respect:** all motion must honor `prefers-reduced-motion: reduce`. Accessibility, not optional.

---

## 8. What must NOT be in the product

A hard checklist that designers, copywriters, and reviewers can use as a veto list.

- ❌ "We'll win your appeal" / any guarantee language (legal + tonal violation)
- ❌ "AI assistant" / "AI-powered" / chatbot framing
- ❌ Medical or legal advice claims
- ❌ PHI input fields without explicit consent friction + plain-English explanation of where data goes
- ❌ Urgency manipulation ("Only 2 days left!" with flashing red — even if the deadline is real, deliver factually)
- ❌ Dark patterns: pre-checked boxes, hidden costs (there are no costs), grayed-out cancel buttons
- ❌ Tracking / analytics beyond the minimum strictly necessary for product function (consider: do we even need GA? probably not.)
- ❌ Marketing for paid tiers or features that don't exist (this is open source; there are no paid tiers in scope)
- ❌ Branded references to Gemini, ADK, Phoenix, Google in user-facing UI (these belong in the README and Devpost, not the product surface)
- ❌ Stock photos of multi-ethnic smiling people in hospital corridors (do not use; if illustration is needed, commission custom or use abstract)
- ❌ The phrase "your insurance journey"
- ❌ Any invocation of acts of violence, vigilantism, or polarizing public events around the insurance industry — in copy, illustration, demo, or marketing. The product earns trust by being constructive, not by riding cultural anger. If the impact narrative needs scale, source it from primary research (KFF, Commonwealth Fund, JAMA, Senate report) and present it factually.

---

## 9. Accessibility floor (non-negotiable)

- WCAG 2.2 AA color contrast minimum (4.5:1 for body text; 3:1 for large)
- Full keyboard navigation; visible focus states on every interactive element
- Screen-reader-correct landmarks; every form input has a proper `<label>`
- `prefers-reduced-motion: reduce` honored throughout
- Mobile-first responsive (the user might be reading this on their phone after a doctor's visit)
- Plain-language reading level ~grade 8 (Flesch reading ease ≥ 60)

---

## 10. Scope of this brief

This brief covers **strategy, tone, and constraints**. It does NOT yet specify:

- ❌ Design tokens (colors, typography scale, spacing, radius, motion curves as values) — owned by `design-tokens-craft` skill
- ❌ Component-level layouts and patterns — owned by `frontend-design` skill
- ❌ Specific page wireframes — to be drafted during build Day 1–3
- ❌ Final icon set — owned by `icon-craft` skill

When those artifacts are produced, link them here so this brief is the navigation root.

---

## 11. Update log

| Date | Author | Change |
|---|---|---|
| 2026-05-25 | Session 2 (Amp + PM) | Initial draft; archetype + tone + framework decision (Next.js) approved by PM |
