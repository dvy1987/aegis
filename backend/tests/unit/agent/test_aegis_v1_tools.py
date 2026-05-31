from __future__ import annotations

from app.aegis_v1.drafter_client import StubDrafterClient
from app.aegis_v1.simulator_client import StubSimulatorClient, uniform_assessment
from app.aegis_v1.pipeline import run_aegis_v1_pipeline
from app.aegis_v1.schemas import ParsedCase
from app.aegis_v1.schemas import AppealPackage
from app.aegis_v1.tools import (
    case_parser,
    corpus_retrieval,
    drafter,
    phoenix_mcp_lookup,
    playbook_loader,
    self_check,
    simulator,
)


CIGNA_DENIAL = """Dear Member,

We reviewed the request for Intensive Outpatient Program services for severe
Obsessive-Compulsive Disorder. Cigna denied the request because weekly
outpatient therapy is available and the submitted notes do not show medical
necessity for an intensive level of care. You may appeal within 180 days.
"""


def test_case_parser_extracts_mvp_fields() -> None:
    parsed = ParsedCase.model_validate(
        case_parser(
            denial_text=CIGNA_DENIAL,
            clinical_context=(
                "The person has severe OCD, daily compulsions lasting 6 hours, "
                "and failed 6 months of weekly outpatient therapy."
            ),
            case_id="case_01_cigna_mednec",
        )
    )

    assert parsed.case_id == "case_01_cigna_mednec"
    assert parsed.insurer == "Cigna"
    assert parsed.denial_type == "medical_necessity"
    assert parsed.plan_type == "commercial"
    assert "Obsessive-Compulsive Disorder" in parsed.diagnosis_summary
    assert parsed.deadlines_mentioned == ["180 days"]


def test_corpus_retrieval_returns_traceable_hits() -> None:
    result = corpus_retrieval(
        query="Cigna medical necessity appeal 180 days ERISA full and fair review",
        top_k=2,
    )

    assert result["query"]
    assert len(result["hits"]) == 2
    assert all(hit["corpus_doc_id"].endswith(".md") for hit in result["hits"])
    assert all(hit["quote"] for hit in result["hits"])


def test_playbook_loader_returns_cold_start_playbook_when_missing() -> None:
    playbook = playbook_loader(insurer="Aetna", denial_type="prior_authorization")

    assert playbook["version"] == "cold-start"
    assert playbook["status"] == "missing"
    assert "playbook_cold_start" in playbook["risk_flags"]
    assert playbook["tactics"]


def test_tool_pipeline_produces_self_checked_appeal_package() -> None:
    parsed = case_parser(
        denial_text=CIGNA_DENIAL,
        clinical_context=(
            "The provider documented severe OCD, inability to leave the house, "
            "failed weekly therapy, and need for a higher level of care."
        ),
        case_id="case_01_cigna_mednec",
    )
    retrieval = corpus_retrieval(
        query="Cigna medical necessity ERISA MHPAEA intensive outpatient appeal",
        top_k=3,
    )
    playbook = playbook_loader(
        insurer=parsed["insurer"],
        denial_type=parsed["denial_type"],
    )
    phoenix = phoenix_mcp_lookup(
        insurer=parsed["insurer"],
        denial_type=parsed["denial_type"],
        case_id=parsed["case_id"],
    )
    draft = drafter(
        parsed_case=parsed,
        retrieval_results=retrieval,
        playbook=playbook,
        phoenix_summary=phoenix,
        client=StubDrafterClient(),
    )
    check = self_check(parsed_case=parsed, appeal_draft=draft, retrieval_results=retrieval)
    sim = simulator(parsed_case=parsed, appeal_draft=draft, self_check_result=check,
                    client=StubSimulatorClient(assessment=uniform_assessment(1)))

    assert "Not legal or medical advice. Draft assistance only." in draft["appeal_letter"]
    assert check["hard_gate_pass"] is True
    assert check["citation_check"]["all_citations_traceable"] is True
    assert sim["verdict"] == "DENY"
    assert sim["feature_scores"]


def test_local_pipeline_returns_structured_appeal_package() -> None:
    package = AppealPackage.model_validate(
        run_aegis_v1_pipeline(
            denial_text=CIGNA_DENIAL,
            clinical_context=(
                "The provider documented severe OCD, inability to leave the house, "
                "failed weekly therapy, and need for a higher level of care."
            ),
            case_id="case_01_cigna_mednec",
            dataset_split="train",
            run_mode="benchmark",
            drafter_client=StubDrafterClient(),
        )
    )

    assert package.run_id.startswith("aegis-v1-")
    assert package.parsed_case.insurer == "Cigna"
    assert package.trace_metadata.prompt_version == "aegis_v1_weak"
    assert package.trace_metadata.dataset_split == "train"
    assert package.appeal_package_draft.citations_used
    assert package.self_check.hard_gate_pass is True
