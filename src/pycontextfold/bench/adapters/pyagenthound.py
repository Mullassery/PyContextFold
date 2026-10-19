"""Adapter for PyAgentHound — agent-task evaluation and tracing.

Tracing, root-cause analysis and task evaluation belong to PyAgentHound. This
adapter forwards to its evaluation entry point and exposes its tracing SDK for
producing traces; it implements neither.

Contract (must hold for the installed PyAgentHound):

- ``evaluate(...)`` at the top level or as ``pyagenthound.evaluation.evaluate``,
  returning a result whose numeric fields can be harvested as metrics.
- optionally a top-level ``AgentHound`` class for producing traces.
"""

from __future__ import annotations

from typing import Any

from ..capabilities import Capability, of
from .base import AdapterError, BaseAdapter, module_version


class PyAgentHoundAdapter(BaseAdapter):
    name = "pyagenthound"
    requires = ("pyagenthound",)
    capabilities = of(
        Capability.AGENT_TRACING,
        Capability.AGENT_METRICS,
    )

    def resolve_version(self) -> str:
        return module_version(self.requires[0])

    def _evaluate(self):
        module = self.load()
        fn = getattr(module, "evaluate", None)
        if callable(fn):
            return fn
        fn = getattr(module, "evaluate_with_inspect", None)
        if callable(fn):
            return fn
        evaluation = getattr(module, "evaluation", None)
        fn = getattr(evaluation, "evaluate", None)
        if callable(fn):
            return fn
        raise AdapterError("pyagenthound does not expose evaluate()")

    def agent_metrics(self, cases: Any, **kwargs: Any) -> dict[str, float]:
        """Evaluate agent test cases and return numeric metrics."""
        result = self._evaluate()(cases, **kwargs)
        if isinstance(result, dict):
            return {
                str(k): float(v)
                for k, v in result.items()
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            }
        metrics: dict[str, float] = {}
        for name in ("passed", "failed", "pass_rate", "total", "score"):
            value = getattr(result, name, None)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                metrics[name] = float(value)
        if not metrics:
            raise AdapterError("pyagenthound evaluate() returned no numeric metrics")
        return metrics

    def tracer(self, **kwargs: Any) -> Any:
        """Return a PyAgentHound tracing client (``AgentHound``)."""
        module = self.load()
        cls = getattr(module, "AgentHound", None)
        if cls is None:
            raise AdapterError("pyagenthound does not expose AgentHound")
        return cls(**kwargs)


__all__ = ["PyAgentHoundAdapter"]
