# Aegis frontend

Two surfaces, one design language:

- **`/` + `/appeal`** — the calm consumer flow (intake → working → mirror → draft → decide).
  Never names the AI.
- **`/showcase`** — "How Aegis learns": the judge-facing proof of the self-improvement loop
  (v1 vs v3, what changed, the memory-off counterfactual).

Design spec: `docs/superpowers/specs/2026-06-01-aegis-frontend-design.md`
Implementation plan: `docs/superpowers/plans/2026-06-01-aegis-frontend.md`

## Run

```bash
pnpm install
pnpm dev        # http://localhost:3000
pnpm test       # vitest (logic + firewall + data layer)
pnpm build      # production build
pnpm lint
```

## Data modes

All data flows through one `DataSource` seam (`src/lib/data/`):

| Env | Behavior |
|---|---|
| _(unset)_ / `NEXT_PUBLIC_AEGIS_MODE=demo` | **Default.** Bundled fixtures from the real benchmark cases + recorded efficacy run. Fully clickable offline; no backend or credentials needed. |
| `NEXT_PUBLIC_AEGIS_MODE=live` | `draftAppeal` calls the FastAPI backend `POST /v1/appeal`. Set `NEXT_PUBLIC_AEGIS_API` to the backend base URL (default `http://localhost:8001`). The showcase always reads recorded artifacts. |

## Firewall (INV-2)

Demo fixtures carry only student-visible fields. The teacher answer key
(`synthetic_provenance`, `appeal_difficulty`, `exploitable_weaknesses`, …) must never appear in
`src/lib/fixtures/`. Enforced by `src/__tests__/firewall.test.ts` — keep it green.

## Notes

- Visual system (tokens, type, motion) is locked in `.design/aegis/` and `src/styles/tokens.css` —
  use semantic token classes only, never raw Tailwind palette names.
- Live mode omits `parsed_case` / `appeal_strategy`, so the Mirror step renders a lighter view in
  live mode (spec §6.1). Returning those from the API is a noted backend follow-up.
