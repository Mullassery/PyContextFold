"""Adapter for PyVectorHound — retrieval-quality metrics.

Retrieval evaluation (recall@k, nDCG, ...) belongs to PyVectorHound. This adapter
only forwards to it and normalises the result; it implements no retrieval or
embedding logic.

Contract (must hold for the installed PyVectorHound):

- a callable ``evaluate(...)`` (or ``evaluate_retrieval``) accepting keyword
  arguments and returning a mapping of ``metric_name -> number``.
"""

from __future__ import annotations

from typing import Any

from ..capabilities import Capability, of
from .base import AdapterError, BaseAdapter, module_version


class PyVectorHoundAdapter(BaseAdapter):
    name = "pyvectorhound"
    requires = ("pyvectorhound",)
    capabilities = of(Capability.RETRIEVAL_METRICS)

    def resolve_version(self) -> str:
        return module_version(self.requires[0])

    def _evaluate(self):
        module = self.load()
        for attr in ("evaluate", "evaluate_retrieval"):
            fn = getattr(module, attr, None)
            if callable(fn):
                return fn
        # Real pyvectorhound 1.8 exposes ranking.compute_reranker_metrics.
        ranking = getattr(module, "ranking", None)
        fn = getattr(ranking, "compute_reranker_metrics", None)
        if callable(fn):
            return fn
        raise AdapterError(
            "pyvectorhound does not expose evaluate/evaluate_retrieval"
        )

    def retrieval_metrics(self, **kwargs: Any) -> dict[str, float]:
        """Return retrieval metrics as ``{name: value}``."""
        result = self._evaluate()(**kwargs)
        if isinstance(result, dict):
            return {
                str(k): float(v)
                for k, v in result.items()
                if isinstance(v, (int, float))
            }
        # A result object: harvest numeric public attributes.
        metrics: dict[str, float] = {}
        for name in dir(result):
            if name.startswith("_"):
                continue
            value = getattr(result, name)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                metrics[name] = float(value)
        if not metrics:
            raise AdapterError(
                "pyvectorhound evaluate() returned no numeric metrics"
            )
        return metrics


__all__ = ["PyVectorHoundAdapter"]
