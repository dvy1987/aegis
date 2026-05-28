from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from app.aegis_v1.schemas import AppealPackage
from app.aegis_v1.schemas import Playbook
from app.aegis_v1.schemas import TraceMetadata
from app.aegis_v1.tools import (
    case_parser,
    corpus_retrieval,
    drafter,
    phoenix_mcp_lookup,
    playbook_loader,
    self_check,
    simulator,
)


def run_aegis_v1_pipeline(
    denial_text: str,
    clinical_context: str = "",
    case_id: str = "interactive_case",
    dataset_split: str = "interactive",
    run_mode: Literal["interactive", "benchmark", "autonomous_promotion"] = (
        "interactive"
    ),
) -> dict[str, Any]:
    """Run the deterministic seven-tool v1 flow for local smoke tests."""

    parsed = case_parser(
        denial_text=denial_text,
        clinical_context=clinical_context,
        case_id=case_id,
    )
    query = " ".join(
        [
            parsed["insurer"],
            parsed["denial_type"],
            parsed["service_or_procedure"],
            parsed["diagnosis_summary"],
            parsed["cited_denial_reason"],
        ]
    )
    retrieval = corpus_retrieval(query=query, top_k=3)
    phoenix = phoenix_mcp_lookup(
        insurer=parsed["insurer"],
        denial_type=parsed["denial_type"],
        case_id=parsed["case_id"],
    )
    playbook = playbook_loader(
        insurer=parsed["insurer"],
        denial_type=parsed["denial_type"],
    )
    draft = drafter(
        parsed_case=parsed,
        retrieval_results=retrieval,
        playbook=playbook,
        phoenix_summary=phoenix,
    )
    check = self_check(
        parsed_case=parsed,
        appeal_draft=draft,
        retrieval_results=retrieval,
    )
    sim = simulator(
        parsed_case=parsed,
        appeal_draft=draft,
        self_check_result=check,
    )

    risk_flags = sorted(
        set(
            draft.get("risk_flags", [])
            + check.get("risk_flags", [])
            + phoenix.get("risk_flags", [])
            + playbook.get("risk_flags", [])
        )
    )
    loaded_playbook = Playbook.model_validate(playbook)
    package = AppealPackage(
        run_id=f"aegis-v1-{uuid4().hex[:8]}",
        parsed_case=parsed,
        appeal_package_draft=draft,
        self_check=check,
        simulator_result=sim,
        risk_flags=risk_flags,
        trace_metadata=TraceMetadata(
            case_id=parsed["case_id"],
            insurer=parsed["insurer"],
            denial_type=parsed["denial_type"],
            plan_type=parsed["plan_type"],
            state=parsed["state"],
            playbook_version=loaded_playbook.version,
            dataset_split=dataset_split,
            run_mode=run_mode,
        ),
    )
    return package.model_dump()
