from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "eval" / "benchmarks" / "v1_showcase_100" / "manifest.json"
CASES_DIR = REPO_ROOT / "eval" / "cases" / "drafts"


class ShowcaseCase(BaseModel):
    case_id: str
    path: str
    insurer: str
    denial_type: str
    denial_letter_text: str
    clinical_context: str = ""


class ShowcaseManifest(BaseModel):
    benchmark_id: str
    version: str
    selection_policy: dict[str, str] = Field(default_factory=dict)
    quick_train: list[ShowcaseCase]
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
    return ShowcaseCase(
        case_id=case_id,
        path=str(path.relative_to(REPO_ROOT)),
        insurer=str(data.get("insurer") or "unknown"),
        denial_type=str(data.get("denial_type") or "unknown").replace(" ", "_").lower(),
        denial_letter_text=str(data.get("denial_letter_text") or ""),
        clinical_context=str(data.get("clinical_context") or ""),
    )


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
    serious_train = _load_cases(list(raw.get("serious_train") or []))
    serious_holdout = _load_cases(list(raw.get("serious_holdout") or []))

    if len(quick) != 10:
        raise ValueError("quick_train must contain exactly 10 cases")
    if len(serious_holdout) != 10:
        raise ValueError("serious_holdout must contain exactly 10 cases")
    train_ids = {case.case_id for case in serious_train}
    holdout_ids = {case.case_id for case in serious_holdout}
    if train_ids & holdout_ids:
        raise ValueError("serious_train and serious_holdout must not overlap")
    if train_ids & {case.case_id for case in quick}:
        raise ValueError("quick_train and serious_train must not overlap")

    return ShowcaseManifest(
        benchmark_id=str(raw["benchmark_id"]),
        version=str(raw["version"]),
        selection_policy=dict(raw.get("selection_policy") or {}),
        quick_train=quick,
        serious_train=serious_train,
        serious_holdout=serious_holdout,
    )
