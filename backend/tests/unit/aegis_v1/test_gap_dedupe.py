from app.aegis_v1.gap_dedupe import dedupe_gap_questions


def test_dedupe_gap_questions_collapses_doctor_letter_themes() -> None:
    gaps = dedupe_gap_questions(
        [
            "Did your oncologist send a letter explaining why venetoclax is needed?",
            "Did your doctor submit a formulary exception letter to Aetna?",
            "Which preferred medication does the plan require?",
        ]
    )
    assert len(gaps) == 2
    assert gaps[0].startswith("Did your oncologist")
    assert "preferred medication" in gaps[1]


def test_dedupe_gap_questions_preserves_distinct_themes() -> None:
    gaps = dedupe_gap_questions(
        [
            "What symptoms affect your daily life?",
            "Have you tried other treatments before?",
        ]
    )
    assert len(gaps) == 2
