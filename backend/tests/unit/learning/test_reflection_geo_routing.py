from app.aegis_v1.geo_playbook import US_PLAYBOOK_COMPONENT_ID
from app.learning.models import Component, DimensionSignal
from app.learning.reflection_client import _question_judge_playbook_recs


def test_question_judge_recs_route_global_vs_slice() -> None:
    signal = DimensionSignal(
        component_id=US_PLAYBOOK_COMPONENT_ID,
        weakest_dimension="grounding",
        notes={
            "question_agent": [
                "Add to global playbook: cite ERISA review rights.",
                "Add to playbook:Cigna:medical_necessity:x: mention step therapy.",
            ]
        },
    )
    global_recs = _question_judge_playbook_recs(signal, geo=True)
    slice_recs = _question_judge_playbook_recs(signal, geo=False)
    assert len(global_recs) == 1
    assert "global playbook" in global_recs[0].lower()
    assert len(slice_recs) == 1
    assert "playbook:cigna" in slice_recs[0].lower()


def test_stub_reflection_appends_us_rule() -> None:
    from app.learning.reflection_client import StubReflectionClient

    component = Component(
        component_id=US_PLAYBOOK_COMPONENT_ID,
        kind="playbook",
        version="day_zero",
        playbook={"rules": [], "version": "day_zero"},
    )
    signal = DimensionSignal(
        component_id=US_PLAYBOOK_COMPONENT_ID,
        weakest_dimension="grounding",
    )
    revised = StubReflectionClient().reflect(
        component=component, signal=signal, minibatch=[]
    )
    assert revised.version != "day_zero"
    assert len(revised.playbook["rules"]) == 1
