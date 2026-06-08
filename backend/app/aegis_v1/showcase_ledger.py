"""Durable storage for showcase session JSON (local dir or GCS prefix)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol


def default_ledger_dir() -> Path:
    return Path(os.environ.get("AEGIS_SHOWCASE_LEDGER_DIR", "/tmp/aegis_showcase_sessions"))


def parse_gcs_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError(f"not a GCS URI: {uri!r}")
    rest = uri[5:]
    bucket, _, prefix = rest.partition("/")
    if not bucket:
        raise ValueError(f"GCS URI missing bucket: {uri!r}")
    return bucket, prefix.strip("/")


class LedgerStore(Protocol):
    def ensure_ready(self) -> None: ...

    def exists(self, key: str) -> bool: ...

    def read_text(self, key: str) -> str: ...

    def write_text(self, key: str, content: str) -> None: ...

    def list_keys(self, prefix: str = "") -> list[str]: ...


class LocalLedgerStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def ensure_ready(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / key

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def read_text(self, key: str) -> str:
        return self._path(key).read_text(encoding="utf-8")

    def write_text(self, key: str, content: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def list_keys(self, prefix: str = "") -> list[str]:
        if not self.root.is_dir():
            return []
        out: list[str] = []
        for path in self.root.glob(f"{prefix}*"):
            if path.is_file():
                out.append(path.name)
        return sorted(out)


class GcsLedgerStore:
    """Persist showcase ledger objects under ``gs://bucket/prefix/``."""

    def __init__(self, bucket: str, prefix: str = "") -> None:
        self.bucket_name = bucket
        self.prefix = prefix.strip("/")

    def _object_name(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def _client(self):
        from google.cloud import storage

        return storage.Client()

    def ensure_ready(self) -> None:
        return None

    def exists(self, key: str) -> bool:
        blob = self._client().bucket(self.bucket_name).blob(self._object_name(key))
        return blob.exists()

    def read_text(self, key: str) -> str:
        blob = self._client().bucket(self.bucket_name).blob(self._object_name(key))
        return blob.download_as_text(encoding="utf-8")

    def write_text(self, key: str, content: str) -> None:
        blob = self._client().bucket(self.bucket_name).blob(self._object_name(key))
        blob.upload_from_string(content, content_type="application/json")

    def list_keys(self, prefix: str = "") -> list[str]:
        bucket = self._client().bucket(self.bucket_name)
        blob_prefix = self._object_name(prefix) if prefix else (f"{self.prefix}/" if self.prefix else "")
        names: list[str] = []
        for blob in bucket.list_blobs(prefix=blob_prefix):
            name = blob.name
            if self.prefix and name.startswith(self.prefix + "/"):
                name = name[len(self.prefix) + 1 :]
            elif self.prefix and name == self.prefix:
                continue
            if name:
                names.append(name)
        return sorted(names)


def open_ledger_store(*, ledger_dir: Path | None = None) -> LedgerStore:
    gcs_uri = os.environ.get("AEGIS_SHOWCASE_LEDGER_GCS_URI", "").strip()
    if gcs_uri:
        bucket, prefix = parse_gcs_uri(gcs_uri)
        return GcsLedgerStore(bucket, prefix)
    return LocalLedgerStore(ledger_dir or default_ledger_dir())
