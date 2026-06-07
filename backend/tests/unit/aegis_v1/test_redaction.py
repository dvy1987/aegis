from __future__ import annotations

from app.aegis_v1.redaction import redact_identifiers

FIXTURE = """
Patient: Jordan Lee
Member ID: CIG-8844221
DOB: 03/14/1988
Phone: (555) 123-4567
Email: jordan.lee@example.com

Clinical summary: The member has severe OCD with daily compulsions lasting six hours. Weekly outpatient therapy failed after twelve sessions. Intensive Outpatient Program was recommended for step-up care. Denial cited lack of medical necessity despite documented functional impairment.
""".strip()


def test_redaction_strips_identifiers_but_preserves_clinical_facts():
    result = redact_identifiers(FIXTURE)

    assert "Jordan Lee" not in result.text
    assert "CIG-8844221" not in result.text
    assert "03/14/1988" not in result.text
    assert "555" not in result.text
    assert "jordan.lee@example.com" not in result.text

    assert "severe OCD" in result.text
    assert "six hours" in result.text
    assert "Intensive Outpatient Program" in result.text
    assert "medical necessity" in result.text
    assert result.redacted_fields
