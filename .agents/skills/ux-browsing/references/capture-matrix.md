# Capture Matrix

Required shots before `design-review`. Filename pattern:

`.design/<feature>/screenshots/<route>--<viewport>--<mode>--*.png`

## Minimum matrix (always)

| Viewport | Mode | shotcap flags |
|---|---|---|
| 375×812 | light | `--mobile` |
| 375×812 | dark | `--mobile --dark` |
| 1280×800 | light | `--width 1280 --height 800` |
| 1280×800 | dark | `--width 1280 --height 800 --dark` |

## Extended matrix (dashboard, marketing, multi-page)

| Viewport | Mode | When |
|---|---|---|
| 768×1024 | light | tablet layout check |
| 1920×1080 | light | wide marketing hero |
| any | light + `--full-page` | landing pages with below-fold story |

## Per-route naming

| Route | `--name` prefix |
|---|---|
| `/` | `home` |
| `/pricing` | `pricing` |
| `/app` | `app` |

Use URL path slug for other routes: `/settings/billing` → `settings-billing`.

## Timing defaults

| Archetype | `--settle` | `--scroll-wait` |
|---|---|---|
| Static / docs | 1500 | 800 |
| SaaS / dashboard | 2500 | 1200 |
| Marketing / motion-heavy | 3500 | 1400 |

## Reduced-motion pass (optional)

After standard captures, one desktop light pass with playwright-cli:

```bat
playwright-cli.cmd open http://localhost:3000/
playwright-cli.cmd run-code "async page => { await page.emulateMedia({ reducedMotion: 'reduce' }); await page.reload(); }"
playwright-cli.cmd screenshot --filename=.design/<feature>/screenshots/home--1280x800--light--reduced-motion.png
playwright-cli.cmd close
```

Record results in `AUTOMATED-AUDIT.md` under Reduced-motion.
