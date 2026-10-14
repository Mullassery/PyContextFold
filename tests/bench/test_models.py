from __future__ import annotations

import pytest

from pycontextfold.bench.capabilities import Capability
from pycontextfold.bench.models import (
    DATASET_SCHEMA_VERSION,
    Dataset,
    Document,
    ExperimentConfig,
    GroundTruth,
    MetricResult,
    OptimizationResult,
    required_capabilities_for,
)


def test_document_sizes():
    doc = Document(id="d", text="a\nb\nc\n")
    assert doc.byte_size == 6
    assert doc.char_size == 6
    assert doc.line_count == 3  # trailing newline does not add a line


def test_document_line_count_without_trailing_newline():
    doc = Document(id="d", text="a\nb")
    assert doc.line_count == 2


def test_document_requires_id():
    with pytest.raises(ValueError):
        Document(id="", text="x")


def test_document_round_trip():
    doc = Document(id="d", text="x", path="a.py", language="python", metadata={"k": 1})
    assert Document.from_dict(doc.to_dict()) == doc


def test_ground_truth_validates_reduction():
    with pytest.raises(ValueError):
        GroundTruth(document_id="d", max_reduction=1.5)


def test_ground_truth_round_trip():
    gt = GroundTruth(document_id="d", must_preserve=("a",), must_drop=("b",))
    assert GroundTruth.from_dict(gt.to_dict()) == gt


def test_dataset_rejects_duplicate_ids():
    docs = (Document(id="a", text="1"), Document(id="a", text="2"))
    with pytest.raises(ValueError):
        Dataset(name="x", documents=docs)


def test_dataset_lookup_and_round_trip():
    gt = GroundTruth(document_id="a", must_preserve=("1",))
    ds = Dataset(name="x", documents=(Document(id="a", text="1"),), ground_truth={"a": gt})
    assert ds.get("a").text == "1"
    assert ds.ground_truth_for("a") is gt
    assert ds.ground_truth_for("missing") is None
    assert len(ds) == 1
    assert ds.total_bytes == 1
    assert Dataset.from_dict(ds.to_dict()) == ds
    assert ds.schema_version == DATASET_SCHEMA_VERSION


def test_dataset_get_missing_raises():
    ds = Dataset(name="x", documents=(Document(id="a", text="1"),))
    with pytest.raises(KeyError):
        ds.get("b")


def test_metric_result_unavailable():
    result = MetricResult.unavailable("recall", "no ground truth")
    assert not result.available
    assert result.value is None
    assert result.detail == "no ground truth"


def test_metric_result_available_requires_value():
    with pytest.raises(ValueError):
        MetricResult(name="x", value=None, available=True)


def test_optimization_result_requires_document_id():
    with pytest.raises(ValueError):
        OptimizationResult(document_id="", output="x")


def test_experiment_config_validation():
    with pytest.raises(ValueError):
        ExperimentConfig(name="", dataset="d", adapters=("a",))
    with pytest.raises(ValueError):
        ExperimentConfig(name="n", dataset="d", adapters=())
    with pytest.raises(ValueError):
        ExperimentConfig(name="n", dataset="d", adapters=("a",), seed=-1)


def test_experiment_config_round_trip():
    cfg = ExperimentConfig(name="n", dataset="d", adapters=("contextfold",), seed=3)
    assert ExperimentConfig.from_dict(cfg.to_dict()) == cfg


def test_required_capabilities_for_metrics():
    assert required_capabilities_for("exact_tokens") == (Capability.COUNT_TOKENS_EXACT,)
    assert required_capabilities_for("size_reduction") == ()
