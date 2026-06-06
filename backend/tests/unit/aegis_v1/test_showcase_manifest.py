from __future__ import annotations

from app.aegis_v1.showcase_manifest import load_showcase_manifest


def test_manifest_loads_targeted_quick_cohort() -> None:
    manifest = load_showcase_manifest()

    assert manifest.benchmark_id == "v1_showcase_100"
    assert len(manifest.quick_train) == 10
    assert {case.insurer for case in manifest.quick_train} == {"Cigna"}
    assert {case.denial_type for case in manifest.quick_train} == {"medical_necessity"}


def test_manifest_serious_train_and_holdout_do_not_overlap() -> None:
    manifest = load_showcase_manifest()

    serious_train_ids = {case.case_id for case in manifest.serious_train}
    holdout_ids = {case.case_id for case in manifest.serious_holdout}

    assert len(manifest.serious_train) == 80
    assert len(manifest.serious_holdout) == 10
    assert serious_train_ids.isdisjoint(holdout_ids)


def test_manifest_case_metadata_is_student_safe() -> None:
    manifest = load_showcase_manifest()
    public = manifest.quick_train[0].model_dump()

    assert "denial_letter_text" in public
    assert "clinical_context" in public
    assert "expected_appeal_vectors" not in public
    assert "exploitable_weaknesses" not in public
    assert "synthetic_provenance" not in public
