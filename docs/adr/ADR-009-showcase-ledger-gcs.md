# ADR-009 — Showcase session ledger on GCS (Cloud Run durability)

**Status:** Accepted (2026-06-08)  
**Context:** ADK migration Phase 5

## Problem

Showcase quick/serious runs persist session state as JSON files under `AEGIS_SHOWCASE_LEDGER_DIR` (default `/tmp/aegis_showcase_sessions`). Cloud Run revisions use ephemeral filesystems — **redeploy wipes in-flight sessions**, breaking resume and approve flows mid-demo.

## Decision

Introduce `showcase_ledger.py` with two backends:

| Backend | When | Path |
|---|---|---|
| `LocalLedgerStore` | Dev / tests / no GCS env | `AEGIS_SHOWCASE_LEDGER_DIR` or `/tmp/...` |
| `GcsLedgerStore` | Production Cloud Run | `AEGIS_SHOWCASE_LEDGER_GCS_URI` (`gs://bucket/prefix`) |

`ShowcaseSessionManager` and `PromotionStack` read/write through `open_ledger_store()`.

**Deploy default:** when `AEGIS_LIBRARY_BUCKET` is set and `AEGIS_SHOWCASE_LEDGER_GCS_URI` is not, `deploy-v1.sh` sets:

`AEGIS_SHOWCASE_LEDGER_GCS_URI=gs://${AEGIS_LIBRARY_BUCKET}/aegis-showcase-ledger`

Cloud Run runtime SA needs `roles/storage.objectUser` on that bucket (granted in `deploy-v1.sh --bootstrap` when bucket is configured).

## Consequences

- Sessions survive redeploys and single-instance restarts.
- Promotion rollback stack (`promotion_stack.json`) co-locates with session JSON in the same GCS prefix.
- No new paid vendor — reuses existing GCS bucket.
- Local/tests unchanged when GCS URI unset.

## Alternatives considered

- **Cloud SQL / Firestore** — rejected for hackathon timeline; JSON blobs sufficient for session ledger.
- **GCS FUSE mount** — rejected; extra Cloud Run volume config for marginal benefit over native SDK.
