from __future__ import annotations

from app.aegis_swarm.schemas import AgentTraceSignal
from app.aegis_swarm.trace_recorder import (
    InMemorySwarmTraceRecorder,
    OtelSwarmTraceRecorder,
    build_trace_recorder,
)
from app.aegis_swarm.tools import make_agent_trace_signal


def test_in_memory_recorder_stores_signals() -> None:
    rec = InMemorySwarmTraceRecorder()
    sig = make_agent_trace_signal("drafter", status="drafted_iter_1", citation_count=2)
    ids = rec.record_agent_signals(
        "run-1",
        [sig],
        {"case_id": "c1", "insurer": "Cigna"},
    )
    assert ids == ["mem-run-1-0"]
    assert rec.runs["run-1"]["signals"][0]["role"] == "drafter"


def test_otel_recorder_constructs() -> None:
    assert OtelSwarmTraceRecorder().name == "otel_swarm"


def test_build_trace_recorder_memory_mode(monkeypatch) -> None:
    monkeypatch.setenv("AEGIS_SWARM_TRACE_MODE", "memory")
    assert isinstance(build_trace_recorder(), InMemorySwarmTraceRecorder)
