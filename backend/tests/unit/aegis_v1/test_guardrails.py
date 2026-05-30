from app.aegis_v1.guardrails import apply_guardrails
from app.aegis_v1.tools import DISCLAIMER


def test_guardrails_inject_disclaimer_when_missing():
    out = apply_guardrails("Please review this appeal.", allowed_doc_ids={"erisa_503.md"})
    assert DISCLAIMER.lower() in out.lower()


def test_guardrails_strip_exclamation_marks():
    out = apply_guardrails("Approve this now!", allowed_doc_ids=set())
    assert "!" not in out


def test_guardrails_soften_guarantee_language():
    out = apply_guardrails("This appeal will win.", allowed_doc_ids=set())
    assert "will win" not in out.lower()
