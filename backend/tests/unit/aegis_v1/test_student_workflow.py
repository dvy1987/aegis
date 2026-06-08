"""Phase 1 tests for the ADK student workflow (plan §17).

Covers: firewall, state schema, holdout mode, phoenix read-before-draft,
AppealPackage shape parity.
"""

from __future__ import annotations

from app.aegis_v1.drafter_client import StubDrafterClient
from app.aegis_v1.pipeline import run_aegis_v1_adk_pipeline, run_aegis_v1_pipeline
from app.aegis_v1.phoenix_mode import PhoenixMode
from app.aegis_v1.schemas import AppealPackage
from app.aegis_v1.student_workflow import (
    StudentWorkflowState,
    build_student_workflow,
)

DENIAL = (
    "Cigna denied Intensive Outpatient Program for Obsessive-Compulsive Disorder "
    "because medical necessity was not shown. Appeal within 180 days."
)
CLINICAL = "Severe OCD requiring IOP after conservative treatment failure."


# ---------------------------------------------------------------------------
# Firewall tests (D6, §17.3)
# ---------------------------------------------------------------------------


def test_student_workflow_state_has_no_teacher_fields() -> None:
    """StudentWorkflowState must never carry teacher-packet data (D6)."""
    field_names = set(StudentWorkflowState.model_fields.keys())
    forbidden = {
        "teacher_packet",
        "expected_appeal_vectors",
        "exploitable_weaknesses",
        "simulator_verdict",
        "simulator_score",
        "judge_report",
        "panel_report",
    }
    assert not (field_names & forbidden), (
        f"Firewall violation: state schema contains teacher/simulator/judge fields: "
        f"{field_names & forbidden}"
    )


def test_student_workflow_graph_has_no_simulator_or_judge_nodes() -> None:
    """The student graph must not contain simulator, judge, or reflector nodes (D6)."""
    wf = build_student_workflow()
    # Collect all node names from the graph edges
    node_names: set[str] = set()
    for edge_tuple in wf.edges:
        for item in edge_tuple:
            name = getattr(item, "name", None) or str(item)
            node_names.add(name.lower())
    forbidden_substrings = {"simulator", "judge", "reflector", "panel"}
    for name in node_names:
        for sub in forbidden_substrings:
            assert sub not in name, (
                f"Firewall violation: student graph contains node '{name}' "
                f"which matches forbidden pattern '{sub}'"
            )


# ---------------------------------------------------------------------------
# State schema tests
# ---------------------------------------------------------------------------


def test_state_schema_has_required_fields() -> None:
    """All pipeline I/O fields are declared in the state schema."""
    fields = set(StudentWorkflowState.model_fields.keys())
    required = {
        "denial_text", "clinical_context", "case_id",
        "parsed_case", "playbook", "phoenix_summary",
        "library_retrieval", "library_metadata", "appeal_draft",
        "self_check_result", "active_prompt_version",
        "phoenix_mode", "drafter_prompt_version", "drafter_prompt_text",
        "playbook_override_json", "use_phoenix_memory",
    }
    missing = required - fields
    assert not missing, f"State schema missing fields: {missing}"


# ---------------------------------------------------------------------------
# AppealPackage shape parity
# ---------------------------------------------------------------------------


def test_adk_pipeline_produces_valid_appeal_package() -> None:
    """The ADK pipeline must produce a valid AppealPackage dict."""
    result = run_aegis_v1_pipeline(
        denial_text=DENIAL,
        clinical_context=CLINICAL,
        case_id="adk_shape_test",
        drafter_client=StubDrafterClient(),
    )
    pkg = AppealPackage.model_validate(result)
    assert pkg.parsed_case.case_id == "adk_shape_test"
    assert pkg.parsed_case.insurer == "Cigna"
    assert pkg.appeal_package_draft.appeal_letter  # non-empty
    assert pkg.trace_metadata.case_id == "adk_shape_test"


def test_adk_pipeline_explicit_mode() -> None:
    """run_aegis_v1_adk_pipeline accepts PhoenixMode explicitly."""
    result = run_aegis_v1_adk_pipeline(
        denial_text=DENIAL,
        clinical_context=CLINICAL,
        case_id="explicit_mode_test",
        phoenix_mode=PhoenixMode.HOLDOUT_READONLY,
        drafter_client=StubDrafterClient(),
    )
    pkg = AppealPackage.model_validate(result)
    assert pkg.parsed_case.case_id == "explicit_mode_test"


# ---------------------------------------------------------------------------
# Holdout mode (D9, §17.4)
# ---------------------------------------------------------------------------


def test_holdout_mode_produces_valid_package() -> None:
    """Holdout mode must still produce a valid package (read-only Phoenix)."""
    result = run_aegis_v1_adk_pipeline(
        denial_text=DENIAL,
        clinical_context=CLINICAL,
        case_id="holdout_test",
        phoenix_mode=PhoenixMode.HOLDOUT_READONLY,
        drafter_client=StubDrafterClient(),
    )
    pkg = AppealPackage.model_validate(result)
    assert pkg.appeal_package_draft.appeal_letter


# ---------------------------------------------------------------------------
# Phoenix read-before-draft (D8, §17.4)
# ---------------------------------------------------------------------------


def test_holdout_measure_does_not_call_phoenix_export(monkeypatch) -> None:
    """Plan §17.4: pipeline holdout path must not invoke appeal Phoenix export."""
    calls: list[str] = []

    def _blocked_export(*args, **kwargs):
        calls.append("write")
        return None

    monkeypatch.setattr(
        "app.aegis_v1.appeal_phoenix_export.write_appeal_phoenix_export",
        _blocked_export,
    )

    run_aegis_v1_pipeline(
        denial_text=DENIAL,
        clinical_context=CLINICAL,
        case_id="holdout_no_write",
        phoenix_mode=PhoenixMode.HOLDOUT_READONLY,
        drafter_client=StubDrafterClient(),
    )
    assert calls == []


def test_workflow_chat_node_input_parses_denial(monkeypatch) -> None:
    """ADK chat passes denial text via node_input when state denial_text is empty."""
    from app.aegis_v1.adk_runtime import EchoLlm, run_workflow_sync
    from app.aegis_v1.student_workflow import build_student_workflow
    import app.aegis_v1.student_workflow as _sw

    _sw._injected_offline_pipeline = True
    _sw._injected_drafter_model = EchoLlm()
    try:
        result = run_workflow_sync(
            build_student_workflow(),
            app_name="aegis_v1",
            user_id="chat_test",
            initial_state={},
            message=DENIAL,
        )
    finally:
        _sw._injected_drafter_model = None
        _sw._injected_offline_pipeline = False

    parsed = result["state"].get("parsed_case", {})
    assert parsed.get("insurer") == "Cigna"
    assert result["state"].get("appeal_draft", {}).get("appeal_letter")


def test_holdout_mode_passed_to_pipeline(monkeypatch) -> None:
    """Showcase measure must use holdout_readonly (D9)."""
    captured: list[PhoenixMode] = []

    import app.aegis_v1.pipeline as pipeline_mod

    original = pipeline_mod.run_aegis_v1_adk_pipeline

    def capture_mode(**kwargs):
        captured.append(kwargs.get("phoenix_mode"))
        return original(**kwargs)

    monkeypatch.setattr(pipeline_mod, "run_aegis_v1_adk_pipeline", capture_mode)

    from app.evals.part_a.measurement_run import run_measurement_case

    run_measurement_case(
        {
            "case_id": "holdout_mode",
            "denial_letter_text": DENIAL,
            "clinical_context": CLINICAL,
        },
        drafter_client=StubDrafterClient(),
    )
    assert captured == [PhoenixMode.HOLDOUT_READONLY]


def test_phoenix_read_before_draft(monkeypatch) -> None:
    """Phoenix MCP lookup must execute before the drafter LlmAgent (D8)."""
    call_order: list[str] = []

    def tracking_lookup(*args, **kwargs):
        call_order.append("phoenix_read")
        return {
            "status": "cold_start",
            "query": "test",
            "similar_trace_count": 0,
            "failure_patterns": [],
            "success_traits": [],
            "risk_flags": ["phoenix_mcp_cold_start"],
        }

    import app.aegis_v1.adk_runtime as adk_runtime

    original_run_llm = adk_runtime.run_llm_agent_sync

    def tracking_run_llm(agent, **kwargs):
        if getattr(agent, "name", "") == "v1_drafter_agent":
            call_order.append("drafter")
        return original_run_llm(agent, **kwargs)

    monkeypatch.setattr("app.aegis_v1.tools.phoenix_mcp_lookup", tracking_lookup)
    monkeypatch.setattr(adk_runtime, "run_llm_agent_sync", tracking_run_llm)

    result = run_aegis_v1_pipeline(
        denial_text=DENIAL,
        clinical_context=CLINICAL,
        case_id="order_test",
        drafter_client=StubDrafterClient(),
    )
    assert "phoenix_mcp_cold_start" in result["risk_flags"]
    assert call_order.index("phoenix_read") < call_order.index("drafter")
