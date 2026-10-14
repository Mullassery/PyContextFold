from __future__ import annotations

import pytest

from pycontextfold.bench.metrics import (
    DROP_PRECISION,
    PRESERVATION_RECALL,
    SIZE_REDUCTION,
    TOKEN_REDUCTION,
    aggregate_metrics,
    char_reduction,
    document_metrics,
    drop_precision,
    metric_values,
    preservation_recall,
    size_reduction,
    token_reduction,
)
from pycontextfold.bench.models import (
    Document,
    GroundTruth,
    MetricResult,
    OptimizationResult,
)
from pycontextfold.bench.tokens import CallableTokenMeasurer


def _doc(text: str = "hello world") -> Document:
    return Document(id="d", text=text)


def _result(text: str) -> OptimizationResult:
    return OptimizationResult(document_id="d", output=text)


def test_size_reduction_half():
    doc = _doc("abcdefgh")  # 8 bytes
    assert size_reduction(doc, _result("abcd")).value == 0.5


def test_size_reduction_empty_input_is_zero():
    assert size_reduction(_doc(""), _result("")).value == 0.0


def test_char_reduction():
    assert char_reduction(_doc("abcd"), _result("ab")).value == 0.5


def test_token_reduction_uses_measurer_and_reports_exactness():
    measurer = CallableTokenMeasurer(lambda t: len(t), exact=False)
    result = token_reduction(_doc("abcd"), _result("ab"), measurer)
    assert result.value == 0.5
    assert "exact=False" in result.detail


def test_preservation_recall_all_kept():
    gt = GroundTruth(document_id="d", must_preserve=("a", "b"))
    result = preservation_recall(_result("xax bx"), gt)
    assert result.value == 1.0


def test_preservation_recall_partial():
    gt = GroundTruth(document_id="d", must_preserve=("a", "b"))
    assert preservation_recall(_result("a only"), gt).value == 0.5


def test_preservation_recall_unavailable_without_ground_truth():
    result = preservation_recall(_result("x"), None)
    assert not result.available
    assert result.name == PRESERVATION_RECALL


def test_drop_precision():
    gt = GroundTruth(document_id="d", must_drop=("secret", "gone"))
    assert drop_precision(_result("secret removed, gone too"), gt).value == 0.0
    assert drop_precision(_result("nothing here"), gt).value == 1.0


def test_drop_precision_unavailable_without_targets():
    assert not drop_precision(_result("x"), None).available


def test_document_metrics_returns_five():
    gt = GroundTruth(document_id="d", must_preserve=("a",), must_drop=("z",))
    results = document_metrics(_doc("abcd"), _result("ab"), gt)
    names = {r.name for r in results}
    assert names == {SIZE_REDUCTION, "char_reduction", TOKEN_REDUCTION,
                     PRESERVATION_RECALL, DROP_PRECISION}


def test_aggregate_means_available_values():
    results = [
        MetricResult(name="x", value=0.2, unit="ratio"),
        MetricResult(name="x", value=0.4, unit="ratio"),
        MetricResult.unavailable("x", "missing"),
    ]
    agg = aggregate_metrics(results)
    assert agg["x"].value == pytest.approx(0.3)
    assert agg["x"].available


def test_aggregate_all_unavailable_stays_unavailable():
    agg = aggregate_metrics([MetricResult.unavailable("y", "nope")])
    assert not agg["y"].available


def test_metric_values_flatten():
    results = [MetricResult(name="a", value=1.0, unit="ratio"), MetricResult.unavailable("b", "no")]
    assert metric_values(results) == {"a": 1.0, "b": None}
