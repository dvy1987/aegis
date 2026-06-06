from __future__ import annotations

from app.aegis_v1.showcase_manifest import load_showcase_manifest


def test_manifest_loads_targeted_quick_cohort() -> None:
    manifest = load_showcase_manifest()

    assert manifest.benchmark_id == "v1_showcase_100"
    assert len(manifest.quick_train) == 8
    assert len(manifest.quick_holdout) == 2
    assert {case.insurer for case in manifest.quick_train} == {"Cigna"}
    assert {case.denial_type for case in manifest.quick_train} == {"medical_necessity"}
    assert {case.insurer for case in manifest.quick_holdout} == {"Cigna"}
    assert {case.denial_type for case in manifest.quick_holdout} == {"medical_necessity"}


def test_manifest_quick_sets_are_subsets_of_serious_sets() -> None:
    manifest = load_showcase_manifest()

    quick_train_ids = {case.case_id for case in manifest.quick_train}
    quick_holdout_ids = {case.case_id for case in manifest.quick_holdout}
    serious_train_ids = {case.case_id for case in manifest.serious_train}
    holdout_ids = {case.case_id for case in manifest.serious_holdout}

    assert len(manifest.serious_train) == 80
    assert len(manifest.serious_holdout) == 20
    assert serious_train_ids.isdisjoint(holdout_ids)
    assert quick_train_ids <= serious_train_ids
    assert quick_holdout_ids <= holdout_ids
    assert len(quick_train_ids | quick_holdout_ids | serious_train_ids | holdout_ids) == 100


def test_manifest_case_metadata_is_student_safe() -> None:
    manifest = load_showcase_manifest()
    public = manifest.quick_train[0].model_dump()

    assert public["headline"]
    assert "denial_letter_text" in public
    assert "clinical_context" in public
    assert "expected_appeal_vectors" not in public
    assert "exploitable_weaknesses" not in public
    assert "synthetic_provenance" not in public
