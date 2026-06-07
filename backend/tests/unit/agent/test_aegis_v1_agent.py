from __future__ import annotations

import inspect
import typing

from app.aegis_v1 import tools as aegis_tools
from app.aegis_v1.agent import AEGIS_V1_TOOL_NAMES, root_agent

EXPECTED_TOOLS = {
    "case_parser",
    "corpus_retrieval",
    "phoenix_mcp_lookup",
    "playbook_loader",
    "drafter",
    "self_check",
}


def test_root_agent_is_workflow() -> None:
    """Phase 1: root_agent is the ADK 2.2 Workflow (not a placeholder LlmAgent)."""
    from google.adk import Workflow

    assert isinstance(root_agent, Workflow)
    assert root_agent.name == "v1_student_workflow"
    assert AEGIS_V1_TOOL_NAMES == EXPECTED_TOOLS


def test_registered_tools_have_resolvable_type_hints() -> None:
    """ADK builds each tool's function declaration at agent-run time by calling
    `typing.get_type_hints()` on it. A forward-ref annotation naming a type that is
    only imported inside the function body (e.g. a DI `client: "DrafterLLMClient |
    None"`) raises NameError there and breaks the live agent / server — even though
    the offline unit tests, which call the tool directly, never trigger it. Guard the
    whole registered tool set against that class of bug."""
    for name in AEGIS_V1_TOOL_NAMES:
        fn = getattr(aegis_tools, name)
        typing.get_type_hints(fn)


def test_registered_tools_do_not_expose_di_client_param() -> None:
    """Dependency-injection seams (the drafter/simulator `client`) must not leak into
    the model-facing tool schema. They are injected by the orchestration/eval layer via
    `draft_appeal()` / `simulator()` instead, keeping the registered tool signatures
    limited to the data parameters the model actually fills."""
    for name in AEGIS_V1_TOOL_NAMES:
        fn = getattr(aegis_tools, name)
        params = inspect.signature(fn).parameters
        assert "client" not in params, (
            f"registered tool '{name}' exposes a DI 'client' param to the model"
        )


def test_workflow_has_state_schema() -> None:
    """Phase 1: workflow uses StudentWorkflowState for typed state."""
    from app.aegis_v1.student_workflow import StudentWorkflowState

    assert root_agent.state_schema is StudentWorkflowState
