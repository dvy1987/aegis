# Interactive Flow — playwright-cli

Use when capture-only shotcap is insufficient: forms, modals, hover menus, keyboard focus rings, multi-step flows.

## Session hygiene

```bat
playwright-cli.cmd list
playwright-cli.cmd close-all
```

Named session for a feature review:

```bat
set PLAYWRIGHT_CLI_SESSION=aegis-review
playwright-cli.cmd -s=aegis-review open http://localhost:3000/
```

## Core patterns

### Resize + color scheme

```bat
playwright-cli.cmd resize 375 812
playwright-cli.cmd run-code "async page => page.emulateMedia({ colorScheme: 'dark' })"
```

### Snapshot before click (token-efficient refs)

```bat
playwright-cli.cmd snapshot --filename=.design/<feature>/snapshots/step-01.yaml
playwright-cli.cmd click e12
playwright-cli.cmd screenshot --filename=.design/<feature>/screenshots/modal-open.png
```

### Keyboard / focus audit

```bat
playwright-cli.cmd press Tab
playwright-cli.cmd screenshot --filename=.design/<feature>/screenshots/focus-01.png
```

Repeat Tab + screenshot for first 5 focusable elements.

### Console errors during browse

```bat
playwright-cli.cmd console error
```

Copy errors into `AUTOMATED-AUDIT.md` — JS errors are design-review guardrails.

## Visual dashboard

For PM observation during agent work:

```bat
playwright-cli.cmd show
```

Use `--annotate` when collecting structured UI feedback.

## Close

Always close when done:

```bat
playwright-cli.cmd close
```

Or `close-all` if sessions were abandoned.
