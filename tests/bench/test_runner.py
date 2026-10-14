from __future__ import annotations

from pycontextfold.bench.adapters.base import AdapterError, BaseAdapter
from pycontextfold.bench.adapters.baseline import BaselineAdapter
from pycontextfold.bench.adapters.registry import AdapterRegistry
from pycontextfold.bench.capabilities import Capability, of
from pycontextfold.bench.dataset import synthetic_dataset
from pycontextfold.bench.models import (
    ExperimentConfig,
    OptimizationResult,
)
from pycontextfold.bench.runner import Runner, run_experiment
from pycontextfold.bench.runs import STATUS_FAILED


def _config(adapters=("baseline",), metrics=(), **options) -> ExperimentConfig:
    return ExperimentConfig(
        name="exp",
        dataset="synthetic",
        adapters=adapters,
        metrics=metrics,
        options=options,
    )


def test_run_produces_one_adapter_run_per_adapter():
    ds = synthetic_dataset()
    run = run_experiment(ds, _config(adapters=("baseline", "contextfold")))
    assert {a.adapter for a in run.adapters} == {"baseline", "contextfold"}
    assert run.adapter("baseline").succeeded == len(ds)


def test_unregistered_adapter_is_unavailable_not_fatal():
    ds = synthetic_dataset()
    run = run_experiment(ds, _config(adapters=("does-not-exist",)))
    adapter = run.adapter("does-not-exist")
    assert adapter.available is False
    assert adapter.error
    assert adapter.documents == ()


def test_unavailable_adapter_aggregate_metrics_are_unavailable():
    ds = synthetic_dataset()
    run = run_experiment(ds, _config(adapters=("does-not-exist",), metrics=("size_reduction",)))
    aggregate = run.adapter("does-not-exist").aggregate
    assert not aggregate["size_reduction"].available


def test_adapter_error_is_isolated_per_document():
    class Flaky(BaseAdapter):
        name = "flaky"
        capabilities = of(Capability.OPTIMIZE_TEXT)

        def optimize(self, request):
            raise AdapterError("boom")

    reg = AdapterRegistry([Flaky(), BaselineAdapter()])
    ds = synthetic_dataset()
    run = run_experiment(ds, _config(adapters=("flaky", "baseline")), registry=reg)
    assert run.adapter("flaky").failed == len(ds)
    assert run.adapter("baseline").succeeded == len(ds)


def test_unexpected_exception_is_isolated():
    class Exploding(BaseAdapter):
        name = "exploding"
        capabilities = of(Capability.OPTIMIZE_TEXT)

        def optimize(self, request):
            raise RuntimeError("kaboom")

    reg = AdapterRegistry([Exploding()])
    run = run_experiment(synthetic_dataset(), _config(adapters=("exploding",)), registry=reg)
    doc = run.adapter("exploding").documents[0]
    assert doc.status == STATUS_FAILED
    assert "kaboom" in doc.error


def test_default_metrics_are_the_core_five():
    run = run_experiment(synthetic_dataset(), _config())
    doc = run.adapter("baseline").documents[0]
    names = {m.name for m in doc.metrics}
    assert names == {
        "size_reduction",
        "char_reduction",
        "token_reduction",
        "preservation_recall",
        "drop_precision",
    }


def test_non_core_requested_metric_is_unavailable():
    run = run_experiment(
        synthetic_dataset(), _config(metrics=("size_reduction", "exact_tokens"))
    )
    aggregate = run.adapter("baseline").aggregate
    assert aggregate["size_reduction"].available
    assert not aggregate["exact_tokens"].available


def test_config_hash_and_dataset_hash_are_stable():
    ds = synthetic_dataset()
    a = run_experiment(ds, _config())
    b = run_experiment(ds, _config())
    assert a.config_hash == b.config_hash
    assert a.dataset_hash == b.dataset_hash
    assert a.to_dict() == b.to_dict()


def test_method_option_is_passed():
    class Recorder(BaseAdapter):
        name = "recorder"
        capabilities = of(Capability.OPTIMIZE_TEXT)

        def optimize(self, request):
            return OptimizationResult(
                document_id=request.document.id,
                output=request.method,
                method=request.method,
            )

    reg = AdapterRegistry([Recorder()])
    run = run_experiment(
        synthetic_dataset(), _config(adapters=("recorder",), method="interface-only"), registry=reg
    )
    assert run.adapter("recorder").documents[0].method == "interface-only"


def test_per_adapter_options_are_merged():
    seen = {}

    class Recorder(BaseAdapter):
        name = "recorder"
        capabilities = of(Capability.OPTIMIZE_TEXT)

        def optimize(self, request):
            seen.update(request.options)
            return OptimizationResult(document_id=request.document.id, output="x")

    reg = AdapterRegistry([Recorder()])
    cfg = ExperimentConfig(
        name="exp",
        dataset="synthetic",
        adapters=("recorder",),
        options={"budget_bytes": 100, "per_adapter": {"recorder": {"budget_bytes": 50}}},
    )
    run_experiment(synthetic_dataset(), cfg, registry=reg)
    assert seen["budget_bytes"] == 50


def test_seeded_limit_selects_deterministically():
    ds = synthetic_dataset()
    cfg = _config(limit=2)
    run_a = run_experiment(ds, cfg)
    run_b = run_experiment(ds, cfg)
    ids_a = [d.document_id for d in run_a.adapter("baseline").documents]
    ids_b = [d.document_id for d in run_b.adapter("baseline").documents]
    assert len(ids_a) == 2
    assert ids_a == ids_b


def test_limit_zero_yields_no_documents():
    run = run_experiment(synthetic_dataset(), _config(limit=0))
    assert run.adapter("baseline").documents == ()


def test_runner_uses_injected_measurer():
    calls = {"n": 0}

    from pycontextfold.bench.tokens import CallableTokenMeasurer

    def counter(text):
        calls["n"] += 1
        return len(text)

    measurer = CallableTokenMeasurer(counter)
    Runner(measurer=measurer).run(synthetic_dataset(), _config())
    assert calls["n"] > 0
