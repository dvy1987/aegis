from app.learning.slice_key import format_slice_key, parse_slice_key, sub_tactic_from_case


def test_format_slice_key_includes_sub_tactic() -> None:
    assert (
        format_slice_key("Cigna", "Medical Necessity", "not_evidence_based")
        == "Cigna:medical_necessity:not_evidence_based"
    )


def test_sub_tactic_from_teacher_case() -> None:
    case = {
        "synthetic_provenance": {
            "matrix_cell": {"sub_tactic": "frequency_excessive"},
        }
    }
    assert sub_tactic_from_case(case) == "frequency_excessive"


def test_parse_slice_key_round_trip() -> None:
    key = "UnitedHealthcare:prior_authorization:visit_limit_exceeded"
    assert parse_slice_key(key) == (
        "UnitedHealthcare",
        "prior_authorization",
        "visit_limit_exceeded",
    )
