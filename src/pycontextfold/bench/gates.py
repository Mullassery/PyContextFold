"""Quality gates for experiment runs.

A gate asserts a bound on an aggregated metric for one adapter (or every
adapter). Gates turn a benchmark into a regression check: an experiment that
drops below a threshold fails, which is useful in CI.

Gates are honest by construction: a metric that is *unavailable* fails the gate
with an explanatory reason — it is never treated as a silent pass.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .models import ExperimentConfig
from .runs import RunResult


@dataclass(frozen=True)
class Threshold:
    """A bound on one aggregated metric, optionally scoped to one adapter."""

    metric: str
    adapter: str | None = None
    minimum: float | None = None
    maximum: float | None = None

    def __post_init__(self) -> None:
        if not self.metric:
            raise ValueError("Threshold.metric must be non-empty")
        if self.minimum is None and self.maximum is None:
            raise ValueError("Threshold requires at least one of minimum/maximum")
        if (
            self.minimum is not None
            and self.maximum is not None
            and self.minimum > self.maximum
        ):
            raise ValueError("Threshold.minimum must be <= maximum")

    def check(self, value: float | None) -> tuple[bool, str]:
        if value is None:
            return False, "metric unavailable"
        if self.minimum is not None and value < self.minimum:
            return False, f"{value:.4g} < minimum {self.minimum:.4g}"
        if self.maximum is not None and value > self.maximum:
            return False, f"{value:.4g} > maximum {self.maximum:.4g}"
        return True, "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "adapter": self.adapter,
            "minimum": self.minimum,
            "maximum": self.maximum,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Threshold:
        return cls(
            metric=str(data["metric"]),
            adapter=data.get("adapter"),
            minimum=None if data.get("minimum") is None else float(data["minimum"]),
            maximum=None if data.get("maximum") is None else float(data["maximum"]),
        )


@dataclass(frozen=True)
class GateOutcome:
    adapter: str
    metric: str
    value: float | None
    minimum: float | None
    maximum: float | None
    passed: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "metric": self.metric,
            "value": self.value,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "passed": self.passed,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class GateReport:
    outcomes: tuple[GateOutcome, ...] = ()

    @property
    def passed(self) -> bool:
        return all(o.passed for o in self.outcomes)

    def failures(self) -> tuple[GateOutcome, ...]:
        return tuple(o for o in self.outcomes if not o.passed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "outcomes": [o.to_dict() for o in self.outcomes],
        }


def evaluate_gates(
    run: RunResult, thresholds: Iterable[Threshold]
) -> GateReport:
    """Evaluate ``thresholds`` against a run and return a :class:`GateReport`."""
    outcomes: list[GateOutcome] = []
    for threshold in thresholds:
        targets = [
            adapter for adapter in run.adapters
            if threshold.adapter is None or adapter.adapter == threshold.adapter
        ]
        if not targets:
            outcomes.append(
                GateOutcome(
                    adapter=threshold.adapter or "<any>",
                    metric=threshold.metric,
                    value=None,
                    minimum=threshold.minimum,
                    maximum=threshold.maximum,
                    passed=False,
                    reason=f"no adapter matched {threshold.adapter!r}",
                )
            )
            continue
        for adapter in targets:
            metric = adapter.aggregate.get(threshold.metric)
            value = metric.value if metric is not None and metric.available else None
            passed, reason = threshold.check(value)
            outcomes.append(
                GateOutcome(
                    adapter=adapter.adapter,
                    metric=threshold.metric,
                    value=value,
                    minimum=threshold.minimum,
                    maximum=threshold.maximum,
                    passed=passed,
                    reason=reason,
                )
            )
    return GateReport(outcomes=tuple(outcomes))


def thresholds_from_config(config: ExperimentConfig) -> tuple[Threshold, ...]:
    """Read gate thresholds from ``config.options['gates']``."""
    raw = config.options.get("gates", []) if config.options else []
    if not isinstance(raw, (list, tuple)):
        return ()
    return tuple(Threshold.from_dict(item) for item in raw)


__all__ = [
    "GateOutcome",
    "GateReport",
    "Threshold",
    "evaluate_gates",
    "thresholds_from_config",
]
