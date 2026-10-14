from __future__ import annotations

from pathlib import Path

import pytest

from pycontextfold.bench.models import MetricResult
from pycontextfold.bench.runs import (
    RUN_SCHEMA_VERSION,
    STATUS_FAILED,
    STATUS_OK,
    AdapterRun,
    DocumentRun,
    RunResult,
    canonical_hash,
    read_run,
    write_run,
)


def test_canonical_hash_is_order_independent():
    assert canonical_hash({"a": 1, "b": 2}) == canonical_hash({"b": 2, "a": 1})
    assert canonical_hash({"a": 1}) != canonical_hash({"a": 2})


def test_document_run_rejects_bad_status():
    with pytest.raises(ValueError):
        DocumentRun(document_id="d", adapter="a", status="nonsense")


def test_document_run_metric_lookup():
    run = DocumentRun(
        document_id="d",
        adapter="a",
        metrics=(MetricResult(name="size_reduction", value=0.5, unit="ratio"),),
    )
    assert run.metric("size_reduction").value == 0.5
    assert run.metric("missing") is None


def test_document_run_round_trip():
    run = DocumentRun(
        document_id="d",
        adapter="a",
        method="safe",
        metrics=(MetricResult(name="x", value=1.0, unit="ratio"),),
        output_bytes=3,
        lossy=False,
        metadata={"k": 1},
    )
    assert DocumentRun.from_dict(run.to_dict()) == run


def test_adapter_run_counts_and_round_trip():
    docs = (
        DocumentRun(document_id="a", adapter="x", status=STATUS_OK),
        DocumentRun(document_id="b", adapter="x", status=STATUS_FAILED, error="e"),
    )
    run = AdapterRun(
        adapter="x",
        documents=docs,
        aggregate={"size_reduction": MetricResult(name="size_reduction", value=0.1, unit="ratio")},
    )
    assert run.succeeded == 1
    assert run.failed == 1
    assert AdapterRun.from_dict(run.to_dict()) == run


def _sample_run() -> RunResult:
    doc = DocumentRun(document_id="a", adapter="baseline", status=STATUS_OK)
    adapter = AdapterRun(adapter="baseline", documents=(doc,))
    return RunResult(
        experiment={"name": "exp"},
        dataset="synthetic",
        dataset_hash="abc",
        config_hash="def",
        adapters=(adapter,),
        seed=3,
    )


def test_run_result_adapter_lookup():
    run = _sample_run()
    assert run.adapter("baseline") is not None
    assert run.adapter("nope") is None
    assert run.schema_version == RUN_SCHEMA_VERSION


def test_run_result_round_trip():
    run = _sample_run()
    assert RunResult.from_dict(run.to_dict()) == run
    assert RunResult.from_json(run.to_json()) == run


def test_write_and_read_run(tmp_path: Path):
    run = _sample_run()
    target = tmp_path / "run.json"
    write_run(run, target)
    assert read_run(target).to_dict() == run.to_dict()
