from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

from app.aegis_v1.phoenix_mode import PhoenixMode
from app.aegis_v1.schemas import AppealPackage, Playbook, TraceMetadata

if TYPE_CHECKING:
    from app.aegis_v1.drafter_client import DrafterLLMClient

logger = logging.getLogger(__name__)


def _configure_workflow_injection(
    drafter_client: "DrafterLLMClient | None",
    library_stack: dict[str, Any] | None,
    question_responder: Any | None = None,
    question_agent_client: Any | None = None,
) -> bool:
    """Set module-level Workflow DI flags. Returns True when offline test mode is active."""
    import app.aegis_v1.student_workflow as _sw
    from app.aegis_v1.adk_runtime import EchoLlm
    from app.aegis_v1.drafter_client import is_offline_pipeline_client

    offline = is_offline_pipeline_client(drafter_client)
    _sw._injected_library_stack = library_stack
    _sw._injected_offline_pipeline = offline
    _sw._injected_drafter_model = EchoLlm() if offline else None
    _sw._injected_question_responder = question_responder
    _sw._injected_question_client = question_agent_client
    return offline


def _clear_workflow_injection() -> None:
    import app.aegis_v1.student_workflow as _sw

    _sw._injected_library_stack = None
    _sw._injected_drafter_model = None
    _sw._injected_offline_pipeline = False
    _sw._injected_question_responder = None
    _sw._injected_question_client = None


def run_aegis_v1_pipeline(
    denial_text: str,
    clinical_context: str = "",
    case_id: str = "interactive_case",
    insurer: str | None = None,
    patient_age: int | None = None,
    patient_gender: str | None = None,
    dataset_split: str = "interactive",
    run_mode: Literal["interactive", "benchmark", "autonomous_promotion"] = (
        "interactive"
    ),
    drafter_client: "DrafterLLMClient | None" = None,
    drafter_prompt_version: str | None = None,
    drafter_prompt_text: str | None = None,
    playbook_override: dict[str, Any] | None = None,
    geo_playbook_override: dict[str, Any] | None = None,
    library_stack: dict[str, Any] | None = None,
    use_phoenix_memory: bool = True,
    phoenix_mode: PhoenixMode = PhoenixMode.APPEAL,
    run_question_agent: bool = False,
    question_responder: Any | None = None,
    question_agent_client: Any | None = None,
    question_interview: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the six-tool v1 Student flow via ADK 2.2 Workflow (D21 seam).

    The Outcome Simulator is no longer part of the Student — it runs in the
    eval layer (``run_evaluated_case``). The pre-draft question agent IS part
    of the Student workflow: pass ``run_question_agent`` plus a
    ``question_responder`` closure (showcase) or a pre-completed
    ``question_interview`` artifact (appeal).
    """
    return run_aegis_v1_adk_pipeline(
        denial_text=denial_text,
        clinical_context=clinical_context,
        case_id=case_id,
        insurer=insurer,
        patient_age=patient_age,
        patient_gender=patient_gender,
        dataset_split=dataset_split,
        run_mode=run_mode,
        phoenix_mode=phoenix_mode,
        drafter_client=drafter_client,
        drafter_prompt_version=drafter_prompt_version,
        drafter_prompt_text=drafter_prompt_text,
        playbook_override=playbook_override,
        geo_playbook_override=geo_playbook_override,
        library_stack=library_stack,
        use_phoenix_memory=use_phoenix_memory,
        run_question_agent=run_question_agent,
        question_responder=question_responder,
        question_agent_client=question_agent_client,
        question_interview=question_interview,
    )


def run_aegis_v1_adk_pipeline(
    denial_text: str,
    clinical_context: str = "",
    case_id: str = "interactive_case",
    insurer: str | None = None,
    patient_age: int | None = None,
    patient_gender: str | None = None,
    dataset_split: str = "interactive",
    run_mode: str = "interactive",
    phoenix_mode: PhoenixMode = PhoenixMode.APPEAL,
    drafter_client: "DrafterLLMClient | None" = None,
    drafter_prompt_version: str | None = None,
    drafter_prompt_text: str | None = None,
    playbook_override: dict[str, Any] | None = None,
    geo_playbook_override: dict[str, Any] | None = None,
    library_stack: dict[str, Any] | None = None,
    use_phoenix_memory: bool = True,
    run_question_agent: bool = False,
    question_responder: Any | None = None,
    question_agent_client: Any | None = None,
    question_interview: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the v1 Student via ADK 2.2 Workflow and return an AppealPackage dict.

    This is the single production path (D4 — no feature flag).
    """
    from app.aegis_v1.adk_runtime import run_workflow_sync
    from app.aegis_v1.library_context import LibraryPrepMetadata
    from app.aegis_v1.student_workflow import build_student_workflow

    initial_state = {
        "denial_text": denial_text,
        "clinical_context": clinical_context,
        "case_id": case_id,
        "insurer": insurer or "",
        "patient_age": patient_age if patient_age is not None else -1,
        "patient_gender": patient_gender or "",
        "dataset_split": dataset_split,
        "run_mode": run_mode,
        "phoenix_mode": phoenix_mode.value,
        "drafter_prompt_version": drafter_prompt_version or "",
        "drafter_prompt_text": drafter_prompt_text or "",
        "playbook_override_json": (
            json.dumps(playbook_override) if playbook_override is not None else ""
        ),
        "geo_playbook_override_json": (
            json.dumps(geo_playbook_override) if geo_playbook_override is not None else ""
        ),
        "use_phoenix_memory": use_phoenix_memory,
        "library_stack_json": "",
        "run_question_agent": run_question_agent,
        "question_interview_json": (
            json.dumps(question_interview, default=str) if question_interview else ""
        ),
    }

    # Inject non-serializable DI objects via module globals.  ADK's Runner
    # spawns a new asyncio context so contextvars don't propagate, but module
    # globals are visible from the @node functions in the same process.
    _configure_workflow_injection(
        drafter_client,
        library_stack,
        question_responder=question_responder,
        question_agent_client=question_agent_client,
    )
    try:
        workflow = build_student_workflow()
        result = run_workflow_sync(
            workflow,
            app_name="aegis_v1",
            user_id="pipeline",
            initial_state=initial_state,
            message=f"Process appeal case {case_id}",
            phoenix_mode=phoenix_mode,
        )
    finally:
        _clear_workflow_injection()
    state = result["state"]

    # --- Assemble AppealPackage from final workflow state ---
    parsed = state.get("parsed_case", {})
    draft = state.get("appeal_draft", {})
    check = state.get("self_check_result", {})
    playbook_data = state.get("playbook", {})
    phoenix_data = state.get("phoenix_summary", {})
    active_prompt_version = state.get("active_prompt_version", "drafter_v1")
    lib_risk_flags = state.get("library_risk_flags", [])
    lib_meta_raw = state.get("library_metadata", {})

    risk_flags = sorted(
        set(
            draft.get("risk_flags", [])
            + check.get("risk_flags", [])
            + phoenix_data.get("risk_flags", [])
            + playbook_data.get("risk_flags", [])
            + lib_risk_flags
        )
    )

    loaded_playbook = Playbook.model_validate(playbook_data)
    prep = LibraryPrepMetadata.model_validate(lib_meta_raw) if lib_meta_raw else LibraryPrepMetadata()

    package = AppealPackage(
        run_id=f"aegis-v1-{uuid4().hex[:8]}",
        parsed_case=parsed,
        appeal_package_draft=draft,
        self_check=check,
        risk_flags=risk_flags,
        question_interview=state.get("question_interview") or None,
        trace_metadata=TraceMetadata(
            case_id=parsed.get("case_id", case_id),
            insurer=parsed.get("insurer", "unknown"),
            denial_type=parsed.get("denial_type", "unknown"),
            plan_type=parsed.get("plan_type", "commercial"),
            state=parsed.get("state", "unknown"),
            prompt_version=active_prompt_version,
            playbook_version=loaded_playbook.version,
            dataset_split=dataset_split,
            run_mode=run_mode,
            search_planner_version=prep.search_planner_version,
            library_search_query=prep.library_search_query,
            library_available=prep.library_available,
            cloud_library_used=prep.cloud_library_used,
            discovery_enabled=prep.discovery_enabled,
            discovery_ran=prep.discovery_ran,
            discovery_fetch_count=prep.discovery_fetch_count,
            discovery_queries=prep.discovery_queries,
            discovery_ingested_count=prep.discovery_ingested_count,
            discovery_rejected_count=prep.discovery_rejected_count,
            layer3_refinement_ran=prep.layer3_refinement_ran,
        ),
    )
    return package.model_dump()
