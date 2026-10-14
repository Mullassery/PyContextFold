from __future__ import annotations

from pathlib import Path

from pycontextfold.bench.dataset import (
    SYNTHETIC_DATASET_NAME,
    dataset_from_dict,
    dataset_from_json,
    dataset_to_json,
    load_dataset,
    synthetic_dataset,
    write_dataset,
)


def test_synthetic_dataset_is_deterministic():
    a = synthetic_dataset()
    b = synthetic_dataset()
    assert a.to_dict() == b.to_dict()
    assert a.name == SYNTHETIC_DATASET_NAME
    assert len(a) == 4


def test_synthetic_dataset_has_expected_ids():
    ds = synthetic_dataset()
    assert {d.id for d in ds} == {"py-basic", "md-basic", "log-basic", "json-basic"}
    assert ds.ground_truth_for("py-basic") is not None


def test_synthetic_ground_truth_targets_exist():
    ds = synthetic_dataset()
    py = ds.ground_truth_for("py-basic")
    assert "def add(a, b):" in py.must_preserve


def test_dataset_json_round_trip():
    ds = synthetic_dataset()
    restored = dataset_from_json(dataset_to_json(ds))
    assert restored.to_dict() == ds.to_dict()


def test_dataset_from_dict_round_trip():
    ds = synthetic_dataset()
    assert dataset_from_dict(ds.to_dict()).to_dict() == ds.to_dict()


def test_write_and_load_dataset(tmp_path: Path):
    ds = synthetic_dataset(name="custom")
    target = tmp_path / "ds.json"
    write_dataset(ds, target)
    loaded = load_dataset(target)
    assert loaded.name == "custom"
    assert loaded.to_dict() == ds.to_dict()
