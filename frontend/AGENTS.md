# Frontend — Agent Rules

See root [AGENTS.md](../AGENTS.md) for project-wide context, PM working-agreement, safety/tone rules, and the Orchestration Map. This file is **frontend-specific** only.

## What lives here

Next.js (App Router) consumer-facing web app. Connects to the Python ADK backend over HTTP. Deployed as its own Cloud Run service.

## Source of truth for design + copy

**[docs/design-brief.md](../docs/design-brief.md) is non-negotiable.** Read it before opening a component file, writing a string of copy, or picking a color. Specifically:
- Archetype: premium consumer health (Headspace · Maven Clinic · One Medical · Calm · Apple Health). NOT classical insurance portals, enterprise health software, chatbot UIs, generic SaaS dashboards.
- Voice rules in design-brief §4 are hard rules — no "AI assistant" framing, no exclamation marks, no chatbot enthusiasm, no insurance jargon without translation, "person" not "human", no manufactured urgency.
- Anti-pattern list in design-brief §8 is a veto list — if you see one of those in a PR, block.

## Stack

| Layer | Tool | Note |
|---|---|---|
| Framework | Next.js (App Router) | SSR for landing page SEO |
| Styling | Tailwind CSS + custom CSS variables | Custom tokens, not raw Tailwind defaults |
| Components | shadcn/ui | **Copied into repo and customized, NOT installed as a dependency.** We own the components. |
| Motion | framer-motion | Long durations, soft easing (`cubic-bezier(0.2, 0.8, 0.2, 1)`, 400ms default) |
| Icons | Lucide React (tuned subset) + ~6–10 bespoke SVGs | Avoid the "Lucide everywhere" vibecoded look |
| Fonts | self-hosted via `next/font` | No Google Fonts CDN flash |
| Deployment | Google Cloud Run | Min instances = 1 during demo period |

## Non-obvious patterns

- **shadcn is copied, not imported.** When you add a shadcn component, copy the source into `src/components/ui/` and customize the tokens. Never `npm install` it.
- **Design tokens are CSS variables.** All colors, type scale, spacing, radius, motion curves live as CSS custom properties — generated/audited by the `design-tokens-craft` skill. Never hardcode hex values in components.
- **Motion respects `prefers-reduced-motion: reduce`.** Always. No exceptions.
- **No tracking / analytics** beyond the bare minimum needed for the product to function. Consider whether you need GA at all — probably not.
- **No Gemini / Phoenix / ADK branding in user-facing UI.** Those belong in README and Devpost, not the product surface.

## Code style

- TypeScript strict mode.
- Server Components by default; mark Client Components explicitly with `'use client'`.
- Co-locate component + styles; one component per file.
- Accessibility floor: WCAG 2.2 AA contrast, full keyboard nav, visible focus states, `<label>` on every input, semantic landmarks.

## Boundaries

- **Ask first:** new dependencies, design system changes, new pages, new color/typography tokens, copy on user-facing surfaces.
- **Full autonomy:** test writing, internal refactors, lint/format fixes, behaviour-preserving cleanups.
- **Never:** AI-marketing copy, urgency-manipulation patterns, dark patterns, stock photos of multi-ethnic smiling people in hospital corridors, the phrase "your insurance journey".

## Skills most relevant here

`frontend-design` (orchestrator) · `design-archetype` · `design-tokens-craft` · `icon-craft` · `design-review` · `test-driven-development` · `code-review-crsp`.
