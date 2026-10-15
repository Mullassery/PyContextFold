from __future__ import annotations

import json
from pathlib import Path

from pycontextfold.bench.cli import main
from pycontextfold.bench.config import config_to_json
from pycontextfold.bench.models import ExperimentConfig


def _write_config(tmp_path: Path, **options) -> Path:
    cfg = ExperimentConfig(
        name="cli-exp",
        dataset="synthetic",
        adapters=("baseline", "contextfold"),
        metrics=("size_reduction", "preservation_recall"),
        options=options,
    )
    path = tmp_path / "exp.json"
    path.write_text(config_to_json(cfg), encoding="utf-8")
    return path


def test_cli_run_writes_artifacts(tmp_path, capsys):
    config = _write_config(tmp_path, method="safe")
    out = tmp_path / "run.json"
    report = tmp_path / "report.html"
    code = main(
        ["run", "--config", str(config), "--out", str(out), "--report", str(report)]
    )
    assert code == 0
    assert out.exists()
    assert report.exists()
    captured = capsys.readouterr().out
    assert "experiment 'cli-exp'" in captured


def test_cli_run_gates_pass(tmp_path, capsys):
    config = _write_config(
        tmp_path, gates=[{"metric": "preservation_recall", "minimum": 0.5}]
    )
    code = main(["run", "--config", str(config), "--gate"])
    assert code == 0
    assert "gates passed" in capsys.readouterr().out


def test_cli_run_gates_fail(tmp_path, capsys):
    config = _write_config(
        tmp_path, gates=[{"metric": "size_reduction", "minimum": 0.9}]
    )
    code = main(["run", "--config", str(config), "--gate"])
    assert code == 1
    assert "gates failed" in capsys.readouterr().out


def test_cli_report_subcommand(tmp_path):
    config = _write_config(tmp_path)
    run_path = tmp_path / "run.json"
    main(["run", "--config", str(config), "--out", str(run_path)])
    report = tmp_path / "r.html"
    code = main(["report", str(run_path), "--out", str(report), "--title", "T"])
    assert code == 0
    assert "<title>T</title>" in report.read_text(encoding="utf-8")


def test_cli_gates_subcommand(tmp_path, capsys):
    config = _write_config(
        tmp_path, gates=[{"metric": "size_reduction", "minimum": 0.0}]
    )
    run_path = tmp_path / "run.json"
    main(["run", "--config", str(config), "--out", str(run_path)])
    code = main(["gates", str(run_path), "--config", str(config)])
    assert code == 0
    assert "gates passed" in capsys.readouterr().out


def test_cli_adapters(capsys):
    code = main(["adapters"])
    assert code == 0
    out = capsys.readouterr().out
    assert "baseline" in out
    assert "pytokencalc" in out


def test_cli_datasets_write(tmp_path):
    out = tmp_path / "ds.json"
    code = main(["datasets", "--out", str(out)])
    assert code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["name"] == "synthetic"


def test_cli_datasets_print(capsys):
    assert main(["datasets"]) == 0
    assert "synthetic" in capsys.readouterr().out


def test_cli_missing_config_returns_usage_error(tmp_path, capsys):
    code = main(["run", "--config", str(tmp_path / "nope.json")])
    assert code == 2
    assert "error:" in capsys.readouterr().out


def test_cli_unknown_dataset_returns_usage_error(tmp_path, capsys):
    config = _write_config(tmp_path)
    code = main(["run", "--config", str(config), "--dataset", "/no/such/file.json"])
    assert code == 2
