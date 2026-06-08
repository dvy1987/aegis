from __future__ import annotations

import json

from app.aegis_v1.adk_runtime import EchoLlm
from app.aegis_v1.library_finder_agent import (
    build_library_finder_agent,
    parse_library_finder_response,
    run_library_finder_agent,
    run_offline_library_search,
)


CIGNA_PARSED = {
    "case_id": "lib_test",
    "insurer": "Cigna",
    "denial_type": "medical_necessity",
    "plan_type": "commercial",
    "service_or_procedure": "IOP",
    "diagnosis_summary": "OCD",
    "state": "CA",
    "cited_denial_reason": "not medically necessary",
    "denial_text": "Cigna denied IOP.",
    "clinical_context": "Severe OCD.",
}


def test_build_library_finder_agent_has_search_tool() -> None:
    agent = build_library_finder_agent(library_stack=None)
    assert agent.name == "library_finder_agent"
    assert agent.tools
    tool_names = {
        getattr(t, "__name__", getattr(t, "name", "")) for t in agent.tools
    }
    assert "search_library" in tool_names


def test_parse_library_finder_response() -> None:
    raw = json.dumps(
        {
            "query": "Cigna IOP OCD",
            "hits": [
                {
                    "corpus_doc_id": "doc-1",
                    "title": "Guideline",
                    "quote": "IOP is indicated.",
                    "relevance_score": 0.9,
                }
            ],
        }
    )
    retrieval, search_error = parse_library_finder_response(raw)
    assert retrieval["query"] == "Cigna IOP OCD"
    assert len(retrieval["hits"]) == 1
    assert search_error is False


def test_run_library_finder_agent_uses_mock_llm_response(monkeypatch) -> None:
    payload = {
        "query": "Cigna IOP OCD medical necessity",
        "hits": [
            {
                "corpus_doc_id": "doc-99",
                "title": "IOP guideline",
                "quote": "IOP is appropriate for severe OCD.",
                "relevance_score": 0.88,
            }
        ],
    }

    def fake_run(agent, **kwargs):
        return {
            "events": [
                type(
                    "E",
                    (),
                    {
                        "content": type(
                            "C",
                            (),
                            {
                                "parts": [
                                    type("P", (), {"text": json.dumps(payload)})()
                                ]
                            },
                        )()
                    },
                )()
            ]
        }

    monkeypatch.setattr(
        "app.aegis_v1.library_finder_agent.run_llm_agent_sync",
        fake_run,
    )
    retrieval, search_error = run_library_finder_agent(
        parsed=CIGNA_PARSED,
        playbook={"tactics": ["Document severity."]},
        phoenix_summary={"status": "cold_start", "risk_flags": []},
        library_stack=None,
        model=EchoLlm(),
    )
    assert retrieval["query"] == payload["query"]
    assert retrieval["hits"][0]["corpus_doc_id"] == "doc-99"
    assert search_error is False


def test_offline_library_search_uses_baseline_query() -> None:
    retrieval, search_error = run_offline_library_search(CIGNA_PARSED, None)
    assert "Cigna" in retrieval["query"]
    assert search_error is False


class _ExplodingCorpusStore:
    def list_domains(self) -> list[str]:
        raise RuntimeError("library offline")

    def search(self, domain, query, top_k: int = 3):
        raise RuntimeError("library offline")


def test_offline_library_search_survives_corpus_failure() -> None:
    stack = {
        "corpus_store": _ExplodingCorpusStore(),
        "discovery": None,
        "refinement_client": None,
        "uses_vertex_store": True,
    }
    retrieval, search_error = run_offline_library_search(CIGNA_PARSED, stack)
    assert retrieval["hits"] == []
    assert search_error is True
