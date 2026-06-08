"""Phase 1 gap A: library_finder and drafter must be LlmAgent workflow graph nodes."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from app.aegis_v1.student_workflow import build_student_workflow


def _graph_node_names(workflow) -> set[str]:
    names: set[str] = set()
    for edge_tuple in workflow.edges:
        for item in edge_tuple:
            name = getattr(item, "name", None)
            if name:
                names.add(name)
            elif isinstance(item, LlmAgent):
                names.add(item.name)
    return names


def _graph_llm_agent_names(workflow) -> set[str]:
    found: set[str] = set()
    for edge_tuple in workflow.edges:
        for item in edge_tuple:
            if isinstance(item, LlmAgent):
                found.add(item.name)
    return found


def test_student_workflow_edges_include_library_and_drafter_llm_agents() -> None:
    wf = build_student_workflow()
    llm_names = _graph_llm_agent_names(wf)
    assert "library_finder_agent" in llm_names
    assert "v1_drafter_agent" in llm_names


def test_student_workflow_does_not_use_function_node_wrappers_for_llm_agents() -> None:
    """Gap A: nested @node wrappers named library_finder_node/drafter_node are removed."""
    names = _graph_node_names(build_student_workflow())
    assert "library_finder_node" not in names
    assert "drafter_node" not in names


def test_student_workflow_student_path_skips_nested_run_llm_agent_sync(
    monkeypatch,
) -> None:
    """Student workflow LLM steps run as graph nodes, not nested run_llm_agent_sync."""
    from app.aegis_v1.adk_runtime import run_workflow_sync
    from app.aegis_v1.drafter_client import StubDrafterClient
    import app.aegis_v1.adk_runtime as adk_runtime
    import app.aegis_v1.pipeline as pipeline_mod
    import app.aegis_v1.student_workflow as student_workflow_mod

    nested_calls: list[str] = []

    original = adk_runtime.run_llm_agent_sync

    def tracking_run_llm(agent, **kwargs):
        nested_calls.append(getattr(agent, "name", "unknown"))
        return original(agent, **kwargs)

    monkeypatch.setattr(adk_runtime, "run_llm_agent_sync", tracking_run_llm)

    pipeline_mod._configure_workflow_injection(StubDrafterClient(), None)
    try:
        workflow = student_workflow_mod.build_student_workflow()
        run_workflow_sync(
            workflow,
            app_name="aegis_v1",
            user_id="gap_a_test",
            initial_state={
                "denial_text": (
                    "Cigna denied IOP because medical necessity was not shown."
                ),
                "clinical_context": "Severe OCD.",
                "case_id": "gap_a_test",
                "phoenix_mode": "appeal",
            },
            message="run",
        )
    finally:
        pipeline_mod._clear_workflow_injection()

    assert "library_finder_agent" not in nested_calls
    assert "v1_drafter_agent" not in nested_calls
