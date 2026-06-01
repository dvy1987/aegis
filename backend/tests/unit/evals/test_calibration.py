from app.evals.part_a.calibration import calibration_report, cohens_kappa


def test_kappa_identical_sequences_is_one():
    assert cohens_kappa([1, 3, 5, 3, 1], [1, 3, 5, 3, 1]) == 1.0


def test_kappa_opposite_sequences_is_below_gate():
    # systematic disagreement -> kappa well below the 0.6 gate (negative, in fact)
    assert cohens_kappa([1, 5, 1, 5, 1, 5], [5, 1, 5, 1, 5, 1]) < 0.6


def test_calibration_report_flags_below_gate_dimensions():
    rep = calibration_report({
        "grounding": [(1, 1), (3, 3), (5, 5), (3, 3)],            # perfect agreement
        "appeal_vector_capture": [(1, 5), (5, 1), (3, 5), (5, 1)],  # poor agreement
    })
    assert rep["kappa_by_dimension"]["grounding"] == 1.0
    assert rep["flags"]["appeal_vector_capture"] == "below_gate"
    assert rep["flags"]["grounding"] == "ok"
    assert rep["gate_pass"] is False
