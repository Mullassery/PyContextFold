"""The offline experiment runner.

Pairs a :class:`~pycontextfold.bench.models.Dataset` with a set of adapters from
a registry and produces a reproducible :class:`~pycontextfold.bench.runs.RunResult`.

Design rules:

- **Failure isolation.** An adapter that raises on one document is recorded as
  ``failed`` for that document; an adapter that is missing or unavailable is
  recorded as ``unavailable``. Neither aborts the run.
- **Determinism.** Documents are processed in dataset order (or a seeded sample).
  No timestamps are recorded; reproducibility is captured via content hashes.
- **Honesty.** Metrics that cannot be computed are stored as *unavailable* with a
  reason, never as a misleading zero.
"""

from __future__ import annotations

import random

from .adapters.base import AdapterError, BaseAdapter
from .adapters.registry import AdapterRegistry, default_registry
from .metrics import CORE_METRICS, aggregate_metrics, document_metrics
from .models import (
    Dataset,
    Document,
    ExperimentConfig,
    MetricResult,
    OptimizationRequest,
)
from .runs import (
    STATUS_FAILED,
    STATUS_OK,
    AdapterRun,
    DocumentRun,
    RunResult,
    canonical_hash,
)
from .tokens import DEFAULT_MEASURER, TokenMeasurer

_RESERVED_OPTION_KEYS = frozenset({"method", "limit", "per_adapter"})


class Runner:
    """Executes experiments against a registry of adapters."""

    def __init__(
        self,
        registry: AdapterRegistry | None = None,
        measurer: TokenMeasurer = DEFAULT_MEASURER,
    ) -> None:
        self.registry = registry if registry is not None else default_registry()
        self.measurer = measurer

    def run(
        self,
        dataset: Dataset,
        config: ExperimentConfig,
        *,
        adapter_names: tuple[str, ...] | None = None,
        method: str | None = None,
    ) -> RunResult:
        names = adapter_names if adapter_names is not None else config.adapters
        documents = _select_documents(dataset, config)
        adapter_runs = tuple(
            self._run_adapter(dataset, config, name, documents, method)
            for name in names
        )
        return RunResult(
            experiment=config.to_dict(),
            dataset=dataset.name,
            dataset_version=dataset.version,
            dataset_hash=canonical_hash(dataset.to_dict()),
            config_hash=canonical_hash(config.to_dict()),
            seed=config.seed,
            adapters=adapter_runs,
        )

    # -- internals --------------------------------------------------------- #

    def _run_adapter(
        self,
        dataset: Dataset,
        config: ExperimentConfig,
        name: str,
        documents: tuple[Document, ...],
        method: str | None,
    ) -> AdapterRun:
        selected = _selected_metrics(config.metrics)

        if name not in self.registry:
            return _unavailable_adapter(
                name, f"adapter {name!r} is not registered", selected
            )

        adapter = self.registry.get(name)
        if not adapter.is_available():
            return _unavailable_adapter(
                name, adapter.availability_detail(), selected, version=adapter.version
            )

        resolved_method = (
            method
            if method is not None
            else _per_adapter_method(config, name, adapter)
        )
        options = _adapter_options(config, name)

        document_runs = tuple(
            self._run_document(dataset, adapter, name, doc, resolved_method, options, selected)
            for doc in documents
        )

        observed: list[MetricResult] = []
        for run in document_runs:
            observed.extend(run.metrics)
        aggregate = aggregate_metrics(observed)

        return AdapterRun(
            adapter=name,
            version=adapter.version,
            available=True,
            documents=document_runs,
            aggregate=aggregate,
        )

    def _run_document(
        self,
        dataset: Dataset,
        adapter: BaseAdapter,
        name: str,
        document: Document,
        method: str,
        options: dict,
        selected: tuple[str, ...],
    ) -> DocumentRun:
        request = OptimizationRequest(document=document, method=method, options=options)
        try:
            result = adapter.optimize(request)
        except AdapterError as exc:
            return DocumentRun(
                document_id=document.id,
                adapter=name,
                method=method,
                status=STATUS_FAILED,
                error=str(exc),
            )
        except Exception as exc:  # noqa: BLE001 - isolation boundary
            return DocumentRun(
                document_id=document.id,
                adapter=name,
                method=method,
                status=STATUS_FAILED,
                error=f"{type(exc).__name__}: {exc}",
            )

        ground_truth = dataset.ground_truth_for(document.id)
        computed = {
            metric.name: metric
            for metric in document_metrics(
                document, result, ground_truth, self.measurer
            )
        }
        metrics = tuple(
            computed.get(
                metric_name,
                MetricResult.unavailable(
                    metric_name,
                    "requires an optional adapter or is not a core metric",
                ),
            )
            for metric_name in selected
        )
        return DocumentRun(
            document_id=document.id,
            adapter=name,
            method=method,
            status=STATUS_OK,
            metrics=metrics,
            output_bytes=len(result.output.encode("utf-8")),
            lossy=result.lossy,
            metadata=dict(result.metadata),
        )


def _selected_metrics(requested: tuple[str, ...]) -> tuple[str, ...]:
    if requested:
        seen: dict[str, None] = {}
        for metric in requested:
            seen[metric] = None
        return tuple(seen)
    return CORE_METRICS


def _adapter_options(config: ExperimentConfig, name: str) -> dict:
    options = {
        key: value
        for key, value in config.options.items()
        if key not in _RESERVED_OPTION_KEYS
    }
    per_adapter = config.options.get("per_adapter") or {}
    if isinstance(per_adapter, dict):
        override = per_adapter.get(name) or {}
        if isinstance(override, dict):
            options.update(
                {k: v for k, v in override.items() if k not in _RESERVED_OPTION_KEYS}
            )
    return options


def _per_adapter_method(
    config: ExperimentConfig, name: str, adapter: BaseAdapter
) -> str:
    per_adapter = config.options.get("per_adapter") or {}
    if isinstance(per_adapter, dict):
        override = per_adapter.get(name) or {}
        if isinstance(override, dict) and "method" in override:
            return str(override["method"])
    return str(config.options.get("method", "safe"))


def _select_documents(
    dataset: Dataset, config: ExperimentConfig
) -> tuple[Document, ...]:
    limit = config.options.get("limit")
    documents = dataset.documents
    if not isinstance(limit, int) or limit < 0 or limit >= len(documents):
        return documents
    if limit == 0:
        return ()
    rng = random.Random(config.seed)
    indices = sorted(rng.sample(range(len(documents)), limit))
    return tuple(documents[i] for i in indices)


def _unavailable_adapter(
    name: str,
    reason: str,
    selected: tuple[str, ...],
    version: str = "0",
) -> AdapterRun:
    aggregate = {
        metric: MetricResult.unavailable(metric, reason) for metric in selected
    }
    return AdapterRun(
        adapter=name,
        version=version,
        available=False,
        documents=(),
        aggregate=aggregate,
        error=reason,
    )


def run_experiment(
    dataset: Dataset,
    config: ExperimentConfig,
    *,
    registry: AdapterRegistry | None = None,
    measurer: TokenMeasurer = DEFAULT_MEASURER,
    adapter_names: tuple[str, ...] | None = None,
    method: str | None = None,
) -> RunResult:
    """Convenience wrapper around :meth:`Runner.run`."""
    return Runner(registry=registry, measurer=measurer).run(
        dataset, config, adapter_names=adapter_names, method=method
    )


__all__ = ["Runner", "run_experiment"]
