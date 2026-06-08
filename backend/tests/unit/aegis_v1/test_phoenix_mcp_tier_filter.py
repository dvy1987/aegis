"""Phase 5: tier B spans excluded from MCP fetch; tier C included."""

from __future__ import annotations

from app.aegis_v1.phoenix_mcp import _join_spans_with_annotations
from app.aegis_v1.tools import phoenix_mcp_lookup


def _span(insurer: str, denial: str, memory_eligible: str, span_id: str) -> dict:
    return {
        "attributes": {
            "aegis.insurer": insurer,
            "aegis.denial_type": denial,
            "aegis.memory_eligible": memory_eligible,
        },
        "context": {"span_id": span_id},
    }


def _annotation(span_id: str, improvement: str) -> dict:
    return {
        "name": "aegis_part_a_panel",
        "span_id": span_id,
        "result": {
            "explanation": (
                '{"dimensions": {"grounding": {"score": 1, "improvement": "'
                + improvement
                + '"}}}'
            )
        },
    }


def test_join_only_returns_annotated_spans() -> None:
    spans = [_span("Cigna", "medical_necessity", "true", "eligible")]
    joined = _join_spans_with_annotations(spans, [_annotation("eligible", "tier c signal")])
    assert len(joined) == 1
    assert joined[0]["dimensions"]["grounding"]["improvement"] == "tier c signal"


def test_phoenix_mcp_lookup_uses_only_fetch_results(monkeypatch) -> None:
    """fetch_slice_traces applies memory_eligible filter before lookup summarizes."""

    def fake_fetch(**_kwargs):
        spans = [_span("Cigna", "medical_necessity", "true", "c1")]
        return _join_spans_with_annotations(spans, [_annotation("c1", "approved pattern")])

    monkeypatch.setenv("PHOENIX_MCP_ENABLED", "true")
    monkeypatch.setattr("app.aegis_v1.phoenix_mcp.fetch_slice_traces", fake_fetch)
    summary = phoenix_mcp_lookup("Cigna", "medical_necessity")
    assert summary["status"] == "available"
    assert "approved pattern" in str(summary["failure_patterns"])


def test_slice_filter_excludes_tier_b_keeps_tier_c() -> None:
    from app.aegis_v1.phoenix_mcp import _slice_filter

    tier_b = _span("Cigna", "medical_necessity", "false", "b1")["attributes"]
    tier_c = _span("Cigna", "medical_necessity", "true", "c1")["attributes"]
    assert _slice_filter(tier_b, insurer="Cigna", denial_type="medical_necessity") is False
    assert _slice_filter(tier_c, insurer="Cigna", denial_type="medical_necessity") is True
