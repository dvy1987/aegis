# Learning-Loop Substrate (F1–F7) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make the Heuristics self-improvement loop physically possible and observable — give the appeal agent an evolvable LLM drafter, move the insurer simulator out of the agent, capture all eval signal onto Phoenix, and join the pipeline + judge panel into one evaluated-run entrypoint — so a later Learning Coordinator (Plan 2) has a surface to evolve and a Phoenix signal to learn from.

**Architecture:** Introduce small dependency-injected **client protocols** (`DrafterLLMClient`, `PhoenixRecorder`) each with an **offline fake** + a **Gemini/Phoenix real impl**, so the whole loop is unit-testable with no GCP. The Student pipeline shrinks to 6 tools (simulator relocated to the eval layer). A new `run_evaluated_case()` runs Student → records the trace → runs the eval layer (judges + simulator) → annotates the trace with a **laundered** signal that never carries answer-key fields.

**Tech Stack:** Python 3.11, `uv`, Pydantic v2, `pytest`, Google ADK, `google-genai` (Vertex), `arize-phoenix` / `phoenix.otel`, `rank_bm25`.

**Scope:** This is **Plan 1 of 2**. It implements spec §6 fixes **F1, F2, F3, F4a, F6, F7**. The Learning Coordinator itself (spec §7 — per-dimension specialists + meta-merge + experiment harness + HITL approval), real Phoenix MCP *reads* (F5 + DEP-1), and live per-slice memory in `phoenix_mcp_lookup` (F4b) are **Plan 2**. Each task below produces a green test suite and a commit.

**Reference (spec):** `docs/specs/2026-05-30-learning-coordinator-design.md`. **Invariants carried in:** INV-2 (firewall), INV-3 (optimize quality not verdict — relevant to what we annotate), INV-4 (weak-but-improvable), INV-6 (honesty).

**Conventions for every task:**
- Run tests with: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest <path> -q` from `backend/`.
- No GCP on the dev machine: real Gemini/Phoenix impls are written and unit-tested **through their interface with fakes**; live calls are integration-tested in a later GCP session, not here.
- Commit message convention matches the repo (short imperative subject).

---

## File Structure

**New files**
- `backend/app/aegis_v1/prompts/drafter_v1.md` — the deliberately-weak starting drafter system prompt (INV-4). (Part A prompts are colocated with the `aegis_v1` backend, matching the `case_generator` pattern; the Part B swarm prompts live under `backend/app/aegis_swarm/prompts/`. The legacy shared `backend/src/prompts/` dir was retired during Task 1.)
- `backend/app/aegis_v1/drafter_client.py` — `DrafterLLMClient` protocol, `StubDrafterClient` (offline), `GeminiDrafterClient` (prod).
- `backend/app/aegis_v1/guardrails.py` — deterministic post-filter (disclaimer/citation/no-exclamation/schema) applied to every draft.
- `backend/app/evals/part_a/recorder.py` — `PhoenixRecorder` protocol, `InMemoryPhoenixRecorder` (offline), `OtelPhoenixRecorder` (prod), and `laundered_signal()`.
- `backend/app/evals/part_a/evaluated_run.py` — `EvaluatedRun` schema + `run_evaluated_case()` (joins Student → record → eval layer → annotate).
- `playbooks/README.md` — versioned-playbook convention (F4a).
- Tests: `backend/tests/unit/aegis_v1/test_drafter_client.py`, `test_guardrails.py`; `backend/tests/unit/evals/test_recorder.py`, `test_evaluated_run.py`, `test_firewall.py`; modify `backend/tests/unit/agent/test_aegis_v1_agent.py`.

**Modified files**
- `backend/app/aegis_v1/tools.py` — `drafter()` becomes client-driven + guardrailed; `simulator()` removed from this module's tool set (moves to eval layer caller).
- `backend/app/aegis_v1/agent.py` — tool list 7→6 (drop `simulator`); instruction lists 6 tools.
- `backend/app/aegis_v1/pipeline.py` — drop the `simulator()` call; `AppealPackage` no longer carries `simulator_result`.
- `backend/app/aegis_v1/schemas.py` — `AppealPackage.simulator_result` removed (simulator result now lives on `EvaluatedRun`).

**Ownership boundaries:** `drafter_client.py` = "how do we get letter prose from a model (or a fake)". `guardrails.py` = "make any draft safe + schema-valid, deterministically". `recorder.py` = "write runs + laundered eval signal to Phoenix (or memory)". `evaluated_run.py` = "orchestrate one scored run end-to-end". Each is independently testable.

---

## Task 1: Weak drafter prompt + `DrafterLLMClient` protocol + offline stub

**Files:**
- Create: `backend/app/aegis_v1/prompts/drafter_v1.md`
- Create: `backend/app/aegis_v1/drafter_client.py`
- Test: `backend/tests/unit/aegis_v1/test_drafter_client.py`

- [x] **Step 1: Write the weak starting prompt** (INV-4 — thin strategy, still safe/structured)

Create `backend/app/aegis_v1/prompts/drafter_v1.md`:

```markdown
# Drafter — v1 (weak baseline)

You write a US commercial health-insurance appeal letter from the parsed case,
the retrieved local-corpus citations, the loaded playbook tactics, and the
Phoenix-memory summary. This is the deliberately weak baseline: be competent,
structured, and safe, but do NOT invent advanced strategy. Use only the inputs
provided.

Write a single appeal letter with: a one-line statement of what is being
appealed, the denial reason restated, a brief basis for appeal drawn from the
playbook tactics, the local citations, and a clear requested action. Keep a calm
professional tone. Do not use exclamation marks. Do not promise the appeal will
win. Do not invent statutes, policy text, or citations beyond those provided.
```

- [x] **Step 2: Write the failing test**

Create `backend/tests/unit/aegis_v1/test_drafter_client.py`:

```python
from app.aegis_v1.drafter_client import DrafterLLMClient, StubDrafterClient


def test_stub_client_is_a_drafter_llm_client():
    client: DrafterLLMClient = StubDrafterClient()
    assert client.name == "stub_drafter"


def test_stub_client_returns_deterministic_letter_body_from_inputs():
    client = StubDrafterClient()
    body = client.draft(
        prompt="ignored in stub",
        parsed_case={"insurer": "Cigna", "service_or_procedure": "TMS",
                     "cited_denial_reason": "not medically necessary",
                     "clinical_context": "failed two SSRIs"},
        citations=[{"corpus_doc_id": "erisa_503.md", "title": "ERISA", "quote": "full and fair review"}],
        playbook={"tactics": ["Rebut the medical-necessity rationale."]},
        phoenix_summary={"success_traits": ["cite local corpus"]},
    )
    assert "Cigna" in body
    assert "TMS" in body
    # deterministic: same inputs -> same output
    again = client.draft("ignored", {"insurer": "Cigna", "service_or_procedure": "TMS",
                                     "cited_denial_reason": "not medically necessary",
                                     "clinical_context": "failed two SSRIs"},
                         [{"corpus_doc_id": "erisa_503.md", "title": "ERISA", "quote": "full and fair review"}],
                         {"tactics": ["Rebut the medical-necessity rationale."]},
                         {"success_traits": ["cite local corpus"]})
    assert body == again
```

- [x] **Step 3: Run test to verify it fails**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1/test_drafter_client.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.aegis_v1.drafter_client'`.

- [x] **Step 4: Implement the protocol + stub**

Create `backend/app/aegis_v1/drafter_client.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


PROMPT_DIR = Path(__file__).resolve().parent / "prompts"  # Part A prompts colocated with aegis_v1


def load_drafter_prompt(version: str = "drafter_v1") -> str:
    return (PROMPT_DIR / f"{version}.md").read_text(encoding="utf-8")


class DrafterLLMClient(Protocol):
    name: str

    def draft(
        self,
        prompt: str,
        parsed_case: dict[str, Any],
        citations: list[dict[str, Any]],
        playbook: dict[str, Any],
        phoenix_summary: dict[str, Any],
    ) -> str:
        """Return the appeal-letter body text (no schema wrapping)."""


class StubDrafterClient:
    """Deterministic offline drafter for tests/dry-runs. NOT for benchmarks."""

    name = "stub_drafter"

    def draft(self, prompt, parsed_case, citations, playbook, phoenix_summary) -> str:
        insurer = parsed_case.get("insurer", "the insurer")
        service = parsed_case.get("service_or_procedure", "the requested service")
        reason = parsed_case.get("cited_denial_reason", "the stated reason")
        tactics = " ".join(playbook.get("tactics", [])[:2])
        cites = "; ".join(
            f"{c.get('title','')} ({c.get('corpus_doc_id','')})" for c in citations[:3]
        )
        context = parsed_case.get("clinical_context", "")
        return (
            f"To the appeals reviewer: I am appealing {insurer}'s denial of {service}. "
            f"The denial rests on: {reason}. {('Clinical context: ' + context + '. ') if context else ''}"
            f"Basis for appeal: {tactics} "
            f"Supporting sources: {cites or 'none retrieved'}. "
            f"Requested action: please conduct a full and fair review and have a "
            f"qualified reviewer reassess whether the service meets plan criteria."
        )
```

- [x] **Step 5: Run test to verify it passes**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1/test_drafter_client.py -q`
Expected: PASS (2 passed).

- [x] **Step 6: Commit**

```bash
git add backend/app/aegis_v1/prompts/drafter_v1.md backend/app/aegis_v1/drafter_client.py backend/tests/unit/aegis_v1/test_drafter_client.py
git commit -m "feat(aegis_v1): add weak drafter prompt + DrafterLLMClient protocol with offline stub"
```

---

## Task 2: Deterministic guardrail post-filter

The LLM may omit the disclaimer, add an exclamation mark, or cite something not retrieved. The guardrail makes **any** letter body safe + schema-valid deterministically (INV — safety not at the LLM's mercy).

**Files:**
- Create: `backend/app/aegis_v1/guardrails.py`
- Test: `backend/tests/unit/aegis_v1/test_guardrails.py`

- [x] **Step 1: Write the failing test**

Create `backend/tests/unit/aegis_v1/test_guardrails.py`:

```python
from app.aegis_v1.guardrails import apply_guardrails
from app.aegis_v1.tools import DISCLAIMER


def test_guardrails_inject_disclaimer_when_missing():
    out = apply_guardrails("Please review this appeal.", allowed_doc_ids={"erisa_503.md"})
    assert DISCLAIMER.lower() in out.lower()


def test_guardrails_strip_exclamation_marks():
    out = apply_guardrails("Approve this now!", allowed_doc_ids=set())
    assert "!" not in out


def test_guardrails_soften_guarantee_language():
    out = apply_guardrails("This appeal will win.", allowed_doc_ids=set())
    assert "will win" not in out.lower()
```

- [x] **Step 2: Run test to verify it fails**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1/test_guardrails.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.aegis_v1.guardrails'`.

- [x] **Step 3: Implement guardrails**

Create `backend/app/aegis_v1/guardrails.py`:

```python
from __future__ import annotations

import re

from app.aegis_v1.tools import DISCLAIMER

_GUARANTEE_RE = re.compile(r"\b(will win|guaranteed(?:\s+to)?\s+(?:win|overturn|approve))\b", re.IGNORECASE)


def apply_guardrails(letter_body: str, allowed_doc_ids: set[str]) -> str:
    """Make any LLM letter body deterministically safe.

    - guarantee/win-claim language softened
    - exclamation marks removed
    - canonical disclaimer ensured (prepended if missing)
    Citation enforcement is handled structurally in the drafter (only
    `allowed_doc_ids` are attached to `citations_used`); this filter scrubs the
    prose. `allowed_doc_ids` is accepted for future prose-citation scrubbing.
    """
    text = _GUARANTEE_RE.sub("may support the request", letter_body)
    text = text.replace("!", ".")
    if DISCLAIMER.lower() not in text.lower():
        text = f"{DISCLAIMER} This is a draft for review by a person before filing.\n\n{text}"
    return text.strip()
```

- [x] **Step 4: Run test to verify it passes**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1/test_guardrails.py -q`
Expected: PASS (3 passed).

- [x] **Step 5: Commit**

```bash
git add backend/app/aegis_v1/guardrails.py backend/tests/unit/aegis_v1/test_guardrails.py
git commit -m "feat(aegis_v1): deterministic guardrail post-filter (disclaimer/no-exclaim/no-guarantee)"
```

---

## Task 3: Rewrite `drafter()` to be client-driven + guardrailed (F1)

**Files:**
- Modify: `backend/app/aegis_v1/tools.py:306-373` (the `drafter` function)
- Test: `backend/tests/unit/aegis_v1/test_drafter_client.py` (add cases)

- [x] **Step 1: Add the failing test**

Append to `backend/tests/unit/aegis_v1/test_drafter_client.py`:

```python
from app.aegis_v1.tools import DISCLAIMER, drafter
from app.aegis_v1.drafter_client import StubDrafterClient


def test_drafter_uses_injected_client_and_applies_guardrails():
    parsed = {"insurer": "Cigna", "service_or_procedure": "TMS",
              "diagnosis_summary": "treatment-resistant depression",
              "cited_denial_reason": "not medically necessary",
              "clinical_context": "failed two SSRIs", "missing_facts": ["plan_document_language"]}
    retrieval = {"query": "x", "hits": [
        {"corpus_doc_id": "erisa_503.md", "title": "ERISA 503", "quote": "full and fair review", "relevance_score": 1.0}]}
    playbook = {"insurer": "Cigna", "denial_type": "medical_necessity", "version": "cold-start",
                "status": "missing", "tactics": ["Rebut the rationale."], "required_evidence": ["clinical notes"],
                "risk_flags": ["playbook_cold_start"]}
    phoenix = {"status": "cold_start", "query": "q", "similar_trace_count": 0,
               "failure_patterns": [], "success_traits": [], "risk_flags": ["phoenix_mcp_cold_start"]}

    out = drafter(parsed, retrieval, playbook, phoenix, client=StubDrafterClient())

    assert DISCLAIMER.lower() in out["appeal_letter"].lower()   # guardrail injected
    assert out["citations_used"][0]["corpus_doc_id"] == "erisa_503.md"  # only retrieved cites attached
    assert "weak_prompt_v1" in out["risk_flags"]
    assert out["safety_disclaimer"] == DISCLAIMER
```

- [x] **Step 2: Run test to verify it fails**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1/test_drafter_client.py -q`
Expected: FAIL — `drafter()` has no `client` keyword argument (TypeError).

- [x] **Step 3: Rewrite `drafter()`**

In `backend/app/aegis_v1/tools.py`, replace the whole `drafter(...)` function (currently lines 306–373) with:

```python
def drafter(
    parsed_case: dict[str, Any],
    retrieval_results: dict[str, Any],
    playbook: dict[str, Any],
    phoenix_summary: dict[str, Any],
    client: "DrafterLLMClient | None" = None,
) -> dict[str, Any]:
    """Draft the appeal package. The letter PROSE is produced by an evolvable
    LLM (or offline stub); structure, citations, and safety are deterministic."""

    from app.aegis_v1.drafter_client import (
        GeminiDrafterClient,
        DrafterLLMClient,
        load_drafter_prompt,
    )
    from app.aegis_v1.guardrails import apply_guardrails

    case = ParsedCase.model_validate(parsed_case)
    retrieval = RetrievalResult.model_validate(retrieval_results)
    loaded_playbook = Playbook.model_validate(playbook)
    phoenix = PhoenixSummary.model_validate(phoenix_summary)
    citations = retrieval.hits[:3]

    active: DrafterLLMClient = client or GeminiDrafterClient()
    raw_body = active.draft(
        prompt=load_drafter_prompt("drafter_v1"),
        parsed_case=case.model_dump(),
        citations=[c.model_dump() for c in citations],
        playbook=loaded_playbook.model_dump(),
        phoenix_summary=phoenix.model_dump(),
    )
    allowed_doc_ids = {hit.corpus_doc_id for hit in citations}
    letter = apply_guardrails(raw_body, allowed_doc_ids=allowed_doc_ids)

    evidence_items = list(
        dict.fromkeys(case.missing_facts + loaded_playbook.required_evidence)
    )
    tactic_text = " ".join(loaded_playbook.tactics[:2])

    risk_flags = ["weak_prompt_v1"]
    risk_flags.extend(loaded_playbook.risk_flags)
    risk_flags.extend(
        flag for flag in phoenix.risk_flags if not flag.startswith("case_id:")
    )
    if not citations:
        risk_flags.append("no_corpus_citations")

    draft = AppealDraft(
        case_summary=(
            f"{case.insurer} denied {case.service_or_procedure} for "
            f"{case.diagnosis_summary}."
        ),
        denial_grounds_interpreted=case.cited_denial_reason,
        appeal_strategy=tactic_text or "Use a conservative medical-record appeal.",
        appeal_letter=letter,
        citations_used=citations,
        missing_evidence_checklist=evidence_items,
        risk_flags=sorted(set(risk_flags)),
        safety_disclaimer=DISCLAIMER,
    )
    return draft.model_dump()
```

(`GeminiDrafterClient` lands in Task 4; the import is lazy so offline tests passing `client=StubDrafterClient()` never touch it.)

- [x] **Step 4: Run test to verify it passes**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1/test_drafter_client.py -q`
Expected: PASS (all). The deterministic template is gone; prose now flows from the injected client.

- [x] **Step 5: Commit**

```bash
git add backend/app/aegis_v1/tools.py backend/tests/unit/aegis_v1/test_drafter_client.py
git commit -m "feat(aegis_v1): drafter is now LLM-driven (injected client) with deterministic guardrails"
```

---

## Task 4: `GeminiDrafterClient` (production drafter path)

Mirrors the existing `GeminiJudgeClient`/`simulator()` Vertex usage. Unit-tested for *construction + prompt assembly*; live generation is integration-tested in a GCP session.

**Files:**
- Modify: `backend/app/aegis_v1/drafter_client.py`
- Test: `backend/tests/unit/aegis_v1/test_drafter_client.py` (add a construction test)

- [x] **Step 1: Add the failing test**

Append to `backend/tests/unit/aegis_v1/test_drafter_client.py`:

```python
from app.aegis_v1.drafter_client import GeminiDrafterClient


def test_gemini_drafter_client_constructs_with_default_model(monkeypatch):
    monkeypatch.delenv("AEGIS_DRAFTER_MODEL", raising=False)
    client = GeminiDrafterClient()
    assert client.name == "gemini"
    assert client.model == "gemini-3.1-pro"
    assert client.location == "global"
```

- [x] **Step 2: Run test to verify it fails**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1/test_drafter_client.py::test_gemini_drafter_client_constructs_with_default_model -q`
Expected: FAIL — `ImportError: cannot import name 'GeminiDrafterClient'`.

- [x] **Step 3: Implement `GeminiDrafterClient`**

Append to `backend/app/aegis_v1/drafter_client.py`:

```python
import json
import os
from typing import Any


def _build_contents(prompt, parsed_case, citations, playbook, phoenix_summary) -> str:
    context = {
        "parsed_case": parsed_case,
        "citations": citations,
        "playbook": playbook,
        "phoenix_summary": phoenix_summary,
    }
    return f"{prompt}\n\nCONTEXT JSON:\n{json.dumps(context, indent=2, default=str)}"


class GeminiDrafterClient:
    """Vertex/Gemini-backed drafter. Returns the appeal-letter body text."""

    name = "gemini"

    def __init__(self, model: str | None = None, location: str = "global") -> None:
        self.model = model or os.environ.get("AEGIS_DRAFTER_MODEL", "gemini-3.1-pro")
        self.location = location

    def draft(self, prompt, parsed_case, citations, playbook, phoenix_summary) -> str:
        from google import genai
        from google.genai import types

        client = genai.Client(vertexai=True, location=self.location)
        response = client.models.generate_content(
            model=self.model,
            contents=_build_contents(prompt, parsed_case, citations, playbook, phoenix_summary),
            config=types.GenerateContentConfig(temperature=0.3),
        )
        return response.text or ""
```

- [x] **Step 4: Run test to verify it passes**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1/test_drafter_client.py -q`
Expected: PASS (all). No live call is made (only construction is tested).

- [x] **Step 5: Commit**

```bash
git add backend/app/aegis_v1/drafter_client.py backend/tests/unit/aegis_v1/test_drafter_client.py
git commit -m "feat(aegis_v1): add GeminiDrafterClient production drafter path"
```

---

## Task 5: Relocate the Outcome Simulator out of the Student pipeline (F7, D11)

The Student must stop simulating its own outcome. Drop `simulator` from the agent's 7 tools (→6) and from `run_aegis_v1_pipeline`; remove `simulator_result` from `AppealPackage`. The simulator still exists in `tools.py` and will be called by the eval layer in Task 7.

**Files:**
- Modify: `backend/app/aegis_v1/schemas.py:110-117` (`AppealPackage`)
- Modify: `backend/app/aegis_v1/pipeline.py:55-99`
- Modify: `backend/app/aegis_v1/agent.py:21-83`
- Modify: `backend/tests/unit/agent/test_aegis_v1_agent.py`

- [x] **Step 1: Update the contract test to expect 6 tools (write the failing expectation)**

In `backend/tests/unit/agent/test_aegis_v1_agent.py`, change the tool-set assertions so the expected set is exactly the 6 below and `simulator` is asserted absent:

```python
EXPECTED_TOOLS = {
    "case_parser", "corpus_retrieval", "phoenix_mcp_lookup",
    "playbook_loader", "drafter", "self_check",
}

def test_root_agent_is_aegis_v1_with_required_tools():
    from app.aegis_v1.agent import root_agent, AEGIS_V1_TOOL_NAMES
    assert AEGIS_V1_TOOL_NAMES == EXPECTED_TOOLS
    tool_names = {t.func.__name__ for t in root_agent.tools}
    assert tool_names == EXPECTED_TOOLS
    assert "simulator" not in tool_names
```

Also update `test_root_agent_instruction_requires_ordered_tool_flow_and_disclaimer` to expect the 6-step order ending at `self_check` (no `simulator` line).

- [x] **Step 2: Run test to verify it fails**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/agent/test_aegis_v1_agent.py -q`
Expected: FAIL — current agent still has 7 tools including `simulator`.

- [x] **Step 3: Remove `simulator` from the agent**

In `backend/app/aegis_v1/agent.py`:
- Drop `simulator` from the `from app.aegis_v1.tools import (...)` import.
- `AEGIS_V1_TOOL_NAMES` = the 6 names above (remove `"simulator"`).
- In `AEGIS_V1_INSTRUCTION`, change the numbered list to 6 steps ending at `6. self_check`; delete the `7. simulator` line. Remove the sentence telling it to return `simulator` output.
- Remove `simulator` from the `tools=[...]` list.

- [x] **Step 4: Remove the simulator call from the pipeline + AppealPackage**

In `backend/app/aegis_v1/pipeline.py`, delete the `sim = simulator(...)` block (lines ~66–70) and the `simulator_result=sim,` argument to `AppealPackage(...)`. Remove `simulator` from the tools import.

In `backend/app/aegis_v1/schemas.py`, delete the `simulator_result: SimulatorResult` line from `AppealPackage` (lines ~110–117). Keep the `SimulatorResult` model itself (the eval layer still uses it).

- [x] **Step 5: Run the agent + pipeline tests**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/agent/test_aegis_v1_agent.py tests/unit/agent/test_aegis_v1_tools.py -q`
Expected: PASS. (If `test_aegis_v1_tools.py` asserts `AppealPackage.simulator_result`, update that assertion to read the simulator result from the eval layer instead — it is no longer on the package.)

- [x] **Step 6: Commit**

```bash
git add backend/app/aegis_v1/agent.py backend/app/aegis_v1/pipeline.py backend/app/aegis_v1/schemas.py backend/tests/unit/agent/test_aegis_v1_agent.py
git commit -m "refactor(aegis_v1): move Outcome Simulator out of Student pipeline (6 tools); drop simulator_result from AppealPackage"
```

---

## Task 6: `PhoenixRecorder` protocol + in-memory fake + `laundered_signal()` (F2a, INV-2)

`laundered_signal()` is the firewall-safe projection of a `PanelReport`: scores, gates, reasoning, **improvement notes**, and only those `evidence_quotes` that appear verbatim in the appeal letter (so no answer-key string leaks).

**Files:**
- Create: `backend/app/evals/part_a/recorder.py`
- Test: `backend/tests/unit/evals/test_recorder.py`

- [x] **Step 1: Write the failing test**

Create `backend/tests/unit/evals/test_recorder.py`:

```python
from app.evals.part_a.recorder import InMemoryPhoenixRecorder, laundered_signal
from app.evals.part_a.schemas import JudgeResult, PanelReport


def _panel_with_leaky_quote():
    return PanelReport(
        case_id="c1", verdict="PASS", weighted_quality=0.6,
        hard_gate_failures=[], promotion_blockers=[],
        dimension_scores={"appeal_vector_capture": 3},
        judge_results={"appeal_vector_capture": JudgeResult(
            dimension="appeal_vector_capture", reasoning="missed the embedded flaw",
            score=3, confidence=0.6,
            evidence_quotes=["SECRET expected vector", "full and fair review"],
            improvement="Attack the specific denial defect.")},
        weights={"appeal_vector_capture": 0.25}, risk_flags=[], metadata={})


def test_laundered_signal_drops_quotes_not_in_letter():
    letter = "We request a full and fair review of the denial."
    out = laundered_signal(_panel_with_leaky_quote(), appeal_letter=letter)
    dim = out["dimensions"]["appeal_vector_capture"]
    assert dim["improvement"] == "Attack the specific denial defect."
    assert "full and fair review" in dim["evidence_quotes"]
    assert "SECRET expected vector" not in dim["evidence_quotes"]   # firewall


def test_in_memory_recorder_round_trips_run_and_annotation():
    rec = InMemoryPhoenixRecorder()
    ref = rec.record_run({"run_id": "r1"}, {"case_id": "c1", "insurer": "Cigna"})
    rec.annotate(ref, {"weighted_quality": 0.6})
    stored = rec.get(ref)
    assert stored["metadata"]["insurer"] == "Cigna"
    assert stored["annotations"]["weighted_quality"] == 0.6
```

- [x] **Step 2: Run test to verify it fails**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/evals/test_recorder.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.evals.part_a.recorder'`.

- [x] **Step 3: Implement the recorder + laundering**

Create `backend/app/evals/part_a/recorder.py`:

```python
from __future__ import annotations

from typing import Any, Protocol

from app.evals.part_a.schemas import PanelReport


def laundered_signal(panel: PanelReport, appeal_letter: str) -> dict[str, Any]:
    """Firewall-safe projection of a PanelReport for the Optimizer (INV-2).

    Keeps scores, gates, reasoning, improvement notes. Keeps an evidence quote
    ONLY if it appears verbatim in the agent's own letter — so teacher-only
    answer-key strings (e.g. expected appeal vectors) can never leak.
    """
    letter = appeal_letter or ""
    dimensions: dict[str, Any] = {}
    for name, result in panel.judge_results.items():
        safe_quotes = [q for q in result.evidence_quotes if q and q in letter]
        dimensions[name] = {
            "score": result.score,
            "reasoning": result.reasoning,
            "improvement": result.improvement,
            "evidence_quotes": safe_quotes,
        }
    return {
        "case_id": panel.case_id,
        "verdict": panel.verdict,
        "weighted_quality": panel.weighted_quality,
        "hard_gate_failures": panel.hard_gate_failures,
        "promotion_blockers": panel.promotion_blockers,
        "dimension_scores": panel.dimension_scores,
        "weights": panel.weights,
        "dimensions": dimensions,
    }


class PhoenixRecorder(Protocol):
    name: str

    def record_run(self, appeal_package: dict[str, Any], trace_metadata: dict[str, Any]) -> str:
        """Persist one run; return a trace reference (e.g. span/trace id)."""

    def annotate(self, trace_ref: str, annotations: dict[str, Any]) -> None:
        """Attach laundered eval/sim signal to an existing run."""


class InMemoryPhoenixRecorder:
    """Offline fake implementing the PhoenixRecorder interface for tests/dry-runs."""

    name = "in_memory"

    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}
        self._seq = 0

    def record_run(self, appeal_package, trace_metadata) -> str:
        self._seq += 1
        ref = f"mem-trace-{self._seq}"
        self._runs[ref] = {
            "appeal_package": appeal_package,
            "metadata": dict(trace_metadata),
            "annotations": {},
        }
        return ref

    def annotate(self, trace_ref, annotations) -> None:
        self._runs[trace_ref]["annotations"].update(annotations)

    def get(self, trace_ref: str) -> dict[str, Any]:
        return self._runs[trace_ref]
```

- [x] **Step 4: Run test to verify it passes**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/evals/test_recorder.py -q`
Expected: PASS (2 passed).

- [x] **Step 5: Commit**

```bash
git add backend/app/evals/part_a/recorder.py backend/tests/unit/evals/test_recorder.py
git commit -m "feat(evals): PhoenixRecorder protocol + in-memory fake + firewall-safe laundered_signal"
```

---

## Task 7: `OtelPhoenixRecorder` (production Phoenix path) (F2b)

Writes a run as a span with tagged attributes and attaches eval annotations via `phoenix.Client().log_evaluations`. Construction-tested offline; live writes integration-tested in GCP.

**Files:**
- Modify: `backend/app/evals/part_a/recorder.py`
- Test: `backend/tests/unit/evals/test_recorder.py` (add construction test)

- [x] **Step 1: Add the failing test**

Append to `backend/tests/unit/evals/test_recorder.py`:

```python
from app.evals.part_a.recorder import OtelPhoenixRecorder


def test_otel_recorder_has_expected_name_and_project(monkeypatch):
    monkeypatch.setenv("PHOENIX_PROJECT_NAME", "default")
    rec = OtelPhoenixRecorder()
    assert rec.name == "otel_phoenix"
    assert rec.project_name == "default"
```

- [x] **Step 2: Run test to verify it fails**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/evals/test_recorder.py::test_otel_recorder_has_expected_name_and_project -q`
Expected: FAIL — `ImportError: cannot import name 'OtelPhoenixRecorder'`.

- [x] **Step 3: Implement `OtelPhoenixRecorder`**

Append to `backend/app/evals/part_a/recorder.py`:

```python
import os


class OtelPhoenixRecorder:
    """Production recorder: a tagged span per run + Phoenix eval annotations.

    Live span emission and `log_evaluations` are exercised in a GCP integration
    session; this class is unit-tested only for construction/config here.
    """

    name = "otel_phoenix"

    def __init__(self, project_name: str | None = None) -> None:
        self.project_name = project_name or os.environ.get("PHOENIX_PROJECT_NAME", "default")

    def record_run(self, appeal_package, trace_metadata) -> str:
        from opentelemetry import trace as otel_trace

        tracer = otel_trace.get_tracer("aegis.evaluated_run")
        with tracer.start_as_current_span("aegis_v1.evaluated_run") as span:
            for key, value in trace_metadata.items():
                span.set_attribute(f"aegis.{key}", str(value))
            span.set_attribute("aegis.run_id", str(appeal_package.get("run_id", "")))
            ctx = span.get_span_context()
            return format(ctx.span_id, "016x")

    def annotate(self, trace_ref, annotations) -> None:
        import pandas as pd
        import phoenix as px
        from phoenix.trace import SpanEvaluations

        df = pd.DataFrame([{"span_id": trace_ref, **annotations}])
        px.Client().log_evaluations(
            SpanEvaluations(eval_name="aegis_part_a_panel", dataframe=df)
        )
```

- [x] **Step 4: Run test to verify it passes**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/evals/test_recorder.py -q`
Expected: PASS (all). Imports inside methods keep the offline suite from importing pandas/phoenix.

- [x] **Step 5: Commit**

```bash
git add backend/app/evals/part_a/recorder.py backend/tests/unit/evals/test_recorder.py
git commit -m "feat(evals): OtelPhoenixRecorder production path (tagged span + log_evaluations)"
```

---

## Task 8: `EvaluatedRun` + `run_evaluated_case()` — join Student → record → eval → annotate (F3)

This is the closed evaluation loop in one entrypoint. Eval layer = judge panel **and** the relocated simulator. Annotations written are the **laundered** signal + the simulator verdict (INV-3: simulator verdict recorded as a guardrail/demo signal, never used as a reward here).

**Files:**
- Create: `backend/app/evals/part_a/evaluated_run.py`
- Test: `backend/tests/unit/evals/test_evaluated_run.py`

- [x] **Step 1: Write the failing test**

Create `backend/tests/unit/evals/test_evaluated_run.py`:

```python
from app.evals.part_a.evaluated_run import run_evaluated_case
from app.evals.part_a.recorder import InMemoryPhoenixRecorder
from app.aegis_v1.drafter_client import StubDrafterClient
from app.evals.part_a.llm_judges import OfflineHeuristicJudgeClient


def _case():
    return {
        "case_id": "case_demo", "insurer": "Cigna", "denial_type": "Medical Necessity",
        "denial_letter_text": "We denied coverage for TMS as not medically necessary.",
        "clinical_context": "Patient failed two SSRIs; severe treatment-resistant depression.",
        "patient_profile": {"plan_funding_type": "fully_insured",
                            "diagnosis": "treatment-resistant depression",
                            "treatment_requested": "TMS"},
        "denial_pattern_sources": [], "synthetic_provenance": {"appeal_difficulty": {}},
    }


def test_run_evaluated_case_closes_the_loop_offline():
    rec = InMemoryPhoenixRecorder()
    result = run_evaluated_case(
        _case(),
        recorder=rec,
        drafter_client=StubDrafterClient(),
        judge_client=OfflineHeuristicJudgeClient(),
        run_simulator=False,   # no GCP in dev
    )
    assert result.appeal_package["trace_metadata"]["case_id"] == "case_demo"
    assert result.panel_report.verdict in {"PASS", "FAIL"}
    stored = rec.get(result.trace_ref)
    # laundered signal landed on the trace
    assert "weighted_quality" in stored["annotations"]
    assert "dimensions" in stored["annotations"]
```

- [x] **Step 2: Run test to verify it fails**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/evals/test_evaluated_run.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.evals.part_a.evaluated_run'`.

- [x] **Step 3: Implement the entrypoint**

Create `backend/app/evals/part_a/evaluated_run.py`:

```python
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.aegis_v1.drafter_client import DrafterLLMClient
from app.aegis_v1.pipeline import run_aegis_v1_pipeline
from app.evals.part_a.llm_judges import JudgeClient
from app.evals.part_a.panel import run_panel
from app.evals.part_a.recorder import PhoenixRecorder, laundered_signal
from app.evals.part_a.schemas import PanelReport
from app.evals.part_a.teacher_packet import build_teacher_grading_packet


class EvaluatedRun(BaseModel):
    appeal_package: dict[str, Any]
    panel_report: PanelReport
    simulator_result: dict[str, Any] | None = None
    trace_ref: str


def run_evaluated_case(
    case_obj: dict[str, Any],
    recorder: PhoenixRecorder,
    drafter_client: DrafterLLMClient | None = None,
    judge_client: JudgeClient | None = None,
    run_simulator: bool = True,
) -> EvaluatedRun:
    """Student → record run → eval layer (judges [+ simulator]) → annotate trace."""

    # 1. Student (blind to answer key): produce the appeal package.
    appeal_package = run_aegis_v1_pipeline(
        denial_text=case_obj.get("denial_letter_text", ""),
        clinical_context=case_obj.get("clinical_context", ""),
        case_id=case_obj.get("case_id", "interactive_case"),
        dataset_split=case_obj.get("dataset_split", "benchmark"),
        run_mode="benchmark",
        drafter_client=drafter_client,
    )

    # 2. Record the run trace (tagged metadata) BEFORE evaluation.
    trace_ref = recorder.record_run(appeal_package, appeal_package["trace_metadata"])

    # 3. Eval layer — independent of the Student.
    teacher = build_teacher_grading_packet(case_obj, appeal_package)
    panel_report = run_panel(appeal_package, teacher, judge_client=judge_client)

    simulator_result = None
    if run_simulator:
        from app.aegis_v1.tools import simulator
        simulator_result = simulator(
            parsed_case=appeal_package["parsed_case"],
            appeal_draft=appeal_package["appeal_package_draft"],
            self_check_result=appeal_package["self_check"],
        )

    # 4. Annotate the trace with the LAUNDERED signal + sim verdict (INV-2/INV-3).
    letter = appeal_package["appeal_package_draft"]["appeal_letter"]
    annotations = laundered_signal(panel_report, appeal_letter=letter)
    if simulator_result is not None:
        annotations["simulator_verdict"] = simulator_result["verdict"]
        annotations["simulator_score"] = simulator_result["score"]
    recorder.annotate(trace_ref, annotations)

    return EvaluatedRun(
        appeal_package=appeal_package,
        panel_report=panel_report,
        simulator_result=simulator_result,
        trace_ref=trace_ref,
    )
```

- [x] **Step 4: Thread `drafter_client` through the pipeline**

`run_aegis_v1_pipeline` must accept and forward `drafter_client`. In `backend/app/aegis_v1/pipeline.py`:
- Add parameter `drafter_client: "DrafterLLMClient | None" = None` to the signature.
- Change the `draft = drafter(...)` call to `draft = drafter(parsed_case=parsed, retrieval_results=retrieval, playbook=playbook, phoenix_summary=phoenix, client=drafter_client)`.

- [x] **Step 5: Run test to verify it passes**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/evals/test_evaluated_run.py -q`
Expected: PASS (1 passed). The loop closes fully offline.

- [x] **Step 6: Commit**

```bash
git add backend/app/evals/part_a/evaluated_run.py backend/app/aegis_v1/pipeline.py backend/tests/unit/evals/test_evaluated_run.py
git commit -m "feat(evals): run_evaluated_case joins Student->trace->judges[+sim]->laundered annotation"
```

---

## Task 9: Anti-Cheating Firewall enforcement test (F6, INV-2) + playbooks convention (F4a)

A build-breaking test that answer-key fields never reach the Student input or the laundered Optimizer signal; plus the `playbooks/` convention doc.

**Files:**
- Create: `backend/tests/unit/evals/test_firewall.py`
- Create: `playbooks/README.md`

- [x] **Step 1: Write the firewall test**

Create `backend/tests/unit/evals/test_firewall.py`:

```python
from app.evals.part_a.evaluated_run import run_evaluated_case
from app.evals.part_a.recorder import InMemoryPhoenixRecorder
from app.evals.part_a.teacher_packet import build_student_case_packet
from app.aegis_v1.drafter_client import StubDrafterClient
from app.evals.part_a.llm_judges import OfflineHeuristicJudgeClient

SECRET = "SECRET_EXPECTED_VECTOR_attack_the_peer_to_peer_failure"


def _case_with_answer_key():
    return {
        "case_id": "fw1", "insurer": "Cigna", "denial_type": "Medical Necessity",
        "denial_letter_text": "Denied: not medically necessary.",
        "clinical_context": "Failed two SSRIs.",
        "patient_profile": {"plan_funding_type": "fully_insured"},
        "denial_pattern_sources": [],
        "synthetic_provenance": {"appeal_difficulty": {
            "exploitable_weaknesses": [SECRET], "strong_defenses": [SECRET]}},
    }


def test_student_packet_excludes_answer_key():
    case = _case_with_answer_key()
    student = build_student_case_packet(case).model_dump()
    assert SECRET not in str(student)


def test_laundered_annotation_never_leaks_answer_key():
    rec = InMemoryPhoenixRecorder()
    run_evaluated_case(_case_with_answer_key(), recorder=rec,
                       drafter_client=StubDrafterClient(),
                       judge_client=OfflineHeuristicJudgeClient(),
                       run_simulator=False)
    ref = "mem-trace-1"
    assert SECRET not in str(rec.get(ref)["annotations"])   # firewall holds
```

- [x] **Step 2: Run test to verify it fails or passes**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/evals/test_firewall.py -q`
Expected: PASS if laundering (Task 6) is correct. If the laundered signal leaks `SECRET` (e.g. an unfiltered evidence quote), this FAILS — fix `laundered_signal()` until green. This test is the firewall's guardrail.

- [x] **Step 3: Document the playbooks convention**

Create `playbooks/README.md`:

```markdown
# Playbooks

Per-slice learned tactics, consumed by `backend/app/aegis_v1/tools.py:playbook_loader`.

- Filename (current/promoted): `<slug_insurer>__<denial_type>.json`
  e.g. `cigna__medical_necessity.json`. `playbook_loader` reads this file as the
  active version; the `version` field inside tracks the promoted version string.
- Archived versions: `archive/<slug_insurer>__<denial_type>__vN.json` (written by
  the Learning Coordinator on each promotion; git history is the audit trail).
- Cold start: when no current file exists, the loader returns a marked
  `status: "missing"` cold-start playbook — this is intentional for the weak v1.

Schema (matches `Playbook` in `aegis_v1/schemas.py`, plus optional learning fields):
{ "insurer", "denial_type", "version", "tactics": [], "required_evidence": [],
  "risk_flags": [], "dimension_targets": { "<tactic>": "<rubric_dimension>" },
  "provenance": { "experiment_id", "promoted_at", "approved_by" } }
```

- [x] **Step 4: Run the full unit suite for the touched areas**

Run: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1 tests/unit/evals -q`
Expected: PASS (all). This confirms the closed loop + firewall hold offline.

- [x] **Step 5: Commit**

```bash
git add backend/tests/unit/evals/test_firewall.py playbooks/README.md
git commit -m "test(evals): build-breaking firewall enforcement; docs: playbooks convention"
```

---

## Done-When (Plan 1 acceptance)

- Drafter prose comes from an injected `DrafterLLMClient` (stub offline / Gemini prod), guardrailed deterministically. The deterministic template is gone.
- The Student pipeline is 6 tools; the simulator runs only in the eval layer.
- `run_evaluated_case()` produces, for any case, an `AppealPackage` + `PanelReport` (+ optional simulator), and writes a **laundered** signal onto a Phoenix trace via a `PhoenixRecorder`.
- The firewall test proves no answer-key string reaches the Student or the laundered annotation.
- Entire suite is green offline (no GCP): `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/aegis_v1 tests/unit/evals tests/unit/agent -q`.

## Deferred to Plan 2 (Learning Coordinator)
- Per-dimension specialist optimizers + meta-merge (spec §7).
- Real Phoenix **reads** via MCP for signal acquisition + `phoenix_mcp_lookup` live per-slice memory (spec F4b/F5; **DEP-1** Arize MCP auth).
- Phoenix Experiments harness for candidate vs current on a frozen held-out set with a frozen judge config (spec §7.5).
- Part A HITL promotion gate (propose + experiment + human approve) and the Part B autonomous gates + ladder (spec §8).
- Live Gemini drafter + judges integration session (**DEP-2**).
```
