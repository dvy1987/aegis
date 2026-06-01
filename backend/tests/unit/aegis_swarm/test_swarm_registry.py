from __future__ import annotations

import pytest

from app.aegis_swarm.prompts import registry


def test_all_ten_agent_roles_have_loadable_prompts() -> None:
    assert len(registry.AGENT_ROLES) == 10
    for role in registry.AGENT_ROLES:
        text = registry.load_prompt(role)
        assert text.strip()
        expected = "v1_weak" if role in registry.WEAK_V1_AGENTS else "v1"
        assert registry.current_version(role) == expected


def test_weak_v1_agents_are_pinned_to_weak_baseline() -> None:
    assert set(registry.WEAK_V1_AGENTS) == {"drafter", "strategist", "medical_necessity"}
    for role in registry.WEAK_V1_AGENTS:
        assert registry.is_weak_agent(role) is True
        assert registry.current_version(role) == "v1_weak"
        assert "v1_weak" in registry.available_versions(role)


def test_strong_reference_is_quarantined_not_a_loadable_version() -> None:
    # Evolution integrity: the strong target must NOT be reachable as a version
    # (so a Phase 6 optimizer seed can't read it), only via the explicit ceiling API.
    for role in registry.WEAK_V1_AGENTS:
        assert "v1" not in registry.available_versions(role)
        assert registry.has_target_reference(role) is True
        ref = registry.load_target_reference(role)
        assert ref.strip()
        # the reference is the strong prompt (has the rich scaffolding the weak one lacks)
        assert "Worked Example" in ref or "Chain-of-Thought" in ref


def test_runtime_prompt_carries_no_experiment_metadata() -> None:
    # The "deliberately weak" rationale must never reach a model at runtime.
    for role in registry.WEAK_V1_AGENTS:
        body = registry.load_prompt(role)
        assert "DELIBERATELY WEAK" not in body
        assert "deliberately weak" not in body.lower()
        assert "demo scaffold" not in body.lower()


def test_non_weak_agents_start_strong() -> None:
    for role in registry.AGENT_ROLES:
        if role in registry.WEAK_V1_AGENTS:
            continue
        assert registry.is_weak_agent(role) is False
        assert registry.current_version(role) == "v1"


def test_weak_prompts_keep_safety_gates() -> None:
    # The deliberate weakness is quality-only; every weak prompt keeps its safety
    # guardrails (disclaimer / no-invention / no-"human").
    for role in registry.WEAK_V1_AGENTS:
        text = registry.load_prompt(role).lower()
        assert "never" in text
        assert "human" in text  # the "never use the word human" rule is present


def test_load_prompt_returns_role_specific_content() -> None:
    assert "Triage Agent" in registry.load_prompt("triage")
    assert "Drafter" in registry.load_prompt("drafter")


def test_available_versions_includes_v1() -> None:
    # triage is a non-weak agent, so its strong v1 is a loadable version.
    assert "v1" in registry.available_versions("triage")


def test_list_components_is_one_prompt_component_per_role() -> None:
    components = registry.list_components()
    assert len(components) == len(registry.AGENT_ROLES)
    assert {c.component_id for c in components} == set(registry.AGENT_ROLES)
    assert all(c.kind == "prompt" and c.text.strip() for c in components)


def test_unknown_role_raises() -> None:
    with pytest.raises(KeyError):
        registry.load_prompt("nonexistent_agent")


def test_missing_version_raises_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        registry.load_prompt("drafter", version="v999")
