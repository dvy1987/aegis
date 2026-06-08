from app.aegis_v1.phoenix_mcp import _memory_eligible, _slice_filter


def test_memory_eligible_defaults_true_when_unset() -> None:
    assert _memory_eligible({}) is True
    assert _memory_eligible({"aegis.insurer": "Cigna"}) is True


def test_memory_eligible_false_values_excluded() -> None:
    for value in ("false", "False", "0", "no"):
        assert _memory_eligible({"aegis.memory_eligible": value}) is False


def test_slice_filter_requires_memory_eligible_true() -> None:
    attrs = {
        "aegis.insurer": "cigna",
        "aegis.denial_type": "medical_necessity",
        "aegis.memory_eligible": "false",
    }
    assert _slice_filter(attrs, insurer="Cigna", denial_type="medical_necessity") is False

    attrs["aegis.memory_eligible"] = "true"
    assert _slice_filter(attrs, insurer="Cigna", denial_type="medical_necessity") is True
