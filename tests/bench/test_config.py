from __future__ import annotations

import sys
from pathlib import Path

import pytest

from pycontextfold.bench.config import (
    ConfigError,
    config_from_dict,
    config_from_json,
    config_to_dict,
    config_to_json,
    load_config,
)
from pycontextfold.bench.models import ExperimentConfig


def _valid() -> dict:
    return {"name": "exp", "dataset": "synthetic", "adapters": ["contextfold"]}


def test_config_from_dict():
    cfg = config_from_dict(_valid())
    assert isinstance(cfg, ExperimentConfig)
    assert cfg.name == "exp"


def test_config_missing_required():
    with pytest.raises(ConfigError):
        config_from_dict({"name": "exp"})


def test_config_not_a_mapping():
    with pytest.raises(ConfigError):
        config_from_dict(["nope"])  # type: ignore[arg-type]


def test_config_invalid_values_wrapped():
    with pytest.raises(ConfigError):
        config_from_dict({"name": "exp", "dataset": "d", "adapters": []})


def test_config_json_round_trip():
    cfg = config_from_dict(_valid())
    restored = config_from_json(config_to_json(cfg))
    assert restored == cfg
    assert config_to_dict(cfg) == cfg.to_dict()


def test_config_invalid_json():
    with pytest.raises(ConfigError):
        config_from_json("{not json")


def test_load_config_json(tmp_path: Path):
    path = tmp_path / "exp.json"
    path.write_text(config_to_json(config_from_dict(_valid())), encoding="utf-8")
    assert load_config(path).name == "exp"


@pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib requires 3.11+")
def test_load_config_toml(tmp_path: Path):
    path = tmp_path / "exp.toml"
    path.write_text(
        'name = "exp"\ndataset = "synthetic"\nadapters = ["contextfold"]\nseed = 2\n',
        encoding="utf-8",
    )
    cfg = load_config(path)
    assert cfg.name == "exp"
    assert cfg.seed == 2


def test_load_config_sniff_json_without_suffix(tmp_path: Path):
    path = tmp_path / "exp.conf"
    path.write_text(config_to_json(config_from_dict(_valid())), encoding="utf-8")
    assert load_config(path).name == "exp"
