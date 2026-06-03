"""Download, normalize, and stage library seed documents (no GCP unless upload=True)."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import ssl
import urllib.error
import urllib.request
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from app.library.models import SeedCatalog, SeedCatalogEntry, load_seed_catalog

_LOG = logging.getLogger(__name__)

USER_AGENT = "AegisLibraryIngest/1.0 (+https://github.com/aegis; research corpus; contact=local)"
MAX_BYTES = 12 * 1024 * 1024  # 12 MiB per document


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = False
        if tag in ("p", "br", "div", "li", "h1", "h2", "h3", "h4", "tr"):
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._chunks.append(data)

    def text(self) -> str:
        raw = "".join(self._chunks)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def html_to_markdown(title: str, html: bytes) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(html.decode("utf-8", errors="replace"))
    except Exception:
        parser.feed(html.decode("latin-1", errors="replace"))
    body = parser.text()
    return f"# {title}\n\n{body}\n"


def fetch_url(url: str, timeout: int = 60) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        data = resp.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError(f"response too large (> {MAX_BYTES} bytes): {url}")
        ctype = resp.headers.get("Content-Type", "")
        return data, ctype


def stage_entry(
    entry: SeedCatalogEntry,
    staging_root: Path,
    *,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    """Download one catalog entry into staging_root. Returns manifest row."""
    retrieved = retrieved_at or datetime.now(UTC).date().isoformat()
    dest_dir = staging_root / entry.domain
    dest_dir.mkdir(parents=True, exist_ok=True)

    if entry.fetch_format == "pdf":
        dest = dest_dir / f"{entry.id}.pdf"
        body_bytes, _ = fetch_url(entry.source_url)
        dest.write_bytes(body_bytes)
        content_preview = ""
        sha = hashlib.sha256(body_bytes).hexdigest()
    else:
        dest = dest_dir / f"{entry.id}.md"
        body_bytes, ctype = fetch_url(entry.source_url)
        if entry.fetch_format == "markdown" or "text/plain" in ctype:
            text = body_bytes.decode("utf-8", errors="replace")
            md = f"# {entry.title}\n\n{text}\n" if not text.startswith("#") else text
        elif "pdf" in ctype or entry.source_url.lower().endswith(".pdf"):
            dest_pdf = dest_dir / f"{entry.id}.pdf"
            dest_pdf.write_bytes(body_bytes)
            dest = dest_pdf
            md = ""
        else:
            md = html_to_markdown(entry.title, body_bytes)
        if dest.suffix == ".md":
            dest.write_text(md, encoding="utf-8")
        content_preview = md[:500] if md else "(binary pdf)"
        sha = hashlib.sha256(dest.read_bytes()).hexdigest()

    rel_path = str(dest.relative_to(staging_root))
    return {
        "id": entry.id,
        "corpus_doc_id": entry.corpus_doc_id(),
        "title": entry.title,
        "domain": entry.domain,
        "trust_tier": entry.trust_tier,
        "license": entry.license,
        "source_url": entry.source_url,
        "source_org": entry.source_org,
        "retrieved_at": retrieved,
        "ingest_mode": "seed",
        "insurers": entry.insurers,
        "denial_types": entry.denial_types,
        "topics": entry.topics,
        "priority": entry.priority,
        "staging_path": rel_path,
        "sha256": sha,
        "content_preview": content_preview,
    }


def run_ingest(
    catalog: SeedCatalog,
    staging_root: Path,
    *,
    max_entries: int | None = None,
    priority_max: int = 3,
    skip_existing: bool = True,
) -> dict[str, Any]:
    """Ingest catalog entries into staging_root; return report dict."""
    staging_root.mkdir(parents=True, exist_ok=True)
    manifest_path = staging_root / "manifest" / "provenance.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    entries = sorted(
        [e for e in catalog.entries if e.priority <= priority_max],
        key=lambda e: (e.priority, e.domain, e.id),
    )
    if max_entries is not None:
        entries = entries[:max_entries]

    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for entry in entries:
        out_file = staging_root / entry.domain / (
            f"{entry.id}.pdf" if entry.fetch_format == "pdf" else f"{entry.id}.md"
        )
        if skip_existing and out_file.exists():
            rows.append(
                {
                    "id": entry.id,
                    "corpus_doc_id": entry.corpus_doc_id(),
                    "skipped": True,
                    "staging_path": str(out_file.relative_to(staging_root)),
                }
            )
            continue
        try:
            row = stage_entry(entry, staging_root)
            rows.append(row)
            _LOG.info("staged %s", entry.id)
        except (urllib.error.URLError, ValueError, OSError) as exc:
            _LOG.warning("failed %s: %s", entry.id, exc)
            errors.append({"id": entry.id, "error": str(exc), "url": entry.source_url})

    provenance = {
        "_note": "Generated by ingest_library_seed.py — ADR-008",
        "catalog_version": catalog.version,
        "ingested_at": datetime.now(UTC).isoformat(),
        "documents": [r for r in rows if not r.get("skipped")],
        "errors": errors,
    }
    manifest_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")

    return {
        "staged": len([r for r in rows if not r.get("skipped")]),
        "skipped": len([r for r in rows if r.get("skipped")]),
        "errors": len(errors),
        "staging_root": str(staging_root),
        "manifest": str(manifest_path),
    }


def upload_to_gcs(staging_root: Path, bucket: str, prefix: str = "library/v1") -> int:
    """Upload staged tree via gsutil (requires gcloud creds). Returns file count."""
    import subprocess

    src = str(staging_root).rstrip("/") + "/*"
    dest = f"gs://{bucket}/{prefix}/"
    subprocess.run(
        ["gsutil", "-m", "cp", "-r", src, dest],
        check=True,
    )
    return sum(1 for _ in staging_root.rglob("*") if _.is_file())


def validate_catalog(catalog: SeedCatalog | None = None) -> list[str]:
    """Return list of validation errors (empty = ok)."""
    from app.library.models import DEFAULT_CATALOG_PATH

    cat = catalog or load_seed_catalog()
    vocab = json.loads((DEFAULT_CATALOG_PATH.parent / "controlled_vocab.json").read_text())
    allowed_license = set(vocab["licenses_allowed"])
    allowed_domain = set(vocab["domains"])
    errors: list[str] = []
    seen_ids: set[str] = set()
    for e in cat.entries:
        if e.id in seen_ids:
            errors.append(f"duplicate id: {e.id}")
        seen_ids.add(e.id)
        if e.license not in allowed_license:
            errors.append(f"{e.id}: license {e.license} not allowed")
        if e.domain not in allowed_domain:
            errors.append(f"{e.id}: domain {e.domain} invalid")
        for ins in e.insurers:
            if ins not in vocab["insurers"]:
                errors.append(f"{e.id}: unknown insurer {ins}")
    return errors


def clear_staging(staging_root: Path) -> None:
    if staging_root.exists():
        shutil.rmtree(staging_root)
