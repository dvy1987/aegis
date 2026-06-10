from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.aegis_v1 import phoenix_retention as retention


class _FakeResponse:
    def __init__(self, *, status_code: int = 200, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self) -> dict:
        return self._payload


def test_prune_disabled_without_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PHOENIX_HOST", raising=False)
    monkeypatch.setenv("AEGIS_PHOENIX_PRUNE_ENABLED", "0")
    result = retention.prune_phoenix_spans_if_needed()
    assert result.checked is False
    assert result.reason == "disabled"


def test_prune_skips_when_under_span_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEGIS_PHOENIX_PRUNE_ENABLED", "1")
    with (
        patch.object(retention, "_phoenix_client", return_value=MagicMock()),
        patch.object(retention, "count_project_spans", return_value=12_000),
    ):
        result = retention.prune_phoenix_spans_if_needed(
            project_name="default",
            threshold=20_000,
        )
    assert result.reason == "under_threshold"
    assert result.pruned is False


def test_prune_deletes_oldest_unprotected_traces(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEGIS_PHOENIX_PRUNE_ENABLED", "1")
    retention.clear_protected_dataset_splits()
    fake_client = MagicMock()
    oldest = [{"trace_id": f"old-{i}", "id": f"old-{i}"} for i in range(3)]

    with (
        patch.object(retention, "_phoenix_client", return_value=fake_client),
        patch.object(retention, "count_project_spans", side_effect=[21_000, 16_000]),
        patch.object(retention, "_list_oldest_traces", return_value=oldest),
        patch.object(retention, "_trace_is_protected", return_value=False),
        patch.object(retention, "_delete_trace", return_value=True) as delete_mock,
    ):
        result = retention.prune_phoenix_spans_if_needed(
            project_name="default",
            threshold=20_000,
            batch=5_000,
            protect_newest=15_000,
            dry_run=False,
        )

    assert result.pruned is True
    assert result.deleted_traces == 3
    assert delete_mock.call_count == 3


def test_prune_skips_protected_showcase_splits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEGIS_PHOENIX_PRUNE_ENABLED", "1")
    retention.register_showcase_session_splits("sess1", "showcase_serious_train_sess1")
    fake_client = MagicMock()
    oldest = [{"trace_id": "protected-trace", "id": "protected-trace"}]

    with (
        patch.object(retention, "_phoenix_client", return_value=fake_client),
        patch.object(retention, "count_project_spans", return_value=25_000),
        patch.object(retention, "_list_oldest_traces", return_value=oldest),
        patch.object(retention, "_trace_is_protected", return_value=True),
        patch.object(retention, "_delete_trace", return_value=True) as delete_mock,
    ):
        result = retention.prune_phoenix_spans_if_needed(dry_run=False)

    retention.clear_protected_dataset_splits()
    assert result.reason == "only_protected_remaining"
    assert result.deleted_traces == 0
    delete_mock.assert_not_called()


def test_ensure_runs_until_under_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEGIS_PHOENIX_PRUNE_ENABLED", "1")
    with patch.object(
        retention,
        "prune_phoenix_spans_if_needed",
        side_effect=[
            retention.PruneResult(
                checked=True,
                pruned=True,
                reason="pruned",
                span_count_before=21_000,
                deleted_traces=50,
            ),
            retention.PruneResult(
                checked=True,
                pruned=False,
                reason="under_threshold",
                span_count_before=19_000,
            ),
        ],
    ) as prune_mock:
        retention.ensure_phoenix_span_budget(project_name="default")
    assert prune_mock.call_count == 2


def test_count_project_spans_early_exit() -> None:
    http = MagicMock()
    http.get.side_effect = [
        _FakeResponse(
            payload={
                "data": [{"name": f"s{i}"} for i in range(100)],
                "next_cursor": "page-2",
            }
        ),
        _FakeResponse(payload={"data": [{"name": f"s{i}"} for i in range(100)]}),
    ]
    client = MagicMock()
    client._client = http

    total = retention.count_project_spans(
        client,
        project_identifier="default",
        early_exit_above=150,
    )
    assert total == 200


def test_register_showcase_session_splits() -> None:
    retention.register_showcase_session_splits("abc", "showcase_quick_train_abc")
    protected = retention.get_protected_dataset_splits()
    assert "showcase_quick_train_abc" in protected
    assert "showcase_pre_measure_abc" in protected
    retention.clear_protected_dataset_splits()
    assert retention.get_protected_dataset_splits() == set()
