# Session Handoff — Question Agent Closeout (2026-06-10)

**Agent:** Cursor  
**Audience:** Next coding agent + PM  
**Related:** `docs/2026-06-10-question-agent-test-handoff.md` (feature + test reference, updated this session)

---

## Session goal

Close remaining question-agent / showcase-learning gaps after Round 2 build: verify what was still open, fix activation + approval UX, refresh stale docs.

---

## Done this session

### 1. Gap re-verification (read-only)
- Re-checked repo vs prior gap list. Most Round 2 items already shipped (showcase Q&A, workflow node, geo playbook, coordinator, tests).
- Backend unit suite verified: **446 passed, 0 failed** (`uv run pytest tests/unit` from `backend/`).
- Frontend vitest: **28 passed**. Frontend `tsc`: **8 errors** — pre-existing in `statusPreviewBatch.test.ts` only.

### 2. Question agent prompt activation on promote — **committed** (`ac628c1` / merged on `main`)
- **Change:** `backend/app/learning/fs_store.py` — `_write_prompt` now writes `active_question_agent_prompt.txt` + `{version}.md` for `question_agent_system_prompt` (mirrors drafter).
- **Test:** `backend/tests/unit/learning/test_promotion_wiring.py` — `test_question_agent_prompt_promotion_writes_runtime_loadable_filename`

### 3. Approval modal — question agent prompt diffs — **committed** (`5259ef2`)
- `promotion_preview.py`, `promotionPreview.ts`, `PromotionReviewModal.tsx`, tests.

### 4. Agent-owned gap routing — **committed** (`e6ee11c` + final refinement this commit)
- Question agent returns `substantive_questions` + `gap_questions` on each step; **on stop these lists are authoritative** for drafter vs draft-page gap note (Python heuristics only if the model omits them).
- `QuestionInterviewResult` carries routing lists for traces.
- Fixes “I'm not totally sure” simulator replies routing to gaps, not drafter.

### 5. Stale docs — **committed** (`06b3467`)
- Question-agent test handoff + geo playbook plan marked implemented; session handoff + memory updated.

---

## PM-locked behavior (unchanged)

| Topic | Rule |
|-------|------|
| Appeal Q&A | Traced, **not** graded (no answer key) |
| Showcase Q&A | Graded by question judge; Part B mines playbook additions |
| INV-QA | Question agent / patient sim never see teacher `clinical_context` on showcase |
| Learning | `question_agent_system_prompt`, slice playbooks, `geo_playbook:us` evolvable in GEPA |

---

## GEPA → approve → runtime (current state)

| Component | In GEPA proposal? | Approval modal diff? | Active after promote? |
|-----------|-------------------|----------------------|---------------------|
| Drafter prompt | Yes | Yes | Yes (`active_drafter_prompt.txt`) |
| Question agent prompt | Yes | Yes (this session) | Yes (`ac628c1`) |
| Slice playbooks | Yes | Yes | Yes (playbook JSON files) |
| US-playbook | Yes | Yes (rule changes) | Yes (`geo_playbooks/us_playbook.json`) |

Question-judge “Add to playbook” / “Add to global playbook” strings flow into reflection → mutated playbooks in the proposal (not a separate suggestions list).

---

## Still open (do not block hackathon demo)

1. **Showcase rollback** — `showcase_rollback.py` snapshots only drafter active pointer, not `active_question_agent_prompt.txt` or US-playbook file. One-click rollback after question-agent or geo promotion may be incomplete.
2. **`PATIENT_UNSURE` substring quirk** — low priority; `is_substantive_answer` may treat “unsure” inside longer answers as substantive.
3. **In-memory question sessions** — fine for demo; not multi-worker safe.
4. **Frontend `tsc`** — fix or skip `statusPreviewBatch.test.ts` mock types when touching showcase status tests.
5. **Push / deploy** — PM has not requested; `main` ahead of `origin/main` by 2 commits + dirty tree.

---

## Next agent should do

1. **Commit** uncommitted work from this session (promotion preview + docs) if PM approves — suggested message: *show question-agent prompt diffs in showcase approval modal; refresh handoff docs*.
2. **Optional:** extend `showcase_rollback.py` for question-agent + US-playbook snapshots.
3. **Before demo:** smoke showcase approval modal with a proposal that mutates `question_agent_system_prompt`; confirm diff visible and post-approve run uses new prompt.
4. Use **`uv run pytest`** from `backend/` — not bare `python -m pytest`.

---

## Key files touched this session

| File | Status |
|------|--------|
| `backend/app/learning/fs_store.py` | Committed |
| `backend/tests/unit/learning/test_promotion_wiring.py` | Committed |
| `backend/app/aegis_v1/promotion_preview.py` | Dirty |
| `backend/tests/unit/aegis_v1/test_promotion_preview.py` | Dirty |
| `frontend/src/lib/promotionPreview.ts` | Dirty |
| `frontend/src/components/showcase/console/PromotionReviewModal.tsx` | Dirty |
| `docs/2026-06-10-question-agent-test-handoff.md` | Dirty |
| `docs/plans/2026-06-10-geo-playbook-plan.md` | Dirty |

---

## Git snapshot

```
Branch: main (synced with origin after session commits)
Session commits: prompt activation, gap routing, approval modal diff, docs/handoff
```

---

## Revisit triggers

- PM wants rollback to restore question-agent or geo promotions → implement rollback snapshots.
- Live showcase shows no question-agent diff in modal → check `build_promotion_preview` payload on session + frontend `kind` handling.
- Promoted question prompt not loading → verify `active_question_agent_prompt.txt` exists under `backend/app/aegis_v1/prompts/` after approve.
