import json

from app.learning.models import Component, DimensionSignal, ScoredRun
from app.aegis_v1.question_agent import (
    QUESTION_AGENT_INTERVIEW_LIMITS_BLOCK,
    QUESTION_AGENT_REGULATORY_FIREWALL_BLOCK,
    ensure_question_agent_prompt_invariants,
)
from app.learning.reflection_client import (
    AnthropicReflectionClient,
    GeminiReflectionClient,
    PROMPT_WORD_CAP,
    StubReflectionClient,
    _apply_text_edit,
    _parse_reflection_response,
    _validate_prompt_text,
    build_reflection_prompt,
)


def _signal(dim="appeal_vector_capture"):
    return DimensionSignal(
        component_id="playbook:Cigna:medical_necessity:not_evidence_based",
        weakest_dimension=dim,
        failing_cases=[],
        notes={dim: ["missed the specific denial flaw"]},
    )


def test_stub_reflects_playbook_by_tagging_target_dimension():
    comp = Component(
        component_id="playbook:Cigna:medical_necessity:not_evidence_based",
        kind="playbook",
        version="v1",
        playbook={"tactics": [], "required_evidence": [], "dimension_targets": []},
    )
    out = StubReflectionClient().reflect(component=comp, signal=_signal(), minibatch=[])
    assert "appeal_vector_capture" in out.playbook["dimension_targets"]
    assert out.playbook["tactics"]


def test_stub_reflects_prompt_without_rubric_jargon():
    comp = Component(
        component_id="drafter_system_prompt",
        kind="prompt",
        version="v1",
        text="Draft an appeal.",
    )
    out = StubReflectionClient().reflect(
        component=comp, signal=_signal("grounding"), minibatch=[]
    )
    assert "appeal_vector_capture" not in (out.text or "").lower()
    assert "Strengthen appeal quality" in (out.text or "")


def test_reflection_prompt_requires_json_and_prompt_caps():
    p = build_reflection_prompt(
        component=Component(component_id="drafter_system_prompt", kind="prompt", text="Draft."),
        signal=_signal(),
        minibatch=[],
    )
    assert "reflection_critique" in p
    assert str(PROMPT_WORD_CAP) in p
    assert "geo_playbook:us" in p
    assert "state-statute" in p or "state law" in p
    assert "exploitable_weaknesses" not in p


def test_cloud_backends_construct_without_calls():
    assert GeminiReflectionClient().name == "gemini_reflection"
    assert AnthropicReflectionClient().name == "anthropic_reflection"


def test_question_agent_reflection_prompt_preserves_regulatory_firewall_rules():
    comp = Component(
        component_id="question_agent_system_prompt",
        kind="prompt",
        version="v1",
        text="Ask patient-knowable questions only.",
    )
    sig = DimensionSignal(
        component_id="question_agent_system_prompt",
        weakest_dimension="grounding",
        failing_cases=[],
        notes={
            "question_agent": [
                "Playbook additions (append-first): Add to global playbook: ERISA",
                "Ask the patient about plan language on coverage criteria.",
                "Ask about symptom timeline earlier.",
            ],
        },
    )
    prompt = build_reflection_prompt(component=comp, signal=sig, minibatch=[])
    assert QUESTION_AGENT_REGULATORY_FIREWALL_BLOCK in prompt
    assert QUESTION_AGENT_INTERVIEW_LIMITS_BLOCK in prompt
    assert "NEVER mutate the question agent" in prompt
    assert "5-question cap" in prompt
    assert "Ask the patient about plan language" not in prompt
    assert "Ask about symptom timeline earlier" in prompt
    assert "Playbook additions" not in prompt


def test_apply_text_edit_parses_json_and_strips_critique_from_prompt():
    comp = Component(
        component_id="drafter_system_prompt",
        kind="prompt",
        version="v1",
        text="Draft an appeal.",
    )
    payload = {
        "reflection_critique": "The draft missed seizure history.",
        "revised_component": "# Drafter\nWrite a clear appeal using patient facts only.",
    }
    out = _apply_text_edit(comp, json.dumps(payload))
    assert out.version == "v2"
    assert out.text.startswith("# Drafter")
    assert "CRITIQUE" not in (out.text or "").upper()
    assert out.reflection_critique == "The draft missed seizure history."


def test_apply_text_edit_rejects_critique_inlined_in_prompt():
    comp = Component(
        component_id="drafter_system_prompt",
        kind="prompt",
        version="v1",
        text="Draft an appeal.",
    )
    bad = (
        "CRITIQUE: Fix appeal vectors.\n\n"
        "# Drafter\nWrite a clear appeal."
    )
    out = _apply_text_edit(comp, json.dumps({"reflection_critique": "", "revised_component": bad}))
    assert out.version == "v1"
    assert out.text == "Draft an appeal."


def test_apply_text_edit_rejects_rubric_jargon_in_prompt():
    comp = Component(
        component_id="drafter_system_prompt",
        kind="prompt",
        version="v1",
        text="Draft an appeal.",
    )
    bad = "Maximize appeal vector capture in every letter."
    out = _apply_text_edit(
        comp, json.dumps({"reflection_critique": "too jargon", "revised_component": bad})
    )
    assert out.version == "v1"


def test_apply_text_edit_rejects_prompt_over_word_cap():
    comp = Component(
        component_id="drafter_system_prompt",
        kind="prompt",
        version="v1",
        text="Draft an appeal.",
    )
    long_body = "word " * (PROMPT_WORD_CAP + 1)
    out = _apply_text_edit(
        comp,
        json.dumps({"reflection_critique": "too long", "revised_component": long_body}),
    )
    assert out.version == "v1"


def test_apply_text_edit_reinjects_question_agent_invariants():
    comp = Component(
        component_id="question_agent_system_prompt",
        kind="prompt",
        version="v1",
        text="Ask patient facts.\n\n## How to interview\n- **Adapt**: follow up",
    )
    stripped = "Ask patient facts.\n\n## How to interview\n- **Adapt**: follow up"
    out = _apply_text_edit(
        comp,
        json.dumps({"reflection_critique": "ok", "revised_component": stripped}),
    )
    assert QUESTION_AGENT_REGULATORY_FIREWALL_BLOCK in (out.text or "")
    assert QUESTION_AGENT_INTERVIEW_LIMITS_BLOCK in (out.text or "")
    assert out.version == "v2"


def test_ensure_question_agent_prompt_invariants_idempotent():
    original = (
        "Intro.\n\n"
        + QUESTION_AGENT_REGULATORY_FIREWALL_BLOCK
        + "\n\n## How to interview\n"
        + QUESTION_AGENT_INTERVIEW_LIMITS_BLOCK
        + "\n"
    )
    assert ensure_question_agent_prompt_invariants(original) == original.strip()


def test_build_reflection_prompt_supports_named_variant():
    comp = Component(component_id="drafter_system_prompt", kind="prompt", text="Draft.")
    sig = DimensionSignal(
        component_id="drafter_system_prompt",
        weakest_dimension="appeal_vector_capture",
        failing_cases=[],
        notes={"appeal_vector_capture": ["missed the specific flaw"]},
    )
    base = build_reflection_prompt(component=comp, signal=sig, minibatch=[])
    v2 = build_reflection_prompt(component=comp, signal=sig, minibatch=[], variant="critique_plus")
    assert "reflection_critique" in v2
    assert v2 != base
    assert "exploitable_weaknesses" not in v2


def test_parse_reflection_response_json():
    critique, body = _parse_reflection_response(
        json.dumps({"reflection_critique": "note", "revised_component": "prompt text"})
    )
    assert critique == "note"
    assert body == "prompt text"


def test_validate_prompt_text_rejects_critique_header():
    text, reason = _validate_prompt_text(
        "CRITIQUE: bad.\n\n# Drafter\nShort prompt."
    )
    assert text is None
    assert reason == "critique_in_prompt_body"
