from __future__ import annotations

from app.aegis_swarm.agent import app, root_agent, run_swarm_appeal


def test_root_agent_has_swarm_tool() -> None:
    assert root_agent.name == "aegis_swarm_coordinator"
    assert run_swarm_appeal in root_agent.tools
    assert app.name == "aegis_swarm"


def test_run_swarm_appeal_offline() -> None:
    result = run_swarm_appeal(
        denial_text=(
            "Cigna denied CPT 90837 as not medically necessary for major depressive disorder."
        ),
        case_id="agent-tool-test",
    )
    assert "appeal_package" in result
    assert result["appeal_package"]["trace_metadata"]["case_id"] == "agent-tool-test"
