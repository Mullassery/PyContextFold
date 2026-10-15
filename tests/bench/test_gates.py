from __future__ import annotations

import pytest

from pycontextfold.bench.gates import (
    GateReport,
    Threshold,
    evaluate_gates,
    thresholds_from_config,
)
from pycontextfold.bench.models import ExperimentConfig, MetricResult
from pycontextfold.bench.runs import AdapterRun, RunResult


def _run() -> RunResult:
    adapter = AdapterRun(
        adapter="contextfold",
        aggregate={
            "size_reduction": MetricResult(name="size_reduction", value=0.2, unit="ratio"),
            "preservation_recall": MetricResult(name="preservation_recall", value=0.9, unit="ratio"),
            "exact_tokens": MetricResult.unavailable("exact_tokens", "no tokenizer"),
        },
    )
    return RunResult(
        experiment={"name": "x"},
        dataset="synthetic",
        dataset_hash="h",
        config_hash="c",
        adapters=(adapter,),
    )


def test_threshold_requires_a_bound():
    with pytest.raises(ValueError):
        Threshold(metric="m")
    with pytest.raises(ValueError):
        Threshold(metric="m", minimum=0.5, maximum=0.1)


def test_threshold_check_bounds():
    assert Threshold(metric="m", minimum=0.1).check(0.2)[0] is True
    assert Threshold(metric="m", minimum=0.3).check(0.2)[0] is False
    assert Threshold(metric="m", maximum=0.1).check(0.2)[0] is False
    assert Threshold(metric="m", minimum=0.1).check(None)[0] is False


def test_evaluate_gates_pass():
    report = evaluate_gates(
        _run(),
        [Threshold(metric="size_reduction", minimum=0.1)],
    )
    assert report.passed
    assert report.outcomes[0].value == pytest.approx(0.2)


def test_evaluate_gates_fail_on_minimum():
    report = evaluate_gates(_run(), [Threshold(metric="size_reduction", minimum=0.5)])
    assert not report.passed
    assert len(report.failures()) == 1
    assert "minimum" in report.failures()[0].reason


def test_evaluate_gates_unavailable_fails():
    report = evaluate_gates(_run(), [Threshold(metric="exact_tokens", minimum=0.0)])
    assert not report.passed
    assert report.outcomes[0].reason == "metric unavailable"


def test_evaluate_gates_adapter_scope_unknown_adapter():
    report = evaluate_gates(
        _run(), [Threshold(metric="size_reduction", adapter="ghost", minimum=0.0)]
    )
    assert not report.passed
    assert "no adapter matched" in report.outcomes[0].reason


def test_evaluate_gates_adapter_scope_ok():
    report = evaluate_gates(
        _run(),
        [Threshold(metric="size_reduction", adapter="contextfold", minimum=0.1)],
    )
    assert report.passed


def test_thresholds_from_config():
    cfg = ExperimentConfig(
        name="n",
        dataset="synthetic",
        adapters=("contextfold",),
        options={"gates": [{"metric": "size_reduction", "minimum": 0.1}]},
    )
    thresholds = thresholds_from_config(cfg)
    assert thresholds == (Threshold(metric="size_reduction", minimum=0.1),)


def test_thresholds_from_config_empty():
    cfg = ExperimentConfig(name="n", dataset="synthetic", adapters=("contextfold",))
    assert thresholds_from_config(cfg) == ()


def test_gate_report_to_dict():
    report = evaluate_gates(_run(), [Threshold(metric="size_reduction", minimum=0.1)])
    payload = report.to_dict()
    assert payload["passed"] is True
    assert payload["outcomes"][0]["metric"] == "size_reduction"


def test_empty_gate_report_passes():
    assert GateReport().passed is True
