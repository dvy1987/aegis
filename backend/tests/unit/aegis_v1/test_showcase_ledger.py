from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.aegis_v1.showcase_ledger import (
    GcsLedgerStore,
    LocalLedgerStore,
    MirroredLedgerStore,
    open_ledger_store,
    parse_gcs_uri,
)
from app.aegis_v1.showcase_session import ShowcaseSessionManager


def test_parse_gcs_uri() -> None:
    assert parse_gcs_uri("gs://my-bucket/aegis/showcase") == ("my-bucket", "aegis/showcase")
    assert parse_gcs_uri("gs://only-bucket") == ("only-bucket", "")


def test_local_ledger_round_trip(tmp_path: Path) -> None:
    store = LocalLedgerStore(tmp_path)
    store.ensure_ready()
    store.write_text("quick_1.json", '{"status": "queued"}')
    assert store.exists("quick_1.json")
    assert store.read_text("quick_1.json") == '{"status": "queued"}'
    assert "quick_1.json" in store.list_keys("quick_")


def test_open_ledger_store_prefers_gcs_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AEGIS_SHOWCASE_LEDGER_GCS_URI", "gs://demo-bucket/showcase")
    monkeypatch.delenv("AEGIS_SHOWCASE_LEDGER_DIR", raising=False)
    store = open_ledger_store(ledger_dir=tmp_path)
    assert isinstance(store, GcsLedgerStore)
    assert store.bucket_name == "demo-bucket"
    assert store.prefix == "showcase"


def test_gcs_ledger_round_trip_with_fake_client(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeBlob:
        def __init__(self) -> None:
            self._data: str | None = None

        def exists(self) -> bool:
            return self._data is not None

        def upload_from_string(self, data: str, content_type: str | None = None) -> None:
            self._data = data

        def download_as_text(self, encoding: str = "utf-8") -> str:
            if self._data is None:
                raise FileNotFoundError("missing")
            return self._data

    class FakeBucket:
        def __init__(self) -> None:
            self.blobs: dict[str, FakeBlob] = {}

        def blob(self, name: str) -> FakeBlob:
            return self.blobs.setdefault(name, FakeBlob())

        def list_blobs(self, prefix: str = ""):
            for name in sorted(self.blobs):
                if not prefix or name.startswith(prefix):
                    yield type("Obj", (), {"name": name})()

    fake_bucket = FakeBucket()

    class FakeClient:
        def bucket(self, name: str) -> FakeBucket:
            assert name == "ledger-bucket"
            return fake_bucket

    monkeypatch.setattr("google.cloud.storage.Client", lambda: FakeClient())
    store = GcsLedgerStore("ledger-bucket", "sessions")
    store.write_text("quick_abc.json", '{"session_id": "quick_abc"}')
    assert store.exists("quick_abc.json")
    assert json.loads(store.read_text("quick_abc.json"))["session_id"] == "quick_abc"
    assert "quick_abc.json" in store.list_keys("quick_")


def test_session_manager_survives_store_reload(tmp_path: Path) -> None:
    manager = ShowcaseSessionManager(ledger_dir=tmp_path)
    session = manager.start_quick(case_ids=["case_1"])
    reloaded = ShowcaseSessionManager(ledger_dir=tmp_path).get(session.session_id)
    assert reloaded.session_id == session.session_id


def test_mirrored_ledger_writes_primary_and_mirror(tmp_path: Path) -> None:
    primary = LocalLedgerStore(tmp_path / "primary")
    mirror = LocalLedgerStore(tmp_path / "mirror")
    store = MirroredLedgerStore(primary, mirror)
    store.write_text("quick_1.json", '{"ok": true}')
    assert primary.read_text("quick_1.json") == '{"ok": true}'
    assert mirror.read_text("quick_1.json") == '{"ok": true}'


def test_promotion_stack_shares_ledger_with_sessions(tmp_path: Path) -> None:
    from app.aegis_v1.showcase_rollback import PromotionStack
    from app.learning.models import Candidate, Component

    store = LocalLedgerStore(tmp_path)
    manager = ShowcaseSessionManager(store=store)
    session = manager.start_quick(case_ids=["case_1"])
    stack = PromotionStack(store=store)
    candidate = Candidate(
        candidate_id="c1",
        components={
            "drafter_system_prompt": Component(
                component_id="drafter_system_prompt",
                kind="prompt",
                version="v2",
                text="prompt",
            )
        },
        origin="reflect",
    )
    stack.push_checkpoint(run_type="quick", session_id=session.session_id, candidate=candidate)
    assert store.exists("promotion_stack.json")
    assert store.exists(f"{session.session_id}.json")
