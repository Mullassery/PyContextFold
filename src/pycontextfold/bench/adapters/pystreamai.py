"""Adapter for PyStreamAI — optional model routing / quality scoring.

Optional. Routing, ONNX and deployment belong to PyStreamAI; this adapter only
asks it to produce a model output or a numeric score.

Contract (must hold for the installed PyStreamAI):

- a callable ``complete(prompt, **kwargs)`` or ``generate(prompt, **kwargs)``
  returning text; or ``score(prompt, **kwargs)`` returning a number.
"""

from __future__ import annotations

from typing import Any

from ..capabilities import Capability, of
from .base import AdapterError, BaseAdapter, module_version


class PyStreamAIAdapter(BaseAdapter):
    name = "pystreamai"
    requires = ("pystreamai",)
    capabilities = of(Capability.QUALITY_SCORING)

    def resolve_version(self) -> str:
        return module_version(self.requires[0])

    def complete(self, prompt: str, **kwargs: Any) -> str:
        module = self.load()
        for attr in ("complete", "generate"):
            fn = getattr(module, attr, None)
            if callable(fn):
                result = fn(prompt, **kwargs)
                if isinstance(result, str):
                    return result
                for field in ("output", "text", "content"):
                    value = getattr(result, field, None)
                    if isinstance(value, str):
                        return value
                raise AdapterError("pystreamai returned no text output")
        raise AdapterError("pystreamai does not expose complete/generate")

    def score(self, prompt: str, **kwargs: Any) -> float:
        module = self.load()
        fn = getattr(module, "score", None)
        if callable(fn):
            return float(fn(prompt, **kwargs))
        return float(self.complete(prompt, **kwargs).strip())


__all__ = ["PyStreamAIAdapter"]
