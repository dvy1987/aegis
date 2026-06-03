"""Unit tests for library seed catalog and validation."""

from __future__ import annotations

from pathlib import Path

from app.library.ingest import validate_catalog
from app.library.models import load_seed_catalog

CATALOG = Path(__file__).resolve().parents[3] / "library" / "seed_catalog.json"


def test_seed_catalog_loads_and_validates() -> None:
    if not CATALOG.exists():
        return  # generated in CI step or locally first
    cat = load_seed_catalog(CATALOG)
    assert len(cat.entries) >= 40
    errors = validate_catalog(cat)
    assert errors == [], errors


def test_priority_1_covers_all_insurers() -> None:
    if not CATALOG.exists():
        return
    cat = load_seed_catalog(CATALOG)
    p1 = [e for e in cat.entries if e.priority == 1]
    insurers_p1 = set()
    for e in p1:
        insurers_p1.update(e.insurers)
    for ins in ("Aetna", "Cigna", "UHC"):
        assert ins in insurers_p1 or any(
            e.domain == "insurer" and ins in e.insurers for e in p1
        ), f"missing priority-1 insurer coverage for {ins}"
