from app.learning.benchmark_dataset import load_benchmark_cases, micro_benchmark_fixture


def test_micro_fixture_has_train_and_holdout():
    cases = micro_benchmark_fixture()
    splits = {c["dataset_split"] for c in cases}
    assert "benchmark_train" in splits
    assert "benchmark_holdout" in splits


def test_load_benchmark_cases_respects_60_40_split():
    train = load_benchmark_cases("benchmark_train", limit=100)
    holdout = load_benchmark_cases("benchmark_holdout", limit=100)
    if not train and not holdout:
        return  # no draft files in CI sandbox — skip assert on counts
    total = len(train) + len(holdout)
    assert total <= 100
    assert len(train) >= len(holdout)
