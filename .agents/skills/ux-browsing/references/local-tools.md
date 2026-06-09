# Local Tools — Building_Apps Shared CLIs

All agents under `C:\Users\reall\Building_Apps\` use these fixed paths. Do not use bare `npx playwright` or `npx shotcap` without a local install.

## shotcap (scroll-aware UX capture)

| Item | Path |
|---|---|
| Package | `C:\Users\reall\Building_Apps\.tools\shotcap\` |
| CMD wrapper | `C:\Users\reall\Building_Apps\shotcap.cmd` |
| PowerShell | `C:\Users\reall\Building_Apps\shotcap.ps1` |
| Binary | `.tools\shotcap\node_modules\.bin\shotcap.cmd` |

```bat
C:\Users\reall\Building_Apps\shotcap.cmd --help
C:\Users\reall\Building_Apps\shotcap.cmd http://localhost:3000 --out .design\feat\screenshots --mobile
```

## playwright-cli (interactive agent browsing)

| Item | Path |
|---|---|
| Package | `C:\Users\reall\Building_Apps\.tools\playwright\` |
| CMD wrapper | `C:\Users\reall\Building_Apps\playwright-cli.cmd` |
| PowerShell | `C:\Users\reall\Building_Apps\playwright-cli.ps1` |

```bat
C:\Users\reall\Building_Apps\playwright-cli.cmd --help
C:\Users\reall\Building_Apps\playwright-cli.cmd open http://localhost:3000
```

## playwright (one-shot screenshot / test runner)

| Item | Path |
|---|---|
| CMD wrapper | `C:\Users\reall\Building_Apps\playwright.cmd` |

Use for quick `screenshot` or `test` subcommands when shotcap matrix is overkill.

## Recovery install

```bat
cd C:\Users\reall\Building_Apps\.tools\shotcap
npm install

cd C:\Users\reall\Building_Apps\.tools\playwright
npm install
npx playwright install chromium
```

Browsers cache to `%LOCALAPPDATA%\ms-playwright\` and are shared across both tools.
