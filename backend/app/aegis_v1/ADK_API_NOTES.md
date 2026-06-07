# ADK 2.2 API verification (Phase 0)

Verified against `google-adk==2.2.0` in `backend/.venv` on 2026-06-07.

**Authoritative plan:** [docs/plans/2026-06-07-aegis-v1-adk-migration-plan-v2.md](../../../docs/plans/2026-06-07-aegis-v1-adk-migration-plan-v2.md) §3.4, §12.3–12.4.

## Phase 0 correction — Workflow

**Initial Phase 0 spike (wrong):** Looked for `google.adk.agents.workflow`, found `ModuleNotFoundError`, and concluded Workflow was not shipped in 2.2.0.

**Correct (verified):** `Workflow` **is** in 2.2.0 — it lives in **`google.adk.workflow`**, top-level re-export:

```python
from google.adk import Workflow   # ✅ — listed in google.adk.__all__
```

```text
google.adk.__all__ == ['Agent', 'Context', 'Event', 'Runner', 'Workflow']
```

`SequentialAgent` / `ParallelAgent` (under `google.adk.agents`) are **deprecated** with message *"Please use Workflow instead."* That refers to this class — not a missing future release.

**Wrong paths (do not use):**

| Path | Result |
|---|---|
| `google.adk.agents.workflow` | `ModuleNotFoundError` |
| `google.adk.agents.SequentialAgent` | Works but **deprecated** |
| `google.adk.agents.ParallelAgent` | Works but **deprecated** |

## Version

```text
google-adk 2.2.0
```

## Workflow package map

| Symbol | Import | Defining module |
|---|---|---|
| `Workflow` | `from google.adk import Workflow` | `google.adk.workflow._workflow` |
| `node`, `START`, `Edge` | `from google.adk.workflow import node, START, Edge` | `google.adk.workflow` |
| `FunctionNode` | `from google.adk.workflow import FunctionNode` | `google.adk.workflow._function_node` |
| `BaseNode` | `from google.adk.workflow import BaseNode` | `google.adk.workflow._base_node` |

`google.adk.workflow.__all__`:

```text
BaseNode, DEFAULT_ROUTE, Edge, FunctionNode, JoinNode, Node,
NodeTimeoutError, RetryConfig, START, Workflow, node
```

## Workflow usage (Aegis v1 — D24)

```python
from google.adk import Workflow
from google.adk.workflow import START, node
from google.adk.agents import LlmAgent
from google.adk.apps import App

v1_student_workflow = Workflow(
    name="v1_student_workflow",
    state_schema=StudentWorkflowState,  # pydantic BaseModel
    edges=[
        (START, case_parser_node, playbook_loader_node, phoenix_read_node,
         library_finder_agent, v1_drafter_agent, self_check_node),
    ],
)

app = App(name="aegis_v1", root_agent=v1_student_workflow)  # Workflow is BaseNode — valid root
```

| Step type | How to add to graph |
|---|---|
| Python / deterministic | `@node` decorator on async/sync function → `FunctionNode` |
| LLM | `LlmAgent(...)` passed directly in `edges` → wrapped by `build_node` |
| Conditional branch | `(router_node, {"route_key": target_node})` |
| Parallel fan-out | `(source_node, (node_a, node_b, ...))` |

**Constraint (ADK 2.2.0):** `LlmAgent` with `mode='task'` **cannot** be a static workflow graph node. Use `single_turn` (default when wrapped) or `chat`.

## Runner + sessions

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

session_service = InMemorySessionService()
session = session_service.create_session_sync(
    app_name="aegis_v1", user_id="user", state={}
)
runner = Runner(
    agent=v1_student_workflow,
    session_service=session_service,
    app_name="aegis_v1",
)
content = types.Content(role="user", parts=[types.Part.from_text(text="...")])
events = list(runner.run(
    user_id="user", session_id=session.id, new_message=content
))
final = session_service.get_session_sync(
    app_name="aegis_v1", user_id="user", session_id=session.id
)
```

- `Runner.run` → **sync generator** of `Event`
- `isinstance(root_agent, Workflow)` → `DynamicNodeScheduler` path in `google.adk.runners`
- `create_session_sync` / `get_session_sync` on `InMemorySessionService`

**Planned helper (Phase 1):** `run_workflow_sync(...)` in `adk_runtime.py` — not implemented yet.

## Model layer

| Symbol | Location | Notes |
|---|---|---|
| `BaseLlm` | `google.adk.models.base_llm` | Implement `generate_content_async(llm_request, stream=False)` |
| `Gemini` | `google.adk.models.google_llm` | Subclass for custom `api_client` (see `VertexGemini`) |
| `LlmRequest` / `LlmResponse` | `google.adk.models` | Request/response types |

**`gemini_retry` hook (Phase 0 ✅):** `RetryFallbackGemini` / `RetryFallbackLlm` in `adk_runtime.py` subclasses `VertexGemini`.

## Agents (non-workflow)

| Symbol | Notes |
|---|---|
| `LlmAgent` | `google.adk.agents.llm_agent.LlmAgent` — use as workflow nodes or single-shot |
| `Agent` | Alias for `LlmAgent` in 2.2.0 |
| `LangGraphAgent` | Experimental — **not** used in Aegis v1 |

Single-shot agents outside any `Workflow` graph: `run_llm_agent_sync` in `adk_runtime.py` (simulator, reflector, redaction scrubber).

## Aegis v1 Workflow surfaces

| Surface | Planned module | Pattern |
|---|---|---|
| Student pipeline | `student_workflow.py` | `Workflow` linear graph |
| Judge panel | `judge_workflow.py` | `Workflow` with fan-out |
| Simulator / reflector / scrubber | `*_agent.py` | `LlmAgent` + `run_llm_agent_sync` |
| `/appeal` best-of-5 | `appeal_orchestrator.py` | Python loop → `run_workflow_sync` + simulator |

## Official docs (verify on upgrade)

- [Graph routes](https://adk.dev/graphs/routes/)
- [Data handling / state](https://adk.dev/workflows/data-handling/)

Re-run the introspection snippet in this file after any `google-adk` version bump.

## FastAPI

`get_fast_api_app` in `main_v1.py` mounts `app` from `agent.py`. Today: Phase 0 placeholder `LlmAgent`. Phase 1 target: `App(root_agent=v1_student_workflow)`.
