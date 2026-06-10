# Plan — Geo playbook (insurer-agnostic, geography-scoped rules)

**Date:** 2026-06-10  
**Status:** Implemented (2026-06-10) — see `docs/2026-06-10-question-agent-test-handoff.md` §Round 2 item 7  
**Builds on:** slice-key work (`insurer:denial_type:sub_tactic`), Learning Coordinator GEPA loop, showcase Preview/Production runs

---

## 1. Problem statement

Aegis needs **three learnable layers**, not two:

| Layer | Scope | Evolves how |
|---|---|---|
| **Drafter** | Global writing craft | Free GEPA evolution every promoting run |
| **Geo playbook** | Insurer-agnostic rules for a geography (deadlines, jurisdiction, filing norms) | Append-friendly; edit/delete old rules only with explicit justification + gates |
| **Slice playbook** | `insurer × denial_pattern × sub_tactic` tactics | Only when training cases exist for that slice (implemented) |

Today only drafter + slice playbook exist. Geo playbook is missing.

---

## 2. Design principles (from PM)

1. **Progressive expansion** — new geographies / insurers add learning without erasing prior geo or slice rules.
2. **Geo isolation (mirror slice isolation)** — a run updates geo playbook `G` only if training cases map to `G`.
3. **Append is the default mutation** — new rules are cheap and safe.
4. **Edit/delete is rare and audited** — reflection must state *why* an existing rule id is changed or removed; promotion gates veto reckless edits.
5. **Drafter untouched by these rules** — geo mutation path is separate from drafter reflection.
6. **No invented law** — rules cite only controlled corpus / existing case facts; reflection prompt repeats citation-only constraint.

---

## 3. Geo model (post PM decisions)

### 3.1 One US playbook

Single learnable component: **`geo_playbook:us`** (display name: **US-playbook**). One file `geo_playbooks/us_playbook.json`. Not separate files per state.

### 3.2 Rule scope labels (on each rule)

| Field | Values | Meaning |
|---|---|---|
| `scope` | **US federal** \| state name (e.g. **California**) | Who the rule applies to geographically |
| `funding_scope` | optional: **self_funded** \| **fully_insured** \| omit = all | When ERISA vs state-regulated matters |

Rule text may repeat scope in plain language (“valid in California only”).

### 3.3 Case → applicable rules (runtime)

```python
def applicable_geo_rules(playbook, case) -> list[Rule]:
    state = resolve_us_state(case)
    funding = case.patient_profile.plan_funding_type
    out = []
    for rule in playbook.rules:
        if rule.status != "active":
            continue
        if rule.scope == "US federal" or rule.scope matches case state:
            if rule.funding_scope is None or rule.funding_scope matches funding:
                out.append(rule)
    return out
```

v1: all cases match **US federal** rules only (no state on cases yet).

### 3.4 Learning activation

Geo playbook is in the GEPA pool when the run has US training cases (always, for now). **State-scoped rule mutations** only when training cases include that state (or reflection explicitly tags a new rule with that scope and cases justify it).

---

## 4. On-disk schema

**Directory:** `geo_playbooks/` (repo root, parallel to `playbooks/`)

**File:** `geo_playbooks/us_playbook.json` (display name **US-playbook**)

```json
{
  "geo_id": "us_federal",
  "version": "day_zero",
  "rules": [
    {
      "rule_id": "fed_001",
      "text": "State the appeal deadline from the denial letter when present.",
      "status": "active",
      "added_in_version": "day_zero",
      "added_at": "2026-06-10T00:00:00Z"
    }
  ]
}
```

**Edit/revoke** (never hard-delete in v1 — audit trail):

```json
{
  "rule_id": "fed_001",
  "text": "Updated text…",
  "status": "active",
  "added_in_version": "day_zero",
  "edited_in_version": "geo_v2",
  "edit_justification": "Judge feedback: letters missed explicit 180-day citation when letter states it.",
  "last_edited_at": "…"
}
```

Revoked:

```json
{
  "rule_id": "fed_002",
  "status": "revoked",
  "revoke_justification": "Contradicted by corpus doc X; rule was wrong.",
  "revoked_in_version": "geo_v3"
}
```

**Component id in Learning Coordinator:** `geo_playbook:us_federal` (prefix `geo_playbook:` to distinguish from `playbook:` slice components).

---

## 5. Runtime (drafting pipeline)

### 5.1 Load path

New module: `backend/app/learning/geo_key.py` (parallel to `slice_key.py`)

New loader: `geo_playbook_loader(geo_id: str) -> dict` in `tools.py` or dedicated `geo_playbook.py`

### 5.2 Student workflow change

After `playbook_loader_node`, add **`geo_playbook_loader_node`**:

1. Resolve `geo_keys` from `parsed_case` + teacher case metadata when available.
2. Load each geo playbook file (cold-start empty rules list if missing).
3. Merge active rules into `ctx.state["geo_playbook"]`:
   ```json
   {
     "geo_ids": ["us_federal"],
     "rules": [ /* active rules from all stacked geos, tagged with geo_id */ ],
     "version": "combined:us_federal@day_zero"
   }
   ```

### 5.3 Drafter injection

Extend `build_drafter_message` with optional `GEO PLAYBOOK` section (separate from slice `PLAYBOOK`):

```
GEO RULES (insurer-agnostic, jurisdiction):
- [us_federal/fed_001] …
```

Slice playbook stays insurer/denial/sub-tactic tactics.

### 5.4 Overrides for GEPA measurement

`geo_playbook_overrides: dict[str, dict]` keyed by `us_federal`, passed through showcase runner / experiment runner like slice overrides.

---

## 6. Learning (GEPA integration)

### 6.1 Coordinator extensions

Extend `LearningCoordinator`:

| Concern | Slice (done) | Geo (this plan) |
|---|---|---|
| Active set from training | `slice_filters` | `geo_filters` |
| Seed components | `playbook:{slice}` | `geo_playbook:{geo_id}` |
| Eligible for round-robin | drafter + active slice playbooks | + active geo playbooks |
| Signal filter | `acquire_signal(..., slice_filter=slice)` | `acquire_signal(..., slice_filter=None, geo_filter=geo_id)` **new** |
| Promote filter | skip playbooks not in `slice_filters` | skip geo playbooks not in `geo_filters` |

**Drafter** remains eligible every run; not geo-filtered.

### 6.2 Signal acquisition for geo

Extend `ScoredRun` with optional `geo_keys: list[str]` (from trace metadata).

Extend `acquire_signal`:

```python
def acquire_signal(..., slice_filter: str | None, geo_filter: str | None = None):
    runs = store.read_scored_runs(...)
    if slice_filter is not None:
        runs = [r for r in runs if r.slice == slice_filter]
    if geo_filter is not None:
        runs = [r for r in runs if geo_filter in (r.geo_keys or [])]
```

Geo component signal = judge feedback from cases that **stack** that geo (federal rules learn from all US cases; CA rules only from CA cases).

### 6.3 Geo-specific reflection (append-first)

**Do not** use generic `reflective_mutate` JSON blob rewrite for geo playbooks.

New: `reflect_geo_playbook(parent, signal, reflection_client) -> Component`

Reflection output schema (structured):

```json
{
  "operation": "append" | "edit" | "revoke",
  "rule_id": "fed_003",           // required for edit/revoke; generated for append
  "text": "…",                    // required for append/edit
  "justification": "…"            // required for edit/revoke; optional for append
}
```

Reflection prompt constraints:
- **Default operation: append** — prefer adding a new rule id.
- **Edit/revoke only if** minibatch failure cannot be fixed by a new rule without contradicting an existing one.
- **Justification must cite** which judge dimension failed and what concrete letter gap the change fixes.
- No statute/case law invention.

Stub reflection client: implements append for tests.

### 6.4 Promotion gates (geo-specific)

Extend `evaluate_vetoes` or add `evaluate_geo_vetoes(candidate, base)`:

| Veto code | Condition |
|---|---|
| `geo_edit_without_justification` | any `edit`/`revoke` op missing non-empty justification (min 40 chars) |
| `geo_edit_without_dimension_link` | justification does not mention weakest dimension name from signal |
| `geo_mass_edit` | >1 edit/revoke in single candidate (v1: max 1 structural change per GEPA child) |
| `geo_rule_id_collision` | append uses existing active rule_id |

Existing global vetoes (composite regression, diff token cap) still apply to the **run as a whole**; geo-specific vetoes block promotion if geo component changed recklessly.

### 6.5 Showcase runner wiring

In `_run_learning_session`:

```python
slice_filters = _slice_filters(train_cases)
geo_filters = _geo_filters(train_cases)  # new
```

Pass both into `_optimize` → `LearningCoordinator`.

Checkpoint / measurement paths resolve per-case geo keys and apply correct overrides.

---

## 7. Phoenix / trace metadata

Extend `evaluated_run.py` trace metadata:

```python
trace_meta["geo_keys"] = ",".join(geo_keys_from_case(case_obj))
```

Extend `phoenix_live.rows_to_scored_runs` to parse `geo_keys` into `ScoredRun.geo_keys`.

---

## 8. Day-zero seed content

Create `geo_playbooks/us_federal.json` with 3–5 conservative, non-legal-advice rules, e.g.:

- Cite appeal deadline from denial letter when stated
- Request full claim file / clinical criteria in writing when letter is vague
- Distinguish coverage determination from medical advice (tone)
- Use person-first, non-inflammatory language (aligns with design brief)

**No state files** until cases have `us_state`.

---

## 9. Open decisions (PM — answer before coding)

### 9.1 Case geography field — **DECIDED (PM 2026-06-10)**

Cases lack `us_state` today. **Ship v1 with US federal only** (display label: **US federal**). Add state playbooks (e.g. **California**) when cases carry `patient_profile.us_state`. Internal storage may use slugs (`us_federal`, `us_ca`); UI and docs use plain labels.

### 9.2 Federal vs state rules — **DECIDED (PM 2026-06-10)**

**One US geo playbook** (not separate per-state files in v1). Each rule carries a **scope label**:
- **US federal** — applies nationwide
- **State name** (e.g. **California**) — applies only in that state; stated explicitly in the rule

At draft time, load the US playbook and **filter rules** to those applicable to the case: all federal rules + state rules matching the case’s state (when known). State-specific law is expressed **inside the rule** (“valid in California only”), not by maintaining wholly separate geo playbooks per state.

Learning: adding a California-scoped rule should only happen when training cases support it (case has that state, or judge signal is clearly state-specific).

### 9.3 `plan_funding_type` — **DECIDED (PM 2026-06-10)**

Rules may carry an optional **funding scope** when relevant (e.g. self-funded, fully insured). Same single US playbook; filter at draft time by case `plan_funding_type` plus state + federal scope labels.

### 9.4 Preview may learn geo — **DECIDED (PM 2026-06-10)**

**Yes.** Preview runs may propose US geo playbook updates with the same human approve-to-promote step as Production.

### 9.5 Approval UI — **DECIDED (PM 2026-06-10)**

PM must see **full rule text** (not summary-only) before approving geo playbook changes. Showcase approval card shows appended/edited/revoked rules with scope labels (US federal / state / funding) and complete text + edit justifications.

---

## 10. Implementation tasks (ordered)

### Phase A — Schema + load (no learning)

| # | Task | Files |
|---|---|---|
| A1 | `geo_key.py`: `geo_keys_from_case`, `parse_geo_key`, `geo_playbook_component_id`, filenames | `backend/app/learning/geo_key.py` |
| A2 | `GeoPlaybook` pydantic schema + loader + cold start | `schemas.py`, `tools.py` or `geo_playbook.py` |
| A3 | Day-zero `geo_playbooks/us_federal.json` | `geo_playbooks/` |
| A4 | `geo_playbook_loader_node` + drafter message section | `student_workflow.py`, `drafter_client.py` |
| A5 | Unit tests: loader, merge, drafter message includes geo rules | `tests/unit/aegis_v1/` |

### Phase B — Traces + showcase read path

| # | Task | Files |
|---|---|---|
| B1 | `ShowcaseCase.us_state` optional field from `patient_profile` | `showcase_manifest.py` |
| B2 | Trace metadata `geo_keys` | `evaluated_run.py`, `phoenix_live.py`, `ScoredRun` model |
| B3 | `_geo_filters(train_cases)` in showcase runner | `showcase_runner.py` |
| B4 | Tests: trace round-trip, showcase geo_filters | tests |

### Phase C — GEPA learn + promote

| # | Task | Files |
|---|---|---|
| C1 | `geo_filters` param on `LearningCoordinator`; seed geo components | `coordinator.py` |
| C2 | `acquire_signal(geo_filter=…)` | `signal.py` |
| C3 | `reflect_geo_playbook` + structured patch apply | `mutation_geo.py`, `reflection_client.py` |
| C4 | Geo promotion vetoes | `gates.py` |
| C5 | `fs_store` write `geo_playbooks/{slug}.json` on promote | `fs_store.py` |
| C6 | Showcase `_optimize` passes `geo_filters`; overrides in measure/train | `showcase_runner.py` |
| C7 | Coordinator tests: federal-only run updates geo; no CA cases → no CA file write | `test_coordinator.py`, new `test_geo_playbook.py` |

### Phase D — Docs + handoff

| # | Task |
|---|---|
| D1 | Update `docs/architecture.md` three-layer diagram |
| D2 | Feature spec `docs/specs/2026-06-10-geo-playbook-feature-spec.md` (executable ACs) |
| D3 | Memory capture + handoff |

---

## 11. Test plan

1. **Loader:** unknown geo → cold-start empty rules; federal file → rules in drafter context.
2. **Stacking:** case with `us_state=ca` loads federal + CA rules (once CA file exists).
3. **Isolation:** training cases all `us_federal` only → coordinator never seeds `geo_playbook:us_ca`.
4. **Append:** reflection append adds rule; promote writes file; second run sees new rule.
5. **Edit veto:** edit without justification → `is_promotable=False`.
6. **Slice unchanged:** geo learning does not mutate slice playbooks (regression).
7. **Showcase:** Preview run `geo_filters == ["us_federal"]` until state on cases.

---

## 12. Out of scope (this plan)

- International geographies
- Medicare/Medicaid (project hard constraint)
- Autonomous geo promotion without HITL (same as slice — approval required)
- Pattern Synthesizer / cross-geo meta inference (Part B)
- UI rich diff viewer (backend summary only in v1)

---

## 13. Success criteria

1. Draft pipeline injects geo rules separately from slice tactics.
2. GEPA can append federal rules from a showcase run with human approval.
3. Edit/revoke without justification is blocked at promotion.
4. A run with no cases for geo `X` never writes `geo_playbook:X`.
5. Drafter evolution behavior unchanged.
