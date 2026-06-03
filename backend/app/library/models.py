"""Pydantic models for the curated library seed catalog."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

LIBRARY_ROOT = Path(__file__).resolve().parents[2] / "library"
DEFAULT_CATALOG_PATH = LIBRARY_ROOT / "seed_catalog.json"

Domain = Literal["clinical", "legal", "insurer", "precedent"]
License = Literal[
    "us_gov_public_domain",
    "cc_by_4",
    "cc_by_nc_4",
    "insurer_public_terms",
    "journalism_fair_use_summary",
]
TrustTier = Literal[
    "gov_regulatory",
    "state_doi_iro",
    "peer_reviewed",
    "specialty_society",
    "journalism",
    "insurer_public",
]
FetchFormat = Literal["html", "pdf", "markdown"]


class SeedCatalogEntry(BaseModel):
    """One redistributable source to ingest into GCS + Vertex."""

    id: str = Field(description="Stable slug, e.g. legal-ecfr-45-cfr-147-136")
    title: str
    source_url: str
    domain: Domain
    trust_tier: TrustTier
    license: License
    fetch_format: FetchFormat = "html"
    insurers: list[str] = Field(default_factory=list)
    denial_types: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    source_org: str = ""
    priority: int = Field(
        default=2, ge=1, le=3, description="1=must-have for benchmark, 3=optional depth"
    )
    notes: str = ""

    @field_validator("source_url")
    @classmethod
    def _url_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source_url required")
        return v.strip()

    def corpus_doc_id(self) -> str:
        ext = ".pdf" if self.fetch_format == "pdf" else ".md"
        return f"{self.domain}/{self.id}{ext}"


class SeedCatalog(BaseModel):
    version: str = "1.0.0"
    updated: str = ""
    description: str = ""
    entries: list[SeedCatalogEntry]


def load_seed_catalog(path: Path | None = None) -> SeedCatalog:
    p = path or DEFAULT_CATALOG_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    return SeedCatalog.model_validate(data)
