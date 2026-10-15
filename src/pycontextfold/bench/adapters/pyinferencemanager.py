"""Adapter for PyInferenceManager — optional quality scoring via inference.

This is *optional*: the offline benchmark never requires it. When present, it can
score the fidelity of an optimized output by asking a model to compare it against
the original.

Contract (must hold for the installed PyInferenceManager):

- an ``Orchestrator`` class; an instance's ``run(prompt, **kwargs)`` returns a
  result exposing ``.output``/``.text`` or a string.
"""

from __future__ import annotations

from typing import Any

from ..capabilities import Capability, of
from .base import AdapterError, BaseAdapter, module_version


def _result_text(result: Any) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        for key in ("output", "text", "content"):
            value = result.get(key)
            if isinstance(value, str):
                return value
    for attr in ("output", "text", "content"):
        value = getattr(result, attr, None)
        if isinstance(value, str):
            return value
    raise AdapterError("PyInferenceManager result exposes no text/output")


class PyInferenceManagerAdapter(BaseAdapter):
    name = "pyinferencemanager"
    requires = ("pyinferencemanager",)
    capabilities = of(Capability.QUALITY_SCORING)

    def resolve_version(self) -> str:
        return module_version(self.requires[0])

    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Run ``prompt`` through the orchestrator and return the text output."""
        module = self.load()
        cls = getattr(module, "Orchestrator", None)
        if cls is None:
            raise AdapterError("pyinferencemanager does not expose Orchestrator")
        orchestrator = kwargs.pop("orchestrator", None) or cls()
        result = orchestrator.run(prompt, **kwargs)
        return _result_text(result)

    def score(self, prompt: str, **kwargs: Any) -> float:
        """Score a prompt response as a float (expects a numeric reply)."""
        text = self.complete(prompt, **kwargs).strip()
        try:
            return float(text)
        except ValueError as exc:
            raise AdapterError(
                f"PyInferenceManager score reply was not numeric: {text!r}"
            ) from exc


__all__ = ["PyInferenceManagerAdapter"]
