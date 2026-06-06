from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

from app.aegis_v1.library_context import prepare_library_context
from app.aegis_v1.retrieval_context import reset_controlled_retrieval, set_controlled_retrieval
from app.aegis_v1.schemas import AppealPackage
from app.aegis_v1.schemas import Playbook
from app.aegis_v1.schemas import TraceMetadata
from app.aegis_v1.tools import (
    case_parser,
    corpus_retrieval,
    draft_appeal,
    phoenix_mcp_lookup,
    playbook_loader,
    self_check,
)
from app.aegis_v1.v1_config import build_v1_library_stack

if TYPE_CHECKING:
    from app.aegis_v1.drafter_client import DrafterLLMClient


def run_aegis_v1_pipeline(
    denial_text: str,
    clinical_context: str = "",
    case_id: str = "interactive_case",
    dataset_split: str = "interactive",
    run_mode: Literal["interactive", "benchmark", "autonomous_promotion"] = (
        "interactive"
    ),
    drafter_client: "DrafterLLMClient | None" = None,
    drafter_prompt_version: str | None = None,
    library_stack: dict[str, Any] | None = None,
    use_phoenix_memory: bool = True,
) -> dict[str, Any]:
    """Run the six-tool v1 Student flow. The Outcome Simulator is no longer part
    of the Student — it runs in the eval layer (`run_evaluated_case`)."""

    parsed = case_parser(
        denial_text=denial_text,
        clinical_context=clinical_context,
        case_id=case_id,
    )

    stack = library_stack or build_v1_library_stack()
    lib_ctx = prepare_library_context(
        parsed,
        case_id=parsed["case_id"],
        corpus_store=stack["corpus_store"],
        discovery=stack.get("discovery"),
        refinement_client=stack.get("refinement_client"),
        cloud_library_used=bool(stack.get("uses_vertex_store")),
    )

    token = set_controlled_retrieval(lib_ctx.retrieval)
    try:
        retrieval = corpus_retrieval(
            query=lib_ctx.metadata.library_search_query,
            top_k=3,
        )
    finally:
        reset_controlled_retrieval(token)

    if use_phoenix_memory:
        phoenix = phoenix_mcp_lookup(
            insurer=parsed["insurer"],
            denial_type=parsed["denial_type"],
            case_id=parsed["case_id"],
        )
    else:
        phoenix = {
            "status": "disabled",
            "query": "measurement mode disables Phoenix memory",
            "similar_trace_count": 0,
            "failure_patterns": [],
            "success_traits": [],
            "risk_flags": ["phoenix_mcp_measurement_disabled"],
        }
    playbook = playbook_loader(
        insurer=parsed["insurer"],
        denial_type=parsed["denial_type"],
    )
    from app.aegis_v1.drafter_client import get_active_drafter_prompt_version

    active_prompt_version = drafter_prompt_version or get_active_drafter_prompt_version()
    draft = draft_appeal(
        parsed_case=parsed,
        retrieval_results=retrieval,
        playbook=playbook,
        phoenix_summary=phoenix,
        client=drafter_client,
        prompt_version=active_prompt_version,
    )
    check = self_check(
        parsed_case=parsed,
        appeal_draft=draft,
        retrieval_results=retrieval,
    )

    risk_flags = sorted(
        set(
            draft.get("risk_flags", [])
            + check.get("risk_flags", [])
            + phoenix.get("risk_flags", [])
            + playbook.get("risk_flags", [])
            + lib_ctx.risk_flags
        )
    )
    loaded_playbook = Playbook.model_validate(playbook)
    prep = lib_ctx.metadata
    package = AppealPackage(
        run_id=f"aegis-v1-{uuid4().hex[:8]}",
        parsed_case=parsed,
        appeal_package_draft=draft,
        self_check=check,
        risk_flags=risk_flags,
        trace_metadata=TraceMetadata(
            case_id=parsed["case_id"],
            insurer=parsed["insurer"],
            denial_type=parsed["denial_type"],
            plan_type=parsed["plan_type"],
            state=parsed["state"],
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
