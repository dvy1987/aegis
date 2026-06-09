---
name: ux-browsing
description: >
  Browse live UIs and capture design-grade screenshots for UX review using
  shared local tools (shotcap, playwright-cli). Load when the user asks to
  browse a site, capture UI screenshots, scroll-capture a page, explore a
  live preview for design feedback, audit a running frontend visually, run
  design capture, shotcap a URL, or when frontend-design / design-review
  need automated multi-viewport captures. Sub-skill of frontend-design;
  hands off to design-review.
license: MIT
metadata:
  author: dvy1987
  version: "1.0"
  category: project-specific
  resources:
    references:
      - local-tools.md
      - capture-matrix.md
      - interactive-flow.md
      - audit-handoff.md
---

# UX Browsing

You are the UX Browser. You explore live pages with token-efficient CLI tools, capture scroll-aware screenshots for design review, and extract lightweight DOM audits — without dumping page trees into the model context.

## Hard Rules

- **Local tools first.** Use shared Building_Apps CLIs at fixed paths (read `references/local-tools.md`). Never rely on bare `npx` without a local `node_modules`.
- **Screenshots to disk, not context.** Save PNGs under `.design/<feature>/screenshots/`. Read images only when the user asks for visual critique of a specific shot.
- **Capture matrix is mandatory** for design-review handoffs. Minimum: mobile light, desktop light, desktop dark. Read `references/capture-matrix.md`.
- **Wait for settle.** Scroll reveals and hero animations need settle time. Do not screenshot on first paint.
- **No PHI, no production patient data.** Synthetic demos, localhost, or approved staging URLs only.
- **Hand off structured output.** Write `CAPTURE-MANIFEST.md` + per-shot `manifest.json` files. Never end with loose PNGs and no audit trail.

---

## Workflow

### Step 1 — Confirm Target

Collect:
1. URL (localhost dev server, preview deploy, or approved staging)
2. Feature slug (maps to `.design/<feature>/`)
3. Routes to capture (default: `/` only)
4. Mode: **capture-only** (shotcap) or **interactive** (playwright-cli)

If dev server is required and not running, start it or ask the user once.

### Step 2 — Verify Local Tools

Read `references/local-tools.md`. Run version checks:

```bat
C:\Users\reall\Building_Apps\shotcap.cmd --help
C:\Users\reall\Building_Apps\playwright-cli.cmd --help
```

If either fails, install from that file's recovery section before continuing.

### Step 3 — Run Capture Matrix

For each route × viewport × color mode in `references/capture-matrix.md`, run shotcap:

```bat
C:\Users\reall\Building_Apps\shotcap.cmd http://localhost:3000/ ^
  --out .design\<feature>\screenshots ^
  --name home--375x812--light --mobile --settle 2500

C:\Users\reall\Building_Apps\shotcap.cmd http://localhost:3000/ ^
  --out .design\<feature>\screenshots ^
  --name home--1280x800--light --width 1280 --height 800

C:\Users\reall\Building_Apps\shotcap.cmd http://localhost:3000/ ^
  --out .design\<feature>\screenshots ^
  --name home--1280x800--dark --width 1280 --height 800 --dark
```

Add `--full-page` for marketing/landing archetypes. Use `--headed` only when debugging capture failures.

### Step 4 — Interactive Pass (when needed)

For flows, forms, hover states, or keyboard focus, read `references/interactive-flow.md` and use playwright-cli. Prefer snapshots + element refs over pasting DOM.

Typical sequence:

```bat
C:\Users\reall\Building_Apps\playwright-cli.cmd open http://localhost:3000 --headed
C:\Users\reall\Building_Apps\playwright-cli.cmd resize 1280 800
C:\Users\reall\Building_Apps\playwright-cli.cmd snapshot --filename=.design\<feature>\snapshots\home.yaml
C:\Users\reall\Building_Apps\playwright-cli.cmd screenshot --filename=.design\<feature>\screenshots\home--interactive.png
C:\Users\reall\Building_Apps\playwright-cli.cmd close
```

Use `-s=<name>` for multi-route sessions. Run `playwright-cli show` if the user wants to watch agent browsing.

### Step 5 — Merge Audits

Each shotcap run writes `<prefix>--manifest.json` with fonts, headings, contrast sample, meta tags. Read `references/audit-handoff.md` and write:

- `.design/<feature>/CAPTURE-MANIFEST.md` — human summary
- `.design/<feature>/AUTOMATED-AUDIT.md` — machine-readable feed for design-review

### Step 6 — Hand Off

Route to `design-review` with:
- Screenshots directory
- `AUTOMATED-AUDIT.md`
- Note any capture gaps (failed route, timeout, missing dark mode)

---

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "One hero screenshot is enough" | Scroll reveals and mobile breakpoints hide most drift. Run the matrix. |
| "I'll paste the DOM" | DOM in context burns tokens and misses computed styles. Use manifest JSON. |
| "Playwright MCP is easier" | MCP loads heavy trees. CLI + shotcap is the default on this machine. |
| "networkidle is too slow" | Use `--wait-until load` for SPAs, but keep `--settle` ≥2000ms for motion. |
| "Skip dark mode" | Dark mode is a hard gate for design-review. Capture it. |

---

## Verification

- [ ] `shotcap.cmd --help` and `playwright-cli.cmd --help` succeed from project root
- [ ] At least 3 matrix cells captured (mobile light, desktop light, desktop dark)
- [ ] Every capture has a matching `--manifest.json`
- [ ] `CAPTURE-MANIFEST.md` lists all shots with viewport + mode
- [ ] `AUTOMATED-AUDIT.md` written for design-review consumption

---

## Output Format (CAPTURE-MANIFEST.md)

```markdown
# Capture manifest — [feature]

Captured: [ISO timestamp]
Base URL: [url]

## Matrix completed
| Route | Viewport | Mode | Shots | Manifest |
|---|---|---|---|---|
| / | 375×812 | light | 5 | home--375x812--light--manifest.json |

## Gaps
- [none | list]

## Handoff
Ready for design-review: [yes/no]
```

---

## Reference Files

- **`references/local-tools.md`** — fixed paths, wrappers, install recovery
- **`references/capture-matrix.md`** — required viewport × mode grid
- **`references/interactive-flow.md`** — playwright-cli patterns for flows and focus
- **`references/audit-handoff.md`** — merge shotcap manifests into AUTOMATED-AUDIT.md

---

## Impact Report

```
UX browse complete: [feature]
Routes: [count]
Matrix cells: [completed/required]
Tool: shotcap + playwright-cli
Manifest: .design/<feature>/CAPTURE-MANIFEST.md
Audit: .design/<feature>/AUTOMATED-AUDIT.md
Handoff: design-review
```
