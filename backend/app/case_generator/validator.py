from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import jsonschema

from .config import load_schema


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]


def validate_case(case_obj: dict[str, Any]) -> ValidationResult:
    schema = load_schema()
    validator = jsonschema.Draft202012Validator(schema)
    errs = sorted(validator.iter_errors(case_obj), key=lambda e: list(e.path))
    if not errs:
        return ValidationResult(ok=True, errors=[])
    return ValidationResult(
        ok=False,
        errors=[
            f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errs
        ],
    )
