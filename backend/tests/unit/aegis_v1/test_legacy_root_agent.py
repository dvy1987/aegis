from __future__ import annotations

from app.aegis_v1._stash.legacy_root_agent import (
    LEGACY_AEGIS_V1_TOOL_NAMES,
    legacy_root_agent,
)
from app.aegis_v1.schemas import AppealPackage

EXPECTED_TOOLS = {
    "case_parser",
    "corpus_retrieval",
    "phoenix_mcp_lookup",
    "playbook_loader",
    "drafter",
    "self_check",
}


def test_legacy_root_agent_kept_for_reference() -> None:
    assert legacy_root_agent.name == "aegis_v1"
    assert legacy_root_agent.output_schema is AppealPackage
    assert LEGACY_AEGIS_V1_TOOL_NAMES == EXPECTED_TOOLS

    tool_names = {
        getattr(tool, "__name__", getattr(tool, "name", ""))
        for tool in legacy_root_agent.tools
    }
    assert tool_names == EXPECTED_TOOLS
    assert "simulator" not in tool_names


def test_legacy_instruction_requires_ordered_tool_flow_and_disclaimer() -> None:
    instruction = str(legacy_root_agent.instruction)
    for tool_name in LEGACY_AEGIS_V1_TOOL_NAMES:
        assert tool_name in instruction
    assert "Not legal or medical advice. Draft assistance only." in instruction
    assert "JSON" in instruction
