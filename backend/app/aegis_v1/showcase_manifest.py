from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

REPO_ROOT = Path(os.environ.get("AEGIS_REPO_ROOT", Path(__file__).resolve().parents[3]))
DEFAULT_MANIFEST_PATH = REPO_ROOT / "eval" / "benchmarks" / "v1_showcase_100" / "manifest.json"
CASES_DIR = REPO_ROOT / "eval" / "cases" / "drafts"


class ShowcaseCase(BaseModel):
    case_id: str
    headline: str
    path: str
    insurer: str
    denial_type: str
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
            return "unknown:unknown"
        first = self.quick_train[0]
        return f"{first.insurer}:{first.denial_type}"


def _case_path(case_id: str) -> Path:
    return CASES_DIR / f"{case_id}.json"


def _load_case(case_id: str) -> ShowcaseCase:
    path = _case_path(case_id)
    if not path.exists():
        raise FileNotFoundError(f"Manifest case not found: {case_id}")
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    actual_id = data.get("case_id") or path.stem
    if actual_id != case_id:
        raise ValueError(f"Manifest case id mismatch: {case_id} != {actual_id}")
    profile = data.get("patient_profile") or {}
    return ShowcaseCase(
        case_id=case_id,
        headline=case_id,
        path=str(path.relative_to(REPO_ROOT)),
        insurer=str(data.get("insurer") or "unknown"),
        denial_type=str(data.get("denial_type") or "unknown").replace(" ", "_").lower(),
        denial_letter_text=str(data.get("denial_letter_text") or ""),
        clinical_context=str(data.get("clinical_context") or ""),
        patient_age=int(profile.get("age") or 0),
        patient_gender=str(profile.get("gender") or ""),
        teacher_case=data,
    )


def _case_number(case_id: str) -> int:
    parts = case_id.split("_")
    if len(parts) < 2 or parts[0] != "case" or not parts[1].isdigit():
        raise ValueError(f"Unrecognized case id format: {case_id}")
    return int(parts[1])


def _load_cases(case_ids: list[str]) -> list[ShowcaseCase]:
    seen: set[str] = set()
    out: list[ShowcaseCase] = []
    for case_id in case_ids:
        if case_id in seen:
            raise ValueError(f"Duplicate case in manifest: {case_id}")
        seen.add(case_id)
        out.append(_load_case(case_id))
    return out


def load_showcase_manifest(path: Path | None = None) -> ShowcaseManifest:
    manifest_path = path or DEFAULT_MANIFEST_PATH
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    quick = _load_cases(list(raw.get("quick_train") or []))
    quick_holdout = _load_cases(list(raw.get("quick_holdout") or []))
    serious_train = _load_cases(list(raw.get("serious_train") or []))
    serious_holdout = _load_cases(list(raw.get("serious_holdout") or []))

    if len(quick) != 8:
        raise ValueError("quick_train must contain exactly 8 cases")
    if len(quick_holdout) != 2:
        raise ValueError("quick_holdout must contain exactly 2 cases")
    if len(serious_train) != 80:
        raise ValueError("serious_train must contain exactly 80 cases")
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
    serious_ids = train_ids | holdout_ids
    if quick_train_ids & serious_ids or quick_holdout_ids & serious_ids:
        raise ValueError("quick cohort must not overlap cases 1-100 serious benchmark")
    for case_id in quick_train_ids | quick_holdout_ids:
        number = _case_number(case_id)
        if not 101 <= number <= 200:
            raise ValueError(f"quick cohort case must be numbered 101-200: {case_id}")

    return ShowcaseManifest(
        benchmark_id=str(raw["benchmark_id"]),
        version=str(raw["version"]),
        selection_policy=dict(raw.get("selection_policy") or {}),
        quick_train=quick,
        quick_holdout=quick_holdout,
        serious_train=serious_train,
        serious_holdout=serious_holdout,
    )
