"""Per-agent Phoenix / OTel trace recording (FR-5, Phase 4).

Emits one child span per ``AgentTraceSignal`` so the demo can show which agent
ran which prompt version without leaking letter text or answer-key fields.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.aegis_swarm.schemas import AgentTraceSignal


@runtime_checkable
class SwarmTraceRecorder(Protocol):
    name: str

    def record_agent_signals(
        self,
        run_id: str,
        signals: list[AgentTraceSignal],
        trace_metadata: dict[str, Any],
    ) -> list[str]:
        """Persist per-agent signals; return span ids (may be empty offline)."""


class InMemorySwarmTraceRecorder:
    """Offline fake for unit tests."""

    name = "in_memory"

    def __init__(self) -> None:
        self.runs: dict[str, dict[str, Any]] = {}

    def record_agent_signals(
        self,
        run_id: str,
        signals: list[AgentTraceSignal],
        trace_metadata: dict[str, Any],
    ) -> list[str]:
        self.runs[run_id] = {
            "signals": [s.model_dump() for s in signals],
            "metadata": dict(trace_metadata),
        }
        return [f"mem-{run_id}-{i}" for i, _ in enumerate(signals)]


class OtelSwarmTraceRecorder:
    """Production recorder: one OTel span per agent role per run.

    Span attributes are firewall-safe (structural only). Live export to Phoenix
    is exercised in a GCP integration session.
    """

    name = "otel_swarm"

    def record_agent_signals(
        self,
        run_id: str,
        signals: list[AgentTraceSignal],
        trace_metadata: dict[str, Any],
    ) -> list[str]:
        from opentelemetry import trace as otel_trace

        tracer = otel_trace.get_tracer("aegis.swarm")
        span_ids: list[str] = []
        with tracer.start_as_current_span("aegis_swarm.run") as parent:
            parent.set_attribute("aegis.run_id", run_id)
            for key, value in trace_metadata.items():
                parent.set_attribute(f"aegis.{key}", str(value))
            for sig in signals:
                with tracer.start_as_current_span(f"aegis_swarm.agent.{sig.role}") as span:
                    span.set_attribute("aegis.agent.role", sig.role)
                    span.set_attribute("aegis.agent.prompt_version", sig.prompt_version)
                    span.set_attribute("aegis.agent.is_weak_v1", sig.is_weak_v1)
                    span.set_attribute("aegis.agent.status", sig.status)
                    span.set_attribute("aegis.agent.summary", sig.summary)
                    if sig.owned_dimensions:
                        span.set_attribute(
                            "aegis.agent.owned_dimensions",
                            ",".join(sig.owned_dimensions),
                        )
                    span.set_attribute("aegis.agent.finding_count", sig.finding_count)
                    span.set_attribute("aegis.agent.citation_count", sig.citation_count)
                    if sig.risk_flags:
                        span.set_attribute(
                            "aegis.agent.risk_flags",
                            ",".join(sig.risk_flags),
                        )
                    ctx = span.get_span_context()
                    span_ids.append(format(ctx.span_id, "016x"))
        return span_ids


def build_trace_recorder() -> SwarmTraceRecorder:
    import os

    mode = os.environ.get("AEGIS_SWARM_TRACE_MODE", "otel").lower()
    if mode in ("off", "none", "disabled"):
        return InMemorySwarmTraceRecorder()
    if mode == "memory":
        return InMemorySwarmTraceRecorder()
    return OtelSwarmTraceRecorder()
