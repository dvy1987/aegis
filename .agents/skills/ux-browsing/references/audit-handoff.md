# Audit Handoff — shotcap → design-review

Merge per-capture `*--manifest.json` files into `.design/<feature>/AUTOMATED-AUDIT.md`.

## Read manifests

Each shotcap manifest contains:

- `audit.fonts` — computed body/display font families
- `audit.headings` — h1–h6 sequence
- `audit.contrast.bodyOnBg` — sample contrast ratio
- `audit.meta.viewport` / `themeColor`
- `console` — page errors (first 20)

## AUTOMATED-AUDIT.md template

```markdown
# Automated audit — [feature]

Source: ux-browsing / shotcap
Captured: [timestamp]

## Routes captured
- / → [N] screenshots (375 light, 375 dark, 1280 light, 1280 dark)

## Computed contrast (sample)
| Pair | Ratio | Meets 4.5:1? |
|---|---|---|
| body on background (light) | X:1 | ✓/✗ |

## Font rendering verification
- Body: [family] (compare to TOKENS.md)
- Display: [family]

## Heading hierarchy
- /: h1 → h2 → h3 ✓/⚠

## Meta
- viewport meta: ✓/✗
- theme-color: [value|missing]

## Console errors
- [none | list]

## Reduced-motion
- [not tested | pass/fail notes]
```

## CAPTURE-MANIFEST.md

Human-readable index of every PNG + manifest path. design-review reads both files plus `ARCHETYPE.md` / `TOKENS.md`.

## Handoff gate

Proceed to `design-review` only when:

1. Minimum capture matrix complete (see capture-matrix.md)
2. `AUTOMATED-AUDIT.md` exists
3. No uncaptured routes the user explicitly requested
