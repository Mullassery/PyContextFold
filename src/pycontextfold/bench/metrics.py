"""Core, dependency-free metrics.

Every metric is honest about availability: when it cannot be computed (no ground
truth, empty input, missing measurer) it returns an *unavailable*
:class:`~pycontextfold.bench.models.MetricResult` with a reason, rather than a
misleading zero.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from .models import Document, GroundTruth, MetricResult, OptimizationResult
from .tokens import DEFAULT_MEASURER, TokenMeasurer, count_tokens

SIZE_REDUCTION = "size_reduction"
CHAR_REDUCTION = "char_reduction"
TOKEN_REDUCTION = "token_reduction"
PRESERVATION_RECALL = "preservation_recall"
DROP_PRECISION = "drop_precision"

#: Metrics the runner can always compute from a document + result pair.
CORE_METRICS: tuple[str, ...] = (
    SIZE_REDUCTION,
    CHAR_REDUCTION,
    TOKEN_REDUCTION,
    PRESERVATION_RECALL,
    DROP_PRECISION,
)


def _ratio(original: int, reduced: int) -> float:
    if original <= 0:
        return 0.0
    return (original - reduced) / original


def size_reduction(document: Document, result: OptimizationResult) -> MetricResult:
    reduced = len(result.output.encode("utf-8"))
    return MetricResult(
        name=SIZE_REDUCTION,
        value=_ratio(document.byte_size, reduced),
        unit="ratio",
    )


def char_reduction(document: Document, result: OptimizationResult) -> MetricResult:
    return MetricResult(
        name=CHAR_REDUCTION,
        value=_ratio(document.char_size, len(result.output)),
        unit="ratio",
    )


def token_reduction(
    document: Document,
    result: OptimizationResult,
    measurer: TokenMeasurer = DEFAULT_MEASURER,
) -> MetricResult:
    original = count_tokens(measurer, document.text)
    reduced = count_tokens(measurer, result.output)
    return MetricResult(
        name=TOKEN_REDUCTION,
        value=_ratio(original, reduced),
        unit="ratio",
        detail=f"measurer={measurer.name} exact={measurer.exact}",
    )


def preservation_recall(
    result: OptimizationResult, ground_truth: GroundTruth | None
) -> MetricResult:
    if ground_truth is None or not ground_truth.must_preserve:
        return MetricResult.unavailable(
            PRESERVATION_RECALL,
            "no ground-truth preservation targets for this document",
        )
    kept = sum(1 for needle in ground_truth.must_preserve if needle in result.output)
    return MetricResult(
        name=PRESERVATION_RECALL,
        value=kept / len(ground_truth.must_preserve),
        unit="ratio",
        detail=f"{kept}/{len(ground_truth.must_preserve)} preserved",
    )


def drop_precision(
    result: OptimizationResult, ground_truth: GroundTruth | None
) -> MetricResult:
    if ground_truth is None or not ground_truth.must_drop:
        return MetricResult.unavailable(
            DROP_PRECISION,
            "no ground-truth drop targets for this document",
        )
    dropped = sum(1 for needle in ground_truth.must_drop if needle not in result.output)
    return MetricResult(
        name=DROP_PRECISION,
        value=dropped / len(ground_truth.must_drop),
        unit="ratio",
        detail=f"{dropped}/{len(ground_truth.must_drop)} dropped",
    )


def document_metrics(
    document: Document,
    result: OptimizationResult,
    ground_truth: GroundTruth | None = None,
    measurer: TokenMeasurer = DEFAULT_MEASURER,
) -> tuple[MetricResult, ...]:
    """Compute the five core metrics for a single document."""
    return (
        size_reduction(document, result),
        char_reduction(document, result),
        token_reduction(document, result, measurer),
        preservation_recall(result, ground_truth),
        drop_precision(result, ground_truth),
    )


def aggregate_metrics(
    results: Iterable[MetricResult],
) -> dict[str, MetricResult]:
    """Average available metric values by name; keep unavailability.

    Aggregates over *available* observations only. If no observation of a metric
    was available, the aggregate is unavailable too.
    """
    buckets: dict[str, list[float]] = {}
    unavailable: dict[str, str] = {}
    order: list[str] = []
    for result in results:
        if result.name not in order:
            order.append(result.name)
        if result.available and result.value is not None:
            buckets.setdefault(result.name, []).append(result.value)
        elif result.name not in buckets:
            unavailable.setdefault(result.name, result.detail)

    aggregate: dict[str, MetricResult] = {}
    for name in order:
        values = buckets.get(name)
        if values:
            aggregate[name] = MetricResult(
                name=name,
                value=sum(values) / len(values),
                unit="ratio",
                detail=f"mean over {len(values)} document(s)",
            )
        else:
            aggregate[name] = MetricResult.unavailable(
                name, unavailable.get(name, "no observations")
            )
    return aggregate


def metric_values(results: Sequence[MetricResult]) -> Mapping[str, float | None]:
    """Flatten metric results to a name -> value mapping (None when unavailable)."""
    return {r.name: (r.value if r.available else None) for r in results}


__all__ = [
    "CHAR_REDUCTION",
    "CORE_METRICS",
    "DROP_PRECISION",
    "PRESERVATION_RECALL",
    "SIZE_REDUCTION",
    "TOKEN_REDUCTION",
    "aggregate_metrics",
    "char_reduction",
    "document_metrics",
    "drop_precision",
    "metric_values",
    "preservation_recall",
    "size_reduction",
    "token_reduction",
]
