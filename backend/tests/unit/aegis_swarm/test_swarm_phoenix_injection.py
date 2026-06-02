from app.aegis_swarm.client import StubSwarmClient
from app.aegis_swarm.swarm_pipeline import run_swarm_pipeline


def test_pipeline_uses_injected_phoenix_lookup() -> None:
    seen: list[str] = []

    def fake_lookup(insurer: str, denial_type: str, case_id: str) -> dict:
        seen.append(f"{insurer}:{denial_type}:{case_id}")
        return {"status": "disabled", "risk_flags": ["phoenix_mcp_disabled"]}

    run_swarm_pipeline(
        denial_text="Denied TMS.",
        clinical_context="Failed SSRIs.",
        case_id="inj_1",
        client=StubSwarmClient(),
        phoenix_lookup=fake_lookup,
    )
    assert seen == ["unknown:unknown:inj_1"]
