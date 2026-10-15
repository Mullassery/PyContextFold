"""Adapter for PyTokenCalc — provider tokenization and cost estimation.

PyContextFold deliberately ships no model vocabulary; this adapter lets a
benchmark measure *exact* tokens and cost by delegating to PyTokenCalc. The
dependency is optional and imported lazily.

Contract (must hold for the installed PyTokenCalc):

- ``count_tokens(text, model=...) -> int`` — exact token count.
- ``estimate_cost(tokens, model=...) -> float | None`` — optional; when absent,
  cost is reported unavailable.
"""

from __future__ import annotations

from typing import Any

from ..capabilities import Capability, of
from ..tokens import TokenMeasurer
from .base import BaseAdapter, module_version, require


class _PyTokenCalcMeasurer:
    """A :class:`TokenMeasurer` backed by PyTokenCalc (exact)."""

    exact = True

    def __init__(self, count_fn, model: str | None) -> None:
        self._count_fn = count_fn
        self._model = model
        self.name = "pytokencalc" + (f":{model}" if model else "")

    def count(self, text: str) -> int:
        if self._model is None:
            return int(self._count_fn(text))
        return int(self._count_fn(text, model=self._model))


class PyTokenCalcAdapter(BaseAdapter):
    name = "pytokencalc"
    requires = ("pytokencalc",)
    capabilities = of(Capability.COUNT_TOKENS_EXACT, Capability.ESTIMATE_COST)

    def resolve_version(self) -> str:
        return module_version(self.requires[0])

    def measurer(self, model: str | None = None) -> TokenMeasurer:
        """Return an exact, PyTokenCalc-backed token measurer."""
        module = self.load()
        count_fn = require(module, "count_tokens", self)
        return _PyTokenCalcMeasurer(count_fn, model)

    def count_tokens(self, text: str, model: str | None = None) -> int:
        return self.measurer(model).count(text)

    def estimate_cost(self, tokens: int, model: str | None = None, **kwargs: Any) -> float:
        """Estimate cost for ``tokens`` under ``model``.

        Raises :class:`AdapterError` (via :func:`require`) when the installed
        PyTokenCalc does not expose ``estimate_cost``.
        """
        module = self.load()
        estimate = require(module, "estimate_cost", self)
        if model is None:
            value = estimate(tokens)
        else:
            try:
                value = estimate(tokens, model=model, **kwargs)
            except TypeError:
                value = estimate(tokens, model, **kwargs)
        return float(value)

    def available_models(self) -> tuple[str, ...]:
        """Model names known to PyTokenCalc, when distinguishable."""
        module = self.load()
        table = getattr(module, "PRICING_TABLE", None)
        if isinstance(table, dict):
            return tuple(sorted(str(k) for k in table))
        return ()


__all__ = ["PyTokenCalcAdapter"]
