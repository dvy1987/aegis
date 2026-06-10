# Design: Question Agent (appeal + showcase)

**Date:** 2026-06-10  
**Status:** Approved by PM (brainstorming session) — revised 2026-06-10 (geo deferred to a separate agent; appeal = traced-not-graded; firewall promoted to a hard invariant; evolvable component id pinned).  
**Audience:** Any implementing agent — read this before coding.

---

## Summary

Build one **question agent** that runs **before drafting** on both `/appeal` (real person) and showcase (patient simulator). It reads the denial + user notes, **quietly checks playbook + library first**, then runs an **adaptive interview (up to 5 questions)**. Only **patient-knowable** facts go to the person/simulator; regulatory/policy gaps are for playbook/library lookup — never asked of the patient.

A real **question judge** replaces today’s stub score. It grades the Q&A transcript and flags **regulatory playbook gaps** for the existing Phoenix → learning → approval loop.

---

## Problem

People paste a denial and optional notes but rarely provide everything needed to rebut **every denial reason**. The drafter cannot invent patient facts. Regulatory requirements live in playbooks/library — not in the patient’s head.

Today showcase gives the drafter **no** clinical context (good for training), but there is **no Q&A step**, so the question agent never trains. The judge panel stubs `question_agent` at 5/5 (inflates composite by 0.10).

---

## PM decisions (locked)

| Topic | Decision |
|---|---|
| Question cap | **Up to 5**; stop at 2–3 if nothing left worth asking |
| UX | **Chat step** (one question at a time); **“Skip for now”** on the side |
| Skip behavior | Draft immediately with pasted content only; on draft page show **which questions would have helped** (the 2–5 the agent would have asked) |
| Pre-interview research | **Yes** — check playbook + library before first question |
| Adaptivity | Re-plan after each answer; **drop questions a prior answer already resolved** (don’t re-ask); no repeats; if “I don’t know”, move on |
| Gap note | **Not in appeal letter** — separate UX note on draft page (“best effort; these answers would help”) |
| Showcase simulator | **Omniscient** re full clinical file; answers **patient-voiced only**; **never** divulge regulatory content from clinical file |
| Showcase Q&A | **Always full** — treat simulator as real patient |
| Question agent evolution | **Yes** — its own prompt (`question_agent_system_prompt`) improves via question judge + learning loop (not only drafter/playbook) |
| Appeal grading | **Appeal Q&A is traced, not graded.** A real `/appeal` is a live patient conversation with no answer key, so no judge runs there. **Grading + learning happen in showcase only**, where the synthetic clinical file is the answer key. |
| General/geo playbooks | **Deferred** — a separate agent owns geo. Out of scope here; revisit with PM at the very end (see Phase 5). |

---

## Architecture

### Where it sits in the pipeline

```
Intake (denial + optional notes)
    → case_parser
    → playbook_loader (geo playbook deferred to a separate agent)
    → library search / phoenix read (question-prep only)
    → ★ question_agent loop (0–5 turns) ★
    → enriched clinical_context assembled
    → library_finder → drafter → self_check → publish
```

**Appeal path:** question agent talks to the **real user** (chat API).  
**Showcase path:** question agent talks to **patient_simulator** (LLM with full teacher clinical context, patient-voice firewall).

### Two kinds of gaps (never mix them)

| Gap type | Examples | Source |
|---|---|---|
| Patient facts | Step therapy tried, symptom timeline, prior auth dates | User or simulator |
| Regulatory / policy | Plan criteria, filing deadlines, insurer rules, FDA labeling | Playbook, geo playbook, library, model training — **not** patient |

### Question agent outputs (per run)

1. **`qa_transcript`** — ordered `{question, answer, turn}` list (0–5 turns; 0 if skipped).
2. **`enriched_context`** — merged text passed to drafter (original notes + Q&A answers).
3. **`planned_questions`** — if skipped early, the questions it *would* have asked (for UX gap list).
4. **`patient_gap_note`** — plain-English UX copy for draft page (missing info, not in letter).
5. **`internal_gap_analysis`** — for judges/Phoenix only (may reference what regulatory bits were missing).

### Patient simulator (showcase only)

- Input: full teacher `clinical_context` + case metadata (age, etc.).
- Output: short patient-voiced answers.
- **Hard rule:** refuse to answer regulatory/policy questions; redirect (“I wouldn’t know that — that’s my plan/insurer stuff”).
- No injected flaws / vagueness — simulator is helpful when the question is sharp and patient-appropriate.

### Appeal UX (frontend)

New step between intake and working/draft:

1. **Chat screen** — one question at a time; adaptive.
2. **“Skip for now”** — visible, secondary.
3. **Draft page** — letter + side note listing unanswered / skipped questions and why they matter.

Backend: new streaming or turn-based endpoints for Q&A; final `/appeal` draft call receives `qa_transcript` or skip flag.

---

## Question judge (replaces stub)

**Runs in showcase only.** A real `/appeal` has no answer key (it is a live patient conversation), so the question judge never runs there — appeal Q&A is only traced for observability. All scoring + learning signal below comes from showcase runs against the synthetic clinical file.

Remove `STUBBED_QUALITY_DIMENSIONS` for `question_agent` when this ships.

### Part A — Conversation quality (10% weight, unchanged)

Reads full `qa_transcript` + denial. Scores 1–5:

- Asked the **right** patient questions for this denial’s hooks?
- **Adapted** after answers (not rigid pre-planned list)?
- **Extracted value** — each question earned its slot?
- **No waste** — no repeats, no regulatory questions to patient?

Writes `improvement` notes to Phoenix (feeds learning).

### Part B — Playbook gap recommendations

Judge sees **teacher clinical context** (hidden from question agent). Finds regulatory/insurer/law bits that:

- Were **essential** to solve the case,
- Were **not** patient-appropriate to ask,
- Were **missing** from playbooks the run actually loaded.

Output: structured recommendations, e.g.:

```json
{
  "playbook_additions": [
    {
      "target": "slice",
      "slice_id": "Cigna:medical_necessity:not_evidence_based",
      "rule_text": "…",
      "justification": "…",
      "source_in_clinical_context": "…"
    }
  ]
}
```

> Geo-scoped recommendations are **out of scope** here (separate agent owns geo). Emit slice-targeted additions only for now.

These land in Phoenix as judge `improvement` / metadata → existing learning loop proposes playbook edits → **human approval** → on-disk playbook update. **Not auto-applied.**

---

## Learning loop integration

| Component | Evolves? | Signal source |
|---|---|---|
| Drafter prompt | Yes (existing) | All judge dimensions |
| Slice playbook | Yes (existing) | Slice-scoped judge notes |
| Geo playbook | Deferred (separate agent) | — |
| **Question agent prompt** (`question_agent_system_prompt`) | **Yes (new)** | `question_agent` dimension + Q&A improvement notes |

Extend `LearningCoordinator` eligible components with **`question_agent_system_prompt`** (this exact component id — no alias). When `question_agent` is the weakest dimension, reflection mutates the **question agent prompt**, not the drafter.

Credit map already lists `question_agent` → `question_agent` in swarm tools; wire v1 the same way.

---

## Implementation phases (ordered)

### Phase 1 — Core agent (backend, no UI)

- [ ] `question_agent.py` — ADK `LlmAgent` with tools: `playbook_loader`, library search (reuse existing seams).
- [ ] `patient_simulator.py` — showcase-only; patient-voice + regulatory firewall.
- [ ] `question_workflow.py` or nodes in `student_workflow.py` — prep → loop (max 5) → enrich context.
- [ ] Wire showcase measurement path: **no clinical context to drafter**; full Q&A before draft.
- [ ] Persist `qa_transcript` + `planned_questions` on run artifacts / Phoenix trace.

### Phase 2 — Appeal API + UX

- [ ] Turn-based Q&A API (start / answer / skip).
- [ ] Frontend chat step + skip + draft-page gap note.
- [ ] Skip path: 0 turns, populate `planned_questions` from agent’s pre-planned list.

### Phase 3 — Real question judge

- [ ] New judge agent (or two-part single judge) in judge workflow.
- [ ] Remove stub in `panel.py`.
- [ ] Tests: adaptive scoring, playbook recommendation shape, no regulatory leak in simulator tests.

### Phase 4 — Question prompt learning

- [ ] Register `question_agent_system_prompt` as evolvable component.
- [ ] Coordinator + reflection path when `question_agent` is weakest.
- [ ] Showcase approval card shows question-prompt diff if proposed.

### Phase 5 — Geo playbook (DEFERRED — separate agent owns it)

**Out of scope for this feature.** A separate agent is building geo playbooks per `docs/plans/2026-06-10-geo-playbook-plan.md`. Do **not** implement geo here. The question agent's prep pass may *optionally* read geo rules once that agent's loader exists, but must never depend on it. **Revisit with PM at the very end** of the question-agent work.

### Phase 6 — Judge → slice-playbook wiring

- [ ] Map judge `playbook_additions` into reflection input for **slice** components only (geo deferred).
- [ ] Append-first mutation.

### Phase 7 — Showcase firewall hardening (do at the end)

- [ ] Promote to a hard invariant (**INV-QA**): in showcase, the question agent / student **never** receives the teacher `clinical_context`; only the patient simulator does.
- [ ] Build-breaking test asserting no teacher clinical context leaks into question-agent or drafter inputs on the showcase path (mirror the existing answer-key firewall INV-2).

---

## Testing

1. **Appeal skip:** 0 Q&A turns → draft succeeds → UX lists planned questions.
2. **Appeal full:** 3 adaptive turns → enriched context reaches drafter.
3. **Simulator firewall:** agent asks regulatory question → simulator refuses patient-inappropriate answer.
4. **No repeat:** “I don’t know” → next question differs.
5. **Showcase:** always runs Q&A; drafter never sees raw teacher clinical context.
6. **Judge:** low score when questions are generic; high when targeted to denial hooks.
7. **Learning:** question prompt mutation triggers when dimension weakest (offline coordinator test).
8. **Stub removed:** composite no longer flat +0.10 from fake 5.

---

## Non-goals (this feature)

- Document upload (PM deferred).
- Medicare/Medicaid.
- Auto-promote playbooks without human approval.
- Part B swarm question agent (v1 + showcase only for hackathon).
- Rich playbook diff UI (backend summary OK).

---

## Gap analysis vs other agent work

### What the other agent **built** (commit `35903a2` + related)

| Item | Status | Notes |
|---|---|---|
| **Slice key** (`insurer:denial_type:sub_tactic`) | ✅ Shipped | `slice_key.py`, coordinator, showcase, phoenix traces |
| **Per-slice playbook filenames** | ✅ Shipped | e.g. `cigna__medical_necessity__not_evidence_based.json` |
| **Geo playbook plan** | 📄 Plan only | `docs/plans/2026-06-10-geo-playbook-plan.md` — **no code** (`geo_key.py`, `geo_playbooks/` absent) |
| **Question agent** | ❌ Not built | Judge stub at 5/5 only |
| **Patient simulator** | ❌ Not built | Handoff concept only |
| **playbooks/README.md** | ⚠️ Stale | Still documents old two-part filenames; omits sub_tactic |

### Critical gaps in other agent’s work (for this feature)

1. **No question agent at all** — only judge placeholder; implementing agent starts from scratch on Phases 1–4.
2. **Geo playbook is plan-only** — question agent prep should load geo rules when Phase 5 lands; until then, federal/general rules live only in slice playbooks + library.
3. **Drafter still receives clinical context on appeal** — showcase path must be changed to withhold teacher context and insert Q&A (not done).
4. **Learning coordinator does not evolve question prompt** — only drafter + slice playbooks today.
5. **No Q&A transcript in Phoenix traces** — judge Part A blocked until traced.
6. **Frontend has no chat step** — intake goes straight to working/draft today.
7. **README / docs drift** — `playbooks/README.md` doesn’t match `slice_key.py` filenames; fix when touching playbooks.

### Alignment (no conflict)

- PM’s “general playbook (FDA, US-wide)” maps to the **geo playbook plan** (`us_federal` + scoped rules). Same intent; implement that plan after question agent core.
- Question judge Part B playbook recommendations fit geo + slice append paths already designed in geo plan §6.3.

---

## Open questions

- **Geo playbook integration** — deferred; a separate agent owns it. Revisit with PM at the very end of the question-agent work (Phase 5).

---

## Handoff checklist for implementing agent

1. Read this doc. Geo playbook is **deferred** (separate agent) — do not build it here; revisit at the end.
2. Read latest handoff in `docs/memory/agent-handoffs.md` (judge weights, stub behavior).
3. Start Phase 1 backend; do not block on geo playbook files.
4. Replace judge stub only when real judge + transcript exist.
5. Keep language plain in UX copy; no regulatory text invented — corpus/playbook only.
