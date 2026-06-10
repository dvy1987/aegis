# Post-hackathon backlog

Items we noticed during the hackathon build but chose **not** to fix before submission — plus **priority assessments** to run before Part B (swarm, autonomous learning). Append at our discretion; not a commitment to do everything.

**Severity key:** `now` = blocks correctness or demo · `soon` = fix before next touch · `later` = tech debt · `assess` = experiment before committing engineering

## Priority order (June 2026)

Assess **before** resuming Part B swarm or autonomous promotion:

| # | Item | Question |
|---|------|----------|
| **G1** | [§4 Library online search](#4-library-agent--freer-online-search-vs-controlled-corpus--assess-priority) | Does freer online retrieval improve held-out quality enough to justify risk and cost? |
| **G2** | [§5 GEPA economics](#5-gepa-showcase-loop--cost-vs-quality-lift--assess-priority) | Is showcase GEPA spend justified by simulator/judge lift at preview (7) and production (70) scale? |
| **G3** | [§3 Swarm vs v1](#3-evaluate-agent-swarm-vs-aegis-v1--assess-gated) | After G1/G2 — does the 12-agent swarm beat an improved v1 Student? |

### Hackathon submission snapshot

| Shipped | Deferred |
|---------|----------|
| v1 ADK Student workflow | 12-agent Aegis swarm (`aegis_swarm/`) |
| Question agent (appeal + showcase) | Autonomous Journeyman / Master promotion |
| Slice playbooks + US-playbook + GEPA | Full 100-case × 7-denial matrix |
| Showcase preview 5+2 · production 50+20 | State-scoped US rules (no `us_state` on cases yet) |

**Invariants:** `/appeal` = draft only, no learning/promotion · showcase **Approve** = only promotion path · reflection decides append vs edit on playbooks; modal warns on rule edits, does not block.

Cross-ref: [PRD §0.1](prd/PRD.md) · [product-soul](product-soul.md) · [open-questions §G](open-questions.md).

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

## 3. Evaluate agent swarm vs aegis-v1 — `assess` (gated)

**Logged:** 2026-06-10 · **Updated:** 2026-06-10 (PM: swarm **deferred post-hackathon**, not submission path)

**Status:** Hackathon ships **aegis-v1 only**. Swarm scaffold exists; **do not resume until §4 and §5 readouts exist.**

### What

Run a structured comparison: v1 baseline vs **12-agent swarm** on the same held-out cohorts. Question is not “can we build swarm?” (we can) but “does swarm beat an improved v1 enough to justify orchestration complexity and cost?”

### Why it matters

- **Quality:** Specialization may help multi-hook denials — or coordination overhead may hurt.
- **Cost:** Swarm multiplies LLM calls per case; only worth it if APPROVE rate or judge composite improves materially per dollar.
- **Learning:** v1 GEPA already mutates drafter + slice playbooks + US-playbook; swarm `swarm_scored_run` credit assignment is unproven vs v1 on showcase cohorts.

### Proposed exploration

1. Same benchmark, same rubric — quick + serious holdouts; weighted quality, simulator APPROVE, grounding.
2. Cost model — $/case, attempts-to-APPROVE, wall time per architecture.
3. **Go/no-go** — swarm only if it wins on quality **and** passes cost guardrails from §5.

### PM note

Deferred, not cancelled. Chapter two after v1 economics are understood.

---

## 4. Library agent — freer online search vs controlled corpus — `assess` (priority)

**Logged:** 2026-06-10  
**Status:** Corpus-first at submission. Vertex / discovery stack exists; **broader online retrieval not validated for quality lift.**

### What

Today the library path is bounded: local `corpus/` snippets + configured Vertex search. Post-hackathon question: **if the library agent can search online sources more freely**, how much does appeal quality improve on held-out cases?

### Why it matters

- **Upside:** Better grounding and appeal_vector_capture when denial hooks need statutes, plan language, or insurer policy text not in corpus.
- **Downside:** Hallucination risk, citation discipline, latency, and per-draft API cost — judges explicitly score grounding; uncontrolled web text may hurt as often as help.

### Proposed experiment

| Arm | Library stack |
|-----|----------------|
| A (baseline) | Current corpus + Vertex as shipped |
| B (treatment) | A + bounded online / broader discovery (define cap: domains, result count, cache) |

**Metrics:** held-out composite; grounding dimension; hard-gate PASS rate; faithfulness / citation checks; $/draft.

**Kill:** No composite lift or grounding regression vs A.

### PM note

Assess **before** scaling GEPA or swarm — cheap retrieval wins may beat expensive multi-agent coordination.

---

## 5. GEPA showcase loop — cost vs quality lift — `assess` (priority)

**Logged:** 2026-06-10  
**Status:** Showcase GEPA + human approve ships for hackathon. **No cost/lift accounting yet.**

### What

Showcase training is expensive. Per promotion cycle (preview 7 cases or production 70 cases), the system runs:

- Training seed: student draft + full judge panel + question judge per case
- GEPA: reflection + re-score on holdout/train split (`max_rounds` × components: drafter, question prompt, slice playbooks, US-playbook)
- Post-candidate eval + before/after **simulator measurement** (no judges on measure path)

Each step is multiple Gemini calls. Cost scales with cohort size and rounds.

### Why it matters

- A small composite lift on 7 cases may **not** justify production-scale GEPA if 70-case runs cost tens of dollars per cycle.
- PM needs a **$/+0.01 composite** or **$/APPROVE flip** number before enabling larger cohorts, more rounds, or autonomous promotion.

### Proposed instrumentation

1. Log token usage (or estimate from provider billing) per showcase stage: `train_gepa`, `measure_before`, `measure_after`, `promote`.
2. Run at least one full **preview** and one **production** cycle with accounting.
3. Compare held-out simulator APPROVE delta (before vs after approved promotion) to total spend.

| Outcome | Action |
|---------|--------|
| Lift clear, cost acceptable | Keep GEPA; consider more rounds / cohorts |
| Lift clear, cost high | Cheaper reflection signal, fewer rounds, or smaller minibatch |
| Lift weak | Pause GEPA; fix judges/signal before spending more |
| Lift negative | Rollback; treat as regression |

### PM note

Apprentice (human approve) stays until this readout. Journeyman/Master autonomous promotion **blocked** until economics are documented.

---

## 6. State-scoped US-playbook rules — `later`

**Logged:** 2026-06-10  
**Status:** US-playbook ships with federal rules only; cases lack `us_state` so state-tagged rules are filtered at runtime.

When benchmark cases carry `us_state` and `plan_funding_type`, enable state-scoped rule learning (mirror slice isolation: only mutate CA rules when CA cases are in training).

---

<!-- Append new items below with the next number. -->
