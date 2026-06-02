"""Fixed matrix cells for MVP calibration set (case_01–case_20 in flat drafts/).

Train/holdout split is assigned only after Gumloop → approved/; specs here only
preserve ``case_id`` strings and insurer/denial pairings for regeneration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class CalibrationSpec:
    case_id: str
    split: Literal["calibration"]  # legacy tag; not a filesystem train/test split
    cell: dict[str, str]
    build_index: int  # RNG offset for variant selection within specialty


def _cell(
    insurer: str,
    denial_type: str,
    specialty: str,
    sub_tactic: str,
    age_band: str = "26-40",
    gender: str = "F",
) -> dict[str, str]:
    return {
        "insurer": insurer,
        "denial_type": denial_type,
        "specialty": specialty,
        "sub_tactic": sub_tactic,
        "patient_age_band": age_band,
        "patient_gender": gender,
    }


# case_01 … case_10
TRAIN_SPECS: tuple[CalibrationSpec, ...] = (
    CalibrationSpec(
        "case_01_cigna_mednec",
        "calibration",
        _cell("Cigna", "Medical Necessity", "behavioral_health", "level_of_care_too_high", "26-40", "F"),
        1,
    ),
    CalibrationSpec(
        "case_02_cigna_priorauth",
        "calibration",
        _cell("Cigna", "Prior Authorization", "imaging", "emergency_retroactive_auth", "41-55", "M"),
        2,
    ),
    CalibrationSpec(
        "case_03_aetna_mednec",
        "calibration",
        _cell("Aetna", "Medical Necessity", "behavioral_health", "level_of_care_too_high", "41-55", "M"),
        3,
    ),
    CalibrationSpec(
        "case_04_aetna_priorauth",
        "calibration",
        _cell("Aetna", "Prior Authorization", "infusion_specialty_rx", "continuation_of_care_lapsed", "26-40", "F"),
        4,
    ),
    CalibrationSpec(
        "case_05_uhc_mednec",
        "calibration",
        _cell("UHC", "Medical Necessity", "endocrine", "step_therapy_missing", "41-55", "M"),
        5,
    ),
    CalibrationSpec(
        "case_06_uhc_priorauth",
        "calibration",
        _cell("UHC", "Prior Authorization", "womens_health", "out_of_network_no_authorization", "26-40", "F"),
        6,
    ),
    CalibrationSpec(
        "case_07_cigna_mednec",
        "calibration",
        _cell("Cigna", "Medical Necessity", "surgical", "conservative_treatment_required", "41-55", "F"),
        7,
    ),
    CalibrationSpec(
        "case_08_cigna_priorauth",
        "calibration",
        _cell("Cigna", "Prior Authorization", "msk", "visit_limit_exceeded", "56-70", "M"),
        8,
    ),
    CalibrationSpec(
        "case_09_aetna_mednec",
        "calibration",
        _cell("Aetna", "Medical Necessity", "surgical", "conservative_treatment_required", "41-55", "F"),
        9,
    ),
    CalibrationSpec(
        "case_10_uhc_priorauth",
        "calibration",
        _cell("UHC", "Prior Authorization", "imaging", "modality_substitution", "56-70", "M"),
        10,
    ),
)

# case_11 … case_20 (same drafts/ folder; train vs test assigned post-approval)
CALIBRATION_SPECS_B: tuple[CalibrationSpec, ...] = (
    CalibrationSpec(
        "case_11_uhc_mednec",
        "calibration",
        _cell("UHC", "Medical Necessity", "surgical", "conservative_treatment_required", "41-55", "F"),
        101,
    ),
    CalibrationSpec(
        "case_12_aetna_priorauth",
        "calibration",
        _cell("Aetna", "Prior Authorization", "imaging", "out_of_network_no_authorization", "18-25", "M"),
        102,
    ),
    CalibrationSpec(
        "case_13_cigna_mednec",
        "calibration",
        _cell("Cigna", "Medical Necessity", "endocrine", "not_evidence_based", "41-55", "F"),
        103,
    ),
    CalibrationSpec(
        "case_14_uhc_priorauth",
        "calibration",
        _cell("UHC", "Prior Authorization", "neurology", "guideline_mis_cite", "56-70", "F"),
        104,
    ),
    CalibrationSpec(
        "case_15_aetna_mednec",
        "calibration",
        _cell("Aetna", "Medical Necessity", "behavioral_health", "not_evidence_based", "26-40", "M"),
        105,
    ),
    CalibrationSpec(
        "case_16_cigna_priorauth",
        "calibration",
        _cell("Cigna", "Prior Authorization", "cardiology", "emergency_retroactive_auth", "56-70", "M"),
        106,
    ),
    CalibrationSpec(
        "case_17_uhc_mednec",
        "calibration",
        _cell("UHC", "Medical Necessity", "behavioral_health", "level_of_care_too_high", "18-25", "F"),
        107,
    ),
    CalibrationSpec(
        "case_18_aetna_priorauth",
        "calibration",
        _cell("Aetna", "Prior Authorization", "womens_health", "missing_peer_to_peer", "41-55", "F"),
        108,
    ),
    CalibrationSpec(
        "case_19_cigna_mednec",
        "calibration",
        _cell("Cigna", "Medical Necessity", "surgical", "not_evidence_based", "26-40", "M"),
        109,
    ),
    CalibrationSpec(
        "case_20_uhc_priorauth",
        "calibration",
        _cell("UHC", "Prior Authorization", "msk", "continuation_of_care_lapsed", "71+", "F"),
        110,
    ),
)

ALL_CALIBRATION_SPECS: tuple[CalibrationSpec, ...] = TRAIN_SPECS + CALIBRATION_SPECS_B
