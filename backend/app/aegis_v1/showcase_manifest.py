from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

REPO_ROOT = Path(os.environ.get("AEGIS_REPO_ROOT", Path(__file__).resolve().parents[3]))
DEFAULT_MANIFEST_PATH = REPO_ROOT / "eval" / "benchmarks" / "v1_showcase_100" / "manifest.json"
DEFAULT_QUICK_CASES_DIR = REPO_ROOT / "eval" / "cases" / "approved" / "preview-run"
DEFAULT_SERIOUS_CASES_DIR = REPO_ROOT / "eval" / "cases" / "approved" / "prod-run"


class ShowcaseCase(BaseModel):
    case_id: str
    headline: str
    path: str
    insurer: str
    denial_type: str
    sub_tactic: str = "unknown"
    denial_letter_text: str
    clinical_context: str = ""
    patient_age: int = 0
    patient_gender: str = ""
    teacher_case: dict[str, Any] = Field(default_factory=dict, exclude=True)

    def student_case(self, *, dataset_split: str) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "denial_letter_text": self.denial_letter_text,
            "insurer": self.insurer,
            "patient_age": self.patient_age,
            "patient_gender": self.patient_gender,
            "dataset_split": dataset_split,
        }

    def judge_case(self, *, dataset_split: str) -> dict[str, Any]:
        case = dict(self.teacher_case)
        case.update(self.student_case(dataset_split=dataset_split))
        return case


class ShowcaseManifest(BaseModel):
    benchmark_id: str
    version: str
    selection_policy: dict[str, str] = Field(default_factory=dict)
    quick_train: list[ShowcaseCase]
    quick_holdout: list[ShowcaseCase]
    serious_train: list[ShowcaseCase]
    serious_holdout: list[ShowcaseCase]

    @property
    def quick_slice(self) -> str:
        if not self.quick_train:
            return "unknown:unknown:unknown"
        first = self.quick_train[0]
        from app.learning.slice_key import format_slice_key

        return format_slice_key(first.insurer, first.denial_type, first.sub_tactic)


def _resolve_cases_dir(raw: dict[str, Any], *, cohort: str) -> Path:
    paths = raw.get("case_paths") or {}
    rel = paths.get(cohort)
    if isinstance(rel, str) and rel.strip():
        return REPO_ROOT / rel
    if cohort == "serious":
        return DEFAULT_SERIOUS_CASES_DIR
    return DEFAULT_QUICK_CASES_DIR


def _load_case(case_id: str, *, cases_dir: Path) -> ShowcaseCase:
    path = cases_dir / f"{case_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Manifest case not found: {case_id}")
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    actual_id = data.get("case_id") or path.stem
    if actual_id != case_id:
        raise ValueError(f"Manifest case id mismatch: {case_id} != {actual_id}")
    profile = data.get("patient_profile") or {}
    matrix_cell = (data.get("synthetic_provenance") or {}).get("matrix_cell") or {}
    sub_tactic = str(matrix_cell.get("sub_tactic") or "unknown")
    return ShowcaseCase(
        case_id=case_id,
        headline=case_id,
        path=str(path.relative_to(REPO_ROOT)),
        insurer=str(data.get("insurer") or "unknown"),
        denial_type=str(data.get("denial_type") or "unknown").replace(" ", "_").lower(),
        sub_tactic=sub_tactic,
        denial_letter_text=str(data.get("denial_letter_text") or ""),
        clinical_context=str(data.get("clinical_context") or ""),
        patient_age=int(profile.get("age") or 0),
        patient_gender=str(profile.get("gender") or ""),
        teacher_case=data,
    )


def _case_slice(case: ShowcaseCase) -> tuple[str, str, str]:
    return (case.insurer, case.denial_type, case.sub_tactic)


def _case_number(case_id: str) -> int:
    parts = case_id.split("_")
    if len(parts) < 2 or parts[0] != "case" or not parts[1].isdigit():
        raise ValueError(f"Unrecognized case id format: {case_id}")
    return int(parts[1])


def _load_cases(case_ids: list[str], *, cases_dir: Path) -> list[ShowcaseCase]:
    seen: set[str] = set()
    out: list[ShowcaseCase] = []
    for case_id in case_ids:
        if case_id in seen:
            raise ValueError(f"Duplicate case in manifest: {case_id}")
        seen.add(case_id)
        out.append(_load_case(case_id, cases_dir=cases_dir))
    return out


def load_showcase_manifest(path: Path | None = None) -> ShowcaseManifest:
    manifest_path = path or DEFAULT_MANIFEST_PATH
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    quick_dir = _resolve_cases_dir(raw, cohort="quick")
    serious_dir = _resolve_cases_dir(raw, cohort="serious")
    quick = _load_cases(list(raw.get("quick_train") or []), cases_dir=quick_dir)
    quick_holdout = _load_cases(list(raw.get("quick_holdout") or []), cases_dir=quick_dir)
    serious_train = _load_cases(list(raw.get("serious_train") or []), cases_dir=serious_dir)
    serious_holdout = _load_cases(list(raw.get("serious_holdout") or []), cases_dir=serious_dir)

    if len(quick) != 5:
        raise ValueError("quick_train must contain exactly 5 cases")
    if len(quick_holdout) != 2:
        raise ValueError("quick_holdout must contain exactly 2 cases")
    if len(serious_train) != 50:
        raise ValueError("serious_train must contain exactly 50 cases")
    if len(serious_holdout) != 20:
        raise ValueError("serious_holdout must contain exactly 20 cases")
    quick_train_ids = {case.case_id for case in quick}
    quick_holdout_ids = {case.case_id for case in quick_holdout}
    train_ids = {case.case_id for case in serious_train}
    holdout_ids = {case.case_id for case in serious_holdout}
    if quick_train_ids & quick_holdout_ids:
        raise ValueError("quick_train and quick_holdout must not overlap")
    if train_ids & holdout_ids:
        raise ValueError("serious_train and serious_holdout must not overlap")
    train_slices = {_case_slice(case) for case in serious_train}
    for case in serious_holdout:
        if _case_slice(case) not in train_slices:
            raise ValueError(
                f"serious_holdout case {case.case_id} has no same-slice sibling in serious_train"
            )
    serious_ids = train_ids | holdout_ids
    if quick_train_ids & serious_ids or quick_holdout_ids & serious_ids:
        raise ValueError("quick cohort must not overlap production cohort cases")
    cohort_101_200 = quick_train_ids | quick_holdout_ids | serious_ids
    for case_id in cohort_101_200:
        number = _case_number(case_id)
        if not 101 <= number <= 200:
            raise ValueError(f"showcase cohort case must be numbered 101-200: {case_id}")

    return ShowcaseManifest(
        benchmark_id=str(raw["benchmark_id"]),
        version=str(raw["version"]),
        selection_policy=dict(raw.get("selection_policy") or {}),
        quick_train=quick,
        quick_holdout=quick_holdout,
        serious_train=serious_train,
        serious_holdout=serious_holdout,
    )
