from __future__ import annotations

from app.aegis_swarm.client import StubSwarmClient
from app.aegis_swarm.corpus_store import LocalCorpusStore
from app.aegis_swarm.schemas import AgentTraceSignal, SwarmRunArtifacts
from app.aegis_swarm.swarm_pipeline import run_swarm_pipeline
from app.aegis_swarm.tools import make_agent_trace_signal

_DENIAL = (
    "Cigna has denied coverage for esketamine for treatment-resistant depression. "
    "The service is not medically necessary because conservative therapy was not "
    "exhausted. You have 180 days to appeal."
)
_CONTEXT = "Patient documented two failed antidepressant trials at adequate dose."


def _artifacts() -> SwarmRunArtifacts:
    result = run_swarm_pipeline(
        denial_text=_DENIAL,
        clinical_context=_CONTEXT,
        case_id="syn-cigna-mh-001",
        client=StubSwarmClient(),
        corpus_store=LocalCorpusStore(),
    )
    return SwarmRunArtifacts.model_validate(result["artifacts"])


# --- builder ----------------------------------------------------------------


def test_builder_stamps_weak_agent_metadata() -> None:
    sig = make_agent_trace_signal("drafter", status="drafted_iter_1", citation_count=2)
    assert isinstance(sig, AgentTraceSignal)
    assert sig.prompt_version == "v1_weak"
    assert sig.is_weak_v1 is True
    assert sig.owned_dimensions == ["grounding", "persuasive_coherence"]


def test_builder_stamps_strong_agent_metadata() -> None:
    sig = make_agent_trace_signal("triage", status="medical_necessity")
    assert sig.prompt_version == "v1"
    assert sig.is_weak_v1 is False
    assert sig.owned_dimensions == []


def test_builder_dedupes_and_sorts_risk_flags() -> None:
    sig = make_agent_trace_signal("legal_researcher", risk_flags=["b", "a", "a"])
    assert sig.risk_flags == ["a", "b"]


# --- pipeline emission ------------------------------------------------------


def test_pipeline_emits_one_signal_per_invoked_agent() -> None:
    artifacts = _artifacts()
    signals = artifacts.agent_trace_signals
    roles = [s.role for s in signals]
    assert "triage" in roles
    assert "strategist" in roles
    assert "drafter" in roles
    assert "adversarial_reviewer" in roles
    # every invoked researcher has a signal
    for researcher in artifacts.routing_manifest.invoked():
        assert researcher in roles
    # every signal carries a version (the credit-assignment unit)
    assert all(s.prompt_version for s in signals)


def test_pipeline_flags_weak_agents_in_signals() -> None:
    artifacts = _artifacts()
    weak_roles = {s.role for s in artifacts.agent_trace_signals if s.is_weak_v1}
    # drafter + strategist always run; medical_necessity is routed for this case
    assert {"drafter", "strategist", "medical_necessity"} <= weak_roles


def test_trace_signals_are_firewall_safe_no_leak() -> None:
    # Laundered summaries must never carry case/clinical prose or agent thinking -
    # only structural one-liners (enums + counts).
    artifacts = _artifacts()
    for sig in artifacts.agent_trace_signals:
        assert "failed antidepressant trials" not in sig.summary
        assert "Patient documented" not in sig.summary
        assert len(sig.summary) < 200
