from __future__ import annotations

from app.aegis_v1.phoenix_mode import PhoenixMode, can_write_phoenix


def test_can_write_phoenix_allows_appeal_and_training() -> None:
    assert can_write_phoenix(PhoenixMode.APPEAL)
    assert can_write_phoenix(PhoenixMode.TRAINING_WRITE)
    assert can_write_phoenix(PhoenixMode.TRAINING_READWRITE)


def test_can_write_phoenix_blocks_holdout() -> None:
    assert not can_write_phoenix(PhoenixMode.HOLDOUT_READONLY)
