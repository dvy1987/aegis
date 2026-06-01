from __future__ import annotations

from app.aegis_swarm.client import StubSwarmClient
from app.aegis_swarm.corpus_store import LocalCorpusStore
from app.aegis_swarm.schemas import SwarmRunArtifacts
from app.aegis_swarm.swarm_pipeline import run_swarm_pipeline
from app.aegis_v1.schemas import AppealPackage

_DENIAL = (
    "Cigna has denied coverage for esketamine for treatment-resistant depression. "
    "The service is not medically necessary because conservative therapy was not "
    "exhausted. You have 180 days to appeal."
)
_CONTEXT = "Patient documented two failed antidepressant trials at adequate dose."


def _run():
    return run_swarm_pipeline(
        denial_text=_DENIAL,
        clinical_context=_CONTEXT,
        case_id="syn-cigna-mh-001",
        client=StubSwarmClient(),
        corpus_store=LocalCorpusStore(),
    )


def test_pipeline_runs_e2e_offline_and_returns_valid_package() -> None:
    result = _run()
    package = AppealPackage.model_validate(result["appeal_package"])
    assert package.run_id.startswith("aegis-swarm-")
    assert package.trace_metadata.prompt_version == "aegis_swarm_v1"
    assert package.appeal_package_draft.appeal_letter


def test_pipeline_self_check_hard_gate_passes() -> None:
    result = _run()
    check = result["appeal_package"]["self_check"]
    # Guardrails guarantee the disclaimer; citations are traceable to the corpus.
    assert check["safety_check"]["disclaimer_present"] is True
    assert check["citation_check"]["all_citations_traceable"] is True
    assert check["hard_gate_pass"] is True


def test_pipeline_attaches_swarm_artifacts() -> None:
    result = _run()
    artifacts = SwarmRunArtifacts.model_validate(result["artifacts"])
    assert artifacts.routing_manifest.case_id == "syn-cigna-mh-001"
    assert artifacts.briefs
    assert artifacts.strategy is not None
    assert artifacts.critiques
    assert "triage" in artifacts.agent_versions
    assert "drafter" in artifacts.agent_versions


def test_pipeline_fans_out_to_multiple_researchers() -> None:
    result = _run()
    artifacts = SwarmRunArtifacts.model_validate(result["artifacts"])
    invoked = artifacts.routing_manifest.invoked()
    # medical_necessity routes to clinical + policy + the always-on insurer agent.
    assert "insurer_intelligence" in invoked
    assert "medical_necessity" in invoked
    assert "policy_detective" in invoked
    assert artifacts.insurer_brief is not None
    assert len(artifacts.briefs) == len(invoked)


def test_pipeline_draft_cites_only_traceable_corpus_docs() -> None:
    result = _run()
    cited = {
        c["corpus_doc_id"]
        for c in result["appeal_package"]["appeal_package_draft"]["citations_used"]
    }
    store = LocalCorpusStore()
    # With the fan-out, citations may come from any retrieved domain subtree.
    corpus_ids = {
        h.corpus_doc_id
        for domain in ("clinical", "legal", "policy", "insurer", "precedent")
        for h in store.search(domain, "medical necessity appeal", top_k=5)  # type: ignore[arg-type]
    }
    assert cited.issubset(corpus_ids) or not cited


def test_pipeline_denial_type_carries_swarm_classification() -> None:
    result = _run()
    assert result["appeal_package"]["trace_metadata"]["denial_type"] == "medical_necessity"
