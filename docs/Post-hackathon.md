# Post-hackathon backlog

Items we noticed during the hackathon build but chose **not** to fix before submission. Append here at our discretion — not a commitment to do everything.

**Severity key:** `now` = blocks correctness or demo · `soon` = fix before next touch on that area · `later` = tech debt, no active bug

---

## 1. Duplicate drafter packaging logic — `later`

**Logged:** 2026-06-08  
**Status:** Not blocking demo or prod `/appeal`.

### What

The “wrap up the letter” step exists in **two places** with near-identical code:

| Path | File | Used by |
|------|------|---------|
| ADK workflow | `backend/app/aegis_v1/student_workflow.py` → `drafter_finalize_node` | Prod `/appeal`, showcase, eval (via `run_aegis_v1_pipeline`) |
| Legacy / tests | `backend/app/aegis_v1/tools.py` → `draft_appeal()` | Unit tests, ADK `drafter` tool registration, offline stubs |

Both paths: guardrails on prose → build `AppealDraft` (citations, checklist, risk flags, disclaimer).  
The **letter writing** step is separate: ADK uses `v1_drafter_agent`; `draft_appeal()` uses `GeminiDrafterClient` or a test stub.

### Why it matters

If someone edits guardrails or risk-flag logic in one file and forgets the other, prod and tests can silently diverge.

### Proposed fix (when we pick it up)

Extract one shared function, e.g. `assemble_appeal_draft(raw_letter, parsed_case, playbook, phoenix_summary, retrieval, prompt_version)`, called from both `drafter_finalize_node` and `draft_appeal()` **after** each path has produced raw letter text.

**Do not merge:** LLM invocation, ADK graph shape, or Phoenix export.

### What this fix must not touch

- **ADK structure** — keep `drafter_prep` → `v1_drafter_agent` → `drafter_finalize` → `self_check` unchanged.
- **Phoenix firewall** — drafter still only sees laundered `phoenix_summary` in prep; no teacher/judge/simulator data.
- **PII split on `/appeal`** — user-facing draft stays full text; redaction stays only in `appeal_phoenix_export.py` / `write_appeal_phoenix_export()` (called from `appeal_orchestrator.py` **after** the pipeline returns). Packaging must not move redaction into finalize.

### PM note

Recorded principle ([decision-log](memory/decision-log.md), 2026-06-08): don’t ship known structural weakness just because it’s a hackathon — but this one is **deferred**, not ignored.

---

## 2. Phoenix PHI/PII leakage judge — `later`

**Logged:** 2026-06-09  
**Status:** Not in hackathon scope; GEPA judges no longer run the safety scope gate.

### What

Add a dedicated judge (or deterministic gate) that checks whether patient PII/PHI from the appeal draft leaked into Phoenix traces/annotations — separate from the user-facing letter (which should keep member IDs and clinical detail for filing).

Today: `/appeal` redacts via `appeal_phoenix_export.py`; showcase/GEPA/eval paths write to Phoenix without that redaction (synthetic cases assumption).

### Proposed fix (when we pick it up)

- New judge dimension, e.g. `phoenix_export_phi_leakage_gate`, run on Phoenix-bound payloads only.
- Compare exported span/annotation text against a PHI pattern set (SSN, MRN, DOB, etc.) and fail promotion if leakage is detected.
- Wire into benchmark + post-`/appeal` export paths; keep GEPA training judges focused on appeal quality.

---

<!-- Append new items below with the next number. -->
