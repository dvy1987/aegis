# Tier 1 — Learning Coordinator Live (GCP + Phoenix) Companion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax. **This plan is credential-gated:** it MUST be executed on the machine where GCP ADC + `PHOENIX_API_KEY` are configured (the dev box here has neither). Each task is structured so its *logic* is built and unit-tested OFFLINE (pure transforms over fixtures), while the network calls are exercised by **smoke tests gated behind the existing `_adc_available()` skip-guard**. You can therefore build and land Tasks 1–3's offline cores anywhere; the live smoke tests light up only where creds exist.

**Goal:** Make the self-improvement loop *real and demonstrable* on live infrastructure — turn the load-bearing `phoenix_mcp_lookup` from a stub into a real Phoenix MCP read, implement the live `PhoenixLearningStore` over the Phoenix client + Prompts registry, wire the coordinator end-to-end with Gemini drafter/judge/reflection, and capture the headline **MCP-off counterfactual** ("disable Phoenix → quality collapses") plus a κ≥0.6-calibrated judge — using the Tier-2-optimized prompts as the starting point.

**Architecture:** Implement live behaviour behind the **Protocols that already have offline fakes** (`PhoenixLearningStore`, `JudgeClient`, `DrafterLLMClient`, `ReflectionClient`, `ExperimentRunner`, `PhoenixRecorder`). For every live unit, isolate a **pure transform** (`rows -> ScoredRun`, `traces -> PhoenixSummary`, `PanelReport -> score dict`) that is fully unit-tested offline with recorded fixture payloads; the live class is a thin fetch-then-transform wrapper, construction-tested offline and smoke-tested behind credentials. Cloud/SDK imports stay method-local (the established pattern in `GeminiDrafterClient`/`OtelPhoenixRecorder`). The `phoenix_mcp_lookup` keeps its `disabled`/`cold_start` fallbacks so the MCP-off demo toggle (`PHOENIX_MCP_ENABLED`) still works.

**Tech Stack:** Python 3.11, `uv`, Pydantic v2, `pytest`; `google-genai` (Vertex), `arize-phoenix` client + `phoenix.otel` (already wired in `app_utils/telemetry.py`), `@arizeai/phoenix-mcp` (npx stdio server), `mcp` Python client (spike in `backend/test_mcp_standalone.py`). Gemini 3.1 Pro via Vertex/ADC.

**Specs / prior art (read first):**
- [`docs/specs/2026-05-31-learning-coordinator-v2-gepa-design.md`](../specs/2026-05-31-learning-coordinator-v2-gepa-design.md) §2 (Phoenix-grounded I/O — the data model + `PhoenixLearningStore` contract), §7 (build-vs-companion scope).
- [`docs/evals/2026-05-31-coordinator-efficacy-run.md`](../evals/2026-05-31-coordinator-efficacy-run.md) — the offline efficacy method this re-runs live.
- Code anchors: `backend/app/aegis_v1/tools.py:269` (the `phoenix_mcp_lookup` stub) · `backend/app/aegis_v1/agent.py:62` (tool registration) · `backend/app/evals/part_a/recorder.py` (`PhoenixRecorder` + `OtelPhoenixRecorder` + `laundered_signal`) · `backend/app/evals/part_a/evaluated_run.py:26` (`run_evaluated_case`) · `backend/app/learning/{store,experiment,reflection_client}.py` (the Protocols + Gemini backends) · `backend/app/evals/part_a/llm_judges.py:242` (`GeminiJudgeClient`) · `backend/app/app_utils/telemetry.py` (`phoenix.otel.register`) · `backend/test_mcp_standalone.py` (the MCP stdio spike) · `backend/tests/integration/test_live_appeal.py:18` (the `_adc_available()` skip-guard).

**Conventions for every task:** as in the offline plans (tests from `backend/`; commit from repo root with the `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>` trailer; one commit per task; cloud/SDK imports method-local; **no live call in any non-gated test**). Add a shared `_creds_available()` helper (ADC ∧ `PHOENIX_API_KEY`) for the gated smoke tests, mirroring `_adc_available()`.

---

## File Structure

- **Create** `backend/app/learning/judge_adapter.py` — `PanelJudgeAdapter` (Part-A panel → the `judge_client.score()` dict). **Offline-testable.**
- **Create** `backend/app/learning/phoenix_live.py` — `LivePhoenixLearningStore` + the pure `rows_to_scored_runs()` / `component_version_from_prompt()` transforms.
- **Modify** `backend/app/aegis_v1/tools.py` — replace the `phoenix_mcp_lookup` body with `_summarize_traces()` (pure) + a gated MCP fetch; keep `disabled`/`cold_start` fallbacks.
- **Create** `backend/app/aegis_v1/phoenix_mcp.py` — the MCP stdio fetch helper (`fetch_slice_traces()`), promoted from the spike.
- **Create** `backend/app/learning/run_live.py` — live coordinator CLI entrypoint.
- **Create** `backend/app/learning/counterfactual.py` — the MCP-off counterfactual harness (pure delta + gated live toggle).
- **Create** `backend/app/evals/part_a/calibration.py` — Cohen's κ judge-vs-gold calibration.
- **Create** fixtures `backend/tests/fixtures/phoenix/{spans_sample.json,annotations_sample.json,traces_sample.json}` (recorded in Task 0).
- **Create** tests `backend/tests/unit/learning/test_judge_adapter.py`, `test_phoenix_live_transforms.py`, `test_counterfactual.py`; `backend/tests/unit/aegis_v1/test_phoenix_summary_transform.py`; `backend/tests/unit/evals/test_calibration.py`; and gated `backend/tests/integration/test_live_phoenix.py`, `test_live_learning_loop.py`.
- **Create** `docs/demo/2026-06-XX-mcp-loadbearing-capture-checklist.md` (Task 7).

---

## Task 0: Resolve Phoenix MCP auth + record fixtures (PREREQ, credential-gated runbook)

The `backend/test_mcp_standalone.py` spike connects to `@arizeai/phoenix-mcp` but `list-traces` returned an auth/version error (see `agent-handoffs.md`). Fix auth, confirm reads, and **record real payloads as fixtures** — those fixtures make every downstream transform offline-testable forever.

- [ ] **Step 1** — In the env, set `PHOENIX_API_KEY`, `PHOENIX_HOST=https://app.phoenix.arize.com`, and (if Arize Cloud needs it) `PHOENIX_CLIENT_HEADERS="api_key=$PHOENIX_API_KEY"` and `PHOENIX_PROJECT=aegis-hackathon`. Re-run the spike: `cd backend && env UV_CACHE_DIR=/tmp/uv-cache uv run python test_mcp_standalone.py`. Acceptance: it lists tools AND a `get-spans` (or `list-datasets`) call returns without auth error.
- [ ] **Step 2** — First produce real spans: run a few benchmark cases through `run_evaluated_case` with the `OtelPhoenixRecorder` so tagged spans + annotations exist in `aegis-hackathon`. (`cd backend && env UV_CACHE_DIR=/tmp/uv-cache uv run python -m app.learning.run_live --record-only` — added in Task 4, or a one-off script.)
- [ ] **Step 3** — Call `get-spans` + `get-span-annotations` for the slice and **save the raw JSON** to `backend/tests/fixtures/phoenix/spans_sample.json` and `annotations_sample.json`; save a `list-traces`/`get-trace` payload to `traces_sample.json`. Redact nothing structural — these pin the real column/field names the transforms parse.
- [ ] **Step 4** — Document the working auth recipe in `.env.example` (uncomment + annotate the exact vars) and in a comment atop `phoenix_mcp.py`. Commit the fixtures + `.env.example`.

```bash
git add backend/tests/fixtures/phoenix/ .env.example
git commit -m "chore(phoenix): resolve MCP auth + record live span/annotation fixtures

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

> If Step 1 cannot be made to work against Arize Cloud, fall back to the **Phoenix client** (`px.Client()`, already used by `OtelPhoenixRecorder.annotate`) for reads in Tasks 2–3 and record the fixtures from its dataframes instead. The transforms (the tested part) are identical either way; only the fetch wrapper changes. Record this decision in the handoff.

---

## Task 1: `PanelJudgeAdapter` — panel → `judge_client.score()` (TDD, fully OFFLINE)

**Files:** Create `backend/app/learning/judge_adapter.py`; Test `backend/tests/unit/learning/test_judge_adapter.py`.

This is the deferred glue that makes `LiveExperimentRunner` (already in `experiment.py`) runnable: it adapts the Part-A panel to the `judge_client.score(case, appeal_letter) -> {dimension_scores, hard_gate_pass, simulator_verdict?}` contract. It is **fully offline-testable** with `OfflineHeuristicJudgeClient`.

- [ ] **Step 1: Write the failing test** — `backend/tests/unit/learning/test_judge_adapter.py`:

```python
import json
from pathlib import Path

from app.learning.judge_adapter import PanelJudgeAdapter

REPO = Path(__file__).resolve().parents[4]
CASE = json.loads((REPO / "eval" / "cases" / "drafts" / "case_01_cigna_mednec.json").read_text())
LETTER = ("I am appealing the denial of the Intensive Outpatient Program. The denial states the "
          "member is medically stable, yet the record documents six months of failed weekly therapy "
          "and daily compulsions causing job loss. Requested action: overturn the denial. "
          "Not legal or medical advice. Draft assistance only.")


def test_adapter_returns_score_dict_with_five_dims_and_hard_gate():
    out = PanelJudgeAdapter().score(case=CASE, appeal_letter=LETTER)  # default offline heuristic judge
    assert set(out["dimension_scores"]) >= {
        "grounding", "appeal_vector_capture", "case_specific_clinical_rebuttal",
        "evidence_completeness", "persuasive_coherence"}
    assert isinstance(out["hard_gate_pass"], bool)
    assert all(v in (1, 3, 5) for v in out["dimension_scores"].values())


def test_adapter_hard_gate_fails_without_disclaimer():
    out = PanelJudgeAdapter().score(case=CASE, appeal_letter="Overturn this denial.")
    assert out["hard_gate_pass"] is False   # missing canonical disclaimer -> j1 FAIL
```

- [ ] **Step 2: Run to verify it fails** — `... pytest tests/unit/learning/test_judge_adapter.py -q` → ImportError.

- [ ] **Step 3: Implement** — `backend/app/learning/judge_adapter.py`:

```python
"""Adapt the Part-A judge panel to the ExperimentRunner judge_client.score() contract
(used by LiveExperimentRunner). Offline-testable with OfflineHeuristicJudgeClient;
inject GeminiJudgeClient for the live loop. The teacher packet (answer key) is built
here — judges legitimately see it; the drafter never calls this."""
from __future__ import annotations

from typing import Any


class PanelJudgeAdapter:
    name = "panel_judge_adapter"

    def __init__(self, judge_client: Any | None = None) -> None:
        self.judge_client = judge_client  # None -> run_panel uses OfflineHeuristicJudgeClient

    def score(self, *, case: dict[str, Any], appeal_letter: str,
              simulator_verdict: str | None = None) -> dict[str, Any]:
        from app.evals.part_a.panel import run_panel
        from app.evals.part_a.teacher_packet import build_teacher_grading_packet

        appeal_package = {"appeal_package_draft": {
            "appeal_letter": appeal_letter, "missing_evidence_checklist": [], "citations_used": []}}
        teacher = build_teacher_grading_packet(case)
        report = run_panel(appeal_package, teacher, judge_client=self.judge_client)
        return {
            "dimension_scores": dict(report.dimension_scores),
            "hard_gate_pass": report.verdict == "PASS",
            "simulator_verdict": simulator_verdict,
            "weighted_quality": report.weighted_quality,
        }
```

- [ ] **Step 4: Run to verify pass** — `... pytest tests/unit/learning/test_judge_adapter.py -q` → 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/learning/judge_adapter.py backend/tests/unit/learning/test_judge_adapter.py
git commit -m "feat(learning): PanelJudgeAdapter wiring the Part-A panel to score() (offline)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Live `phoenix_mcp_lookup` (T4.1) — pure summary (TDD offline) + gated MCP fetch

**Files:** Create `backend/app/aegis_v1/phoenix_mcp.py`; Modify `backend/app/aegis_v1/tools.py` (the `phoenix_mcp_lookup` body, ~269–302); Test `backend/tests/unit/aegis_v1/test_phoenix_summary_transform.py` (offline) + `backend/tests/integration/test_live_phoenix.py` (gated).

Split the tool into a **pure** `_summarize_traces(traces, *, insurer, denial_type, query) -> PhoenixSummary` (offline-tested with the Task-0 `traces_sample.json` fixture) and a gated MCP fetch. Keep the existing `disabled`/`cold_start` returns so the demo toggle still works.

- [ ] **Step 1: Write the failing offline test** — `backend/tests/unit/aegis_v1/test_phoenix_summary_transform.py`:

```python
from app.aegis_v1.tools import _summarize_traces


def test_summary_from_traces_marks_available_and_counts():
    traces = [
        {"weighted_quality": 0.8, "verdict": "PASS",
         "dimensions": {"appeal_vector_capture": {"score": 5, "improvement": ""}}},
        {"weighted_quality": 0.4, "verdict": "FAIL",
         "dimensions": {"appeal_vector_capture": {"score": 1,
                        "improvement": "did not rebut the specific stated flaw"}}},
    ]
    s = _summarize_traces(traces, insurer="Cigna", denial_type="medical_necessity", query="q")
    assert s.status == "available"
    assert s.similar_trace_count == 2
    assert s.failure_patterns                  # a laundered failure note surfaced
    assert "exploitable_weaknesses" not in s.model_dump_json()   # firewall holds


def test_summary_empty_traces_is_cold_start():
    s = _summarize_traces([], insurer="Cigna", denial_type="medical_necessity", query="q")
    assert s.status == "cold_start"
```

- [ ] **Step 2: Run to verify it fails** — `... pytest tests/unit/aegis_v1/test_phoenix_summary_transform.py -q` → ImportError (`_summarize_traces`).

- [ ] **Step 3: Implement the pure transform + gated fetch.** In `backend/app/aegis_v1/tools.py` add `_summarize_traces` (pure: count traces, derive top failure_patterns from the **laundered** `improvement` notes on low-scoring dimensions, success_traits from high-scoring ones — read ONLY the laundered annotation fields, never answer-key strings), and rewrite `phoenix_mcp_lookup` to: return `disabled` when `PHOENIX_MCP_ENABLED` is off (unchanged); else try `from app.aegis_v1.phoenix_mcp import fetch_slice_traces` → `_summarize_traces(...)`; on empty/error return the existing `cold_start`. Create `backend/app/aegis_v1/phoenix_mcp.py` with `fetch_slice_traces(insurer, denial_type, *, project, limit=20) -> list[dict]` (method-local `mcp`/`stdio_client` import, promoted from `test_mcp_standalone.py`, calling `get-spans` + `get-span-annotations` and joining them into the laundered-trace dicts `_summarize_traces` expects). The fetch never raises to the caller (returns `[]` on failure → cold_start), preserving graceful degradation.

```python
# sketch — in tools.py
def _summarize_traces(traces: list[dict], *, insurer: str, denial_type: str, query: str) -> PhoenixSummary:
    if not traces:
        return PhoenixSummary(status="cold_start", query=query, similar_trace_count=0,
                              failure_patterns=["No promoted Phoenix trace pattern for this slice yet."],
                              success_traits=["Use local corpus citations and clearly mark missing evidence."],
                              risk_flags=["phoenix_mcp_cold_start"])
    fails, wins = [], []
    for t in traces:
        for dim, rec in (t.get("dimensions") or {}).items():
            note = (rec or {}).get("improvement")
            if rec and rec.get("score") == 1 and note:
                fails.append(note)            # laundered note only
            if rec and rec.get("score") == 5:
                wins.append(f"strong {dim}")
    return PhoenixSummary(status="available", query=query, similar_trace_count=len(traces),
                          failure_patterns=list(dict.fromkeys(fails))[:5],
                          success_traits=list(dict.fromkeys(wins))[:5],
                          risk_flags=["phoenix_mcp_live"])
```

- [ ] **Step 4: Run offline test** — `... pytest tests/unit/aegis_v1/test_phoenix_summary_transform.py -q` → 2 passed. Confirm the whole offline suite still green.

- [ ] **Step 5: Gated live smoke test** — `backend/tests/integration/test_live_phoenix.py`: `pytestmark = skipif(not _creds_available())`; call `fetch_slice_traces("Cigna","medical_necessity",project="aegis-hackathon")` and assert it returns a list (≥0) without raising; call `phoenix_mcp_lookup(...)` and assert `status in {"available","cold_start"}`. (Skips cleanly here.)

- [ ] **Step 6: Commit**

```bash
git add backend/app/aegis_v1/tools.py backend/app/aegis_v1/phoenix_mcp.py \
        backend/tests/unit/aegis_v1/test_phoenix_summary_transform.py backend/tests/integration/test_live_phoenix.py
git commit -m "feat(aegis_v1): live phoenix_mcp_lookup over MCP (pure summary + gated fetch, T4.1)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `LivePhoenixLearningStore` — pure transforms (TDD offline) + gated read/write

**Files:** Create `backend/app/learning/phoenix_live.py`; Test `backend/tests/unit/learning/test_phoenix_live_transforms.py` (offline) + extend `backend/tests/integration/test_live_phoenix.py` (gated).

Implements the `PhoenixLearningStore` Protocol (in `store.py`) so the coordinator is unchanged. Pure transforms tested against the Task-0 fixtures; live fetch/write gated.

- [ ] **Step 1: Write the failing offline test** — `backend/tests/unit/learning/test_phoenix_live_transforms.py`:

```python
import json
from pathlib import Path

from app.learning.phoenix_live import rows_to_scored_runs
from app.learning.signal import FORBIDDEN_FIELDS

FIX = Path(__file__).resolve().parents[2] / "fixtures" / "phoenix"


def test_rows_to_scored_runs_parses_fixture_and_launders():
    spans = json.loads((FIX / "spans_sample.json").read_text())
    annotations = json.loads((FIX / "annotations_sample.json").read_text())
    runs = rows_to_scored_runs(spans, annotations)
    assert runs and all(r.case_id and r.slice for r in runs)
    assert all(0 <= r.weighted_quality <= 1 for r in runs)
    blob = "\n".join(r.model_dump_json() for r in runs)
    for forbidden in FORBIDDEN_FIELDS:
        assert forbidden not in blob          # INV-2: only laundered fields survive
```

(If Task 0 produced client-dataframe fixtures instead of MCP JSON, adapt the loader; the transform contract is unchanged.)

- [ ] **Step 2: Run to verify it fails** — `... pytest tests/unit/learning/test_phoenix_live_transforms.py -q` → ImportError.

- [ ] **Step 3: Implement** — `backend/app/learning/phoenix_live.py`: the pure `rows_to_scored_runs(spans: list[dict], annotations: list[dict]) -> list[ScoredRun]` (join spans↔annotations by span_id; read the slice/case_id/prompt_version/playbook_version from span metadata `aegis.*`; read per-dimension scores + hard-gate + weighted_quality + laundered `improvement` notes + simulator verdict from the `aegis_part_a_panel` annotation written by `laundered_signal`; **launder defensively** with the `signal._launder` rule), plus `LivePhoenixLearningStore` implementing the Protocol: `read_scored_runs` (method-local `phoenix as px` → `px.Client()` span+annotation query for `dataset_split`/`prompt_version`, then `rows_to_scored_runs`), `read_prompt_version`/`list_prompt_versions` (Phoenix Prompts registry `get-prompt-version`/`list-prompt-versions`, falling back to the git file `aegis_v1/prompts/<id>.md`), `register_promotion` (write the git file AND `upsert-prompt` + `add-prompt-version-tag`, then append the audit). All cloud imports method-local; constructor is offline-safe.

- [ ] **Step 4: Run offline test** — `... pytest tests/unit/learning/test_phoenix_live_transforms.py -q` → green.

- [ ] **Step 5: Gated live integration** — extend `test_live_phoenix.py` (skipif no creds): construct `LivePhoenixLearningStore`, call `read_scored_runs(dataset_split="benchmark_train")`, assert it returns `list[ScoredRun]` (≥0) and no `FORBIDDEN_FIELDS` in the serialized result. Construction-only assertion runs offline.

- [ ] **Step 6: Commit**

```bash
git add backend/app/learning/phoenix_live.py backend/tests/unit/learning/test_phoenix_live_transforms.py \
        backend/tests/integration/test_live_phoenix.py
git commit -m "feat(learning): LivePhoenixLearningStore (pure transforms offline-tested, gated I/O)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Live coordinator entrypoint `run_live.py` (gated runbook + offline construction test)

**Files:** Create `backend/app/learning/run_live.py`; Test (gated) `backend/tests/integration/test_live_learning_loop.py`.

- [ ] **Step 1** — `run_live.py`: a CLI that wires `LivePhoenixLearningStore` + `LiveExperimentRunner(dataset, GeminiDrafterClient(), PanelJudgeAdapter(GeminiJudgeClient()))` + `GeminiReflectionClient()` into `LearningCoordinator`, runs `optimize()` for a `--slice`, prints the `PromotionProposal` as a HITL card, and on `--promote --approver <name>` calls `coordinator.promote(...)`. Add `--record-only` (Task 0 Step 2: run N cases through `run_evaluated_case` with `OtelPhoenixRecorder` to seed spans). Seed dataset = the `benchmark_train`/`benchmark_holdout` cases.
- [ ] **Step 2 (offline)** — a unit/import test that constructs the CLI's object graph with the **in-memory** store + stub clients (no creds) and asserts `optimize()` returns a proposal — proving the wiring composes. (Reuses the Task-10 coordinator test pattern.)
- [ ] **Step 3 (gated)** — `test_live_learning_loop.py` (skipif no creds): a 1-round `optimize()` over a 2-case slice; assert a `PromotionProposal` with `before`/`after` composites is returned and no answer-key field appears in the proposal's serialized reflection inputs.
- [ ] **Step 4: Commit.**

---

## Task 5: MCP-off counterfactual harness — the headline demo (TDD offline + gated toggle)

**Files:** Create `backend/app/learning/counterfactual.py`; Test `backend/tests/unit/learning/test_counterfactual.py` (offline) + gated live block.

The submission thesis: disable Phoenix MCP → quality visibly drops. Make it a measured, repeatable harness.

- [ ] **Step 1: Write the failing offline test** — with a **fake** lookup returning a rich summary when "on" and the `disabled` summary when "off", and a fake scorer that rewards using `failure_patterns`, assert `run_counterfactual(...)` returns `{on_composite, off_composite, delta}` with `delta > 0` and `on_composite > off_composite`.
- [ ] **Step 2: Run → fail (ImportError).**
- [ ] **Step 3: Implement** `run_counterfactual(cases, *, drafter, judge_adapter, lookup_on, lookup_off) -> dict`: for each case, draft with the on-lookup vs the off-lookup phoenix_summary, score both via the judge adapter, aggregate composites, return the delta + per-case table. Pure over injected callables (so offline-testable); the live demo passes the real `phoenix_mcp_lookup` with `PHOENIX_MCP_ENABLED` true vs false.
- [ ] **Step 4: Run → pass.**
- [ ] **Step 5: Gated live block** (skipif no creds): run 2–3 cases real on/off; assert `delta >= 0` and log the numbers. (This produces the demo's quantified collapse.)
- [ ] **Step 6: Commit.**

---

## Task 6: κ≥0.6 judge calibration (TDD offline)

**Files:** Create `backend/app/evals/part_a/calibration.py`; Test `backend/tests/unit/evals/test_calibration.py`.

- [ ] **Step 1** — failing test: `cohens_kappa(judge_anchors, gold_anchors)` returns 1.0 on identical sequences, ~0 on independent, and `calibration_report(...)` flags `kappa < 0.6` as `"below_gate"`.
- [ ] **Step 2 → fail.**
- [ ] **Step 3** — implement `cohens_kappa` (weighted on the 1/3/5 scale) + `calibration_report(per_dimension_pairs) -> {kappa_by_dimension, gate_pass}`; a small CLI to compare a judge run against a teacher-anchored gold set (a handful of cases the PM/teacher scored). Pure math → fully offline-testable.
- [ ] **Step 4 → pass. Step 5: Commit.**

> Live use: once Gemini judges run, compute κ against the gold set; κ≥0.6 is the gate before any Gemini-judged efficacy number is treated as official (v1 §10, orientation gap #4).

---

## Task 7: Demo capture runbook (gated, manual)

**Files:** Create `docs/demo/2026-06-XX-mcp-loadbearing-capture-checklist.md`.

- [ ] Capture, in order: (1) the **MCP-off counterfactual** from Task 5 (same case, Phoenix on vs off, composite collapses) — the money shot; (2) an **emergent DENY→APPROVE**: a case the weak v1 drafter got DENY on, re-run after a promoted prompt flips the simulator to APPROVE *with hard gates passing* (never an APPROVE-with-failing-gate, INV-3); (3) the **Phoenix UI** showing tagged spans + the per-dimension annotations the loop learned from (proving INV-1's gradient is real). Note the exact commands (`run_live.py`, the counterfactual CLI, `PHOENIX_MCP_ENABLED` toggle) and the Phoenix project/URL. Commit the checklist; the recordings live wherever demo assets are kept.

---

## Done-When (acceptance)
- Offline cores (Tasks 1, 2-transform, 3-transform, 5, 6) are unit-tested and green on any machine; the full `tests/unit` suite stays green with no cloud/API call.
- On the credentialed machine: `phoenix_mcp_lookup` returns live `available` summaries; `LivePhoenixLearningStore.read_scored_runs` returns real `ScoredRun`s with the firewall intact; `run_live.py --slice ... ` produces a `PromotionProposal` from live Gemini + live Phoenix signal; the MCP-off counterfactual shows a measured composite drop; judge κ≥0.6 against the gold set.
- INV-1 holds live (empty `read_scored_runs` → no promotable candidate); INV-2 holds (no answer-key field in any laundered read / reflection input — tested on the fixtures); INV-3 holds (no APPROVE-with-failing-gate promotion).
- The Tier-2-optimized `drafter_v2/v3` prompts are the seed components for the live loop.

## Notes / risks
- **MCP auth is the critical-path unknown** (Task 0). The Phoenix-client fallback de-risks reads if the MCP server auth can't be settled; the `phoenix_mcp_lookup` tool should still go through MCP for the load-bearing demo framing — but if MCP reads are blocked, document the client fallback and keep the `PHOENIX_MCP_ENABLED` toggle wired to whichever path is live so the counterfactual still demonstrates.
- **Same-family judging** (Gemini judges Gemini) remains; Task 6's κ gate + the deterministic hard gates are the mitigation. A cross-family judge is out of scope (G1 abandoned).
- Keep cloud/SDK imports method-local everywhere so the offline suite and `import app.*` stay clean.
