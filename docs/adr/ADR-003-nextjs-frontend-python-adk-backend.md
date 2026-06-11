# ADR-003: Next.js frontend + Python ADK backend (two Cloud Run services)

**Date:** 2026-05-25 (Session 2 decision; ADR backfilled 2026-05-27)
**Status:** Accepted (supersedes Session 1 Streamlit lock-in)
**Mode:** CONTEMPORANEOUS to Session 2.

## Context

Session 1 of the build (2026-05-24) locked the frontend as **Streamlit-only** on the grounds that "UI is not where this submission wins." Session 2 (2026-05-25) reversed this decision after:
1. **Pre-mortem analysis** flagged Cause M (UX too dev-toolish) at impact × blindness score 25 — tied for top risk.
2. **Arize hackathon rubric re-read** confirmed Design is 1 of 4 hackathon-wide judging categories — not optional polish.
3. **PM directive** elevated UX to a first-class product pillar co-equal with the Phoenix MCP self-improvement story and the impact narrative ("UX is a first class citizen of this product").
4. **Trust framing** — the product user (a person navigating a real denial) is stressed and scared; an AI-feeling product breaks trust on the first screen.

Streamlit cannot deliver consumer-grade UX, mobile responsiveness, or the calm motion-design required by the design brief archetype (Headspace · Maven Clinic · One Medical · Calm · Apple Health).

## Decision

**Build the user-facing product as a Next.js (App Router) frontend backed by a Python FastAPI service that hosts the Google ADK agent. Two services on Google Cloud Run.**

Frontend stack:
- Next.js (App Router) for SSR + recognizable portfolio framework
- Tailwind CSS + custom CSS variables (design tokens, not raw Tailwind defaults)
- shadcn/ui — **copied into the repo and customized**, not imported as a dependency (we own the components)
- framer-motion — long durations, soft easing (`cubic-bezier(0.2, 0.8, 0.2, 1)`, 400ms default)
- Lucide React (tuned subset) + ~6–10 bespoke SVG icons
- Self-hosted fonts via `next/font`

Backend stack:
- Python 3.11 + `uv`
- FastAPI as the only public surface the frontend calls
- Google ADK as agent framework (see [ADR-001](ADR-001-google-adk-agent-framework.md))
- `google-agents-cli` for dev lifecycle (see [ADR-005](ADR-005-google-agents-cli-dev-workflow.md))

Deployment: two independent Cloud Run services in `us-central1`.

## Alternatives Considered

- **Streamlit + heavy theming + static landing page (Astro):** the Session 1 default. Rejected: Streamlit's UX ceiling is real; visitors who go past the landing page feel the seam; mobile experience is weak; cannot deliver the calm motion / typography hierarchy / micro-interactions required by the design brief.
- **Hybrid landing page (Astro) + Streamlit workflow:** lower-effort path. Rejected: introduces two frameworks for the same product, doubles maintenance, and the workflow page still feels like Streamlit (the part judges spend the most time on).
- **Gradio + Astro landing:** similar issue to Streamlit option — Gradio cannot deliver consumer-product feel.
- **All-Streamlit with extreme custom CSS:** rejected; fighting Streamlit's component model is more work than building Next.js.
- **Single-service architecture (FastAPI + server-rendered HTML):** lower DevOps complexity. Rejected: portfolio-grade UX needs a real frontend stack; Next.js + Tailwind + framer-motion is the modern path.

## Consequences

- ✓ Consumer-grade UX is achievable; design brief archetype (premium consumer health) is reachable.
- ✓ Mobile-responsive by default.
- ✓ Portfolio-recognizable stack (Next.js / Tailwind / shadcn) — PM portfolio value preserved.
- ✓ framer-motion enables the calm motion language the design brief requires (long durations, soft easing, reduce-motion compliance).
- ✓ Two-service architecture matches the AGENTS.md multi-file scope (`frontend/AGENTS.md` + `backend/AGENTS.md` separation).
- ⚠ **Adds 3–5 build days vs Streamlit baseline.** The 20-day build plan absorbs this; the 5 critical assumption tests in Days 1–10 mitigate downstream risk.
- ⚠ **Two-service Cloud Run deploy** — slight operational complexity (CORS, env propagation, two deploy commands). Mitigation: `google-agents-cli deploy` handles backend; custom script for frontend; deploy scripts in `scripts/`.
- ⚠ **Two AGENTS.md files** — needs sync hygiene. Both reference root for project-wide rules.
- ⚠ **No live-on-Cloud-Run-from-day-1.** Need to budget a day-1 verification that both services boot, talk to each other, and CORS works before any agent-coding begins.
- ⚠ Reverses an earlier locked decision — old AGENTS.md text *"Streamlit frontend. Do not switch to Next.js / React"* is explicitly retracted as of Session 3 (this ADR + the new root AGENTS.md).

## Revisit triggers

- If Day 7 MVP is more than 3 days behind because frontend complexity is the bottleneck, escalate to PM with options (per Code-Wall Escalation Protocol). Do NOT unilaterally fall back to Streamlit.
- If a Next.js-on-Cloud-Run blocker persists >2 days, reopen.
- Post-hackathon: if Heuristics becomes a long-term product and SSR cost / framework choice becomes critical, re-evaluate.

## References

- Session 2 decision in [docs/memory/decision-log.md](../memory/decision-log.md) (2026-05-25 entry "Frontend framework: Next.js + Python ADK backend")
- [docs/design-brief.md](../design-brief.md) — archetype, voice rules, motion, accessibility floor
- Pre-mortem session 2 — top risk Cause M
- Arize hackathon brief — Design as 1 of 4 hackathon-wide criteria
- PM directive 2026-05-25: "UX is a first class citizen of this product"
