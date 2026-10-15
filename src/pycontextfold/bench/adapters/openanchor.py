"""Adapter for OpenAnchor — token/cost attribution.

Attribution and middleware belong to OpenAnchor. This adapter exposes its token
collector and analytics so a benchmark can attribute optimized-vs-original usage;
it re-implements neither.

Contract (must hold for the installed OpenAnchor):

- a ``TokenCollector`` class, and
- an ``Analytics`` class (optionally with ``AttributionModel``).
"""

from __future__ import annotations

from typing import Any

from ..capabilities import Capability, of
from .base import AdapterError, BaseAdapter, module_version


class OpenAnchorAdapter(BaseAdapter):
    name = "openanchor"
    requires = ("openanchor",)
    capabilities = of(Capability.COST_ATTRIBUTION)

    def resolve_version(self) -> str:
        return module_version(self.requires[0])

    def token_collector(self, **kwargs: Any) -> Any:
        """Return an OpenAnchor ``TokenCollector`` instance."""
        module = self.load()
        cls = getattr(module, "TokenCollector", None)
        if cls is None:
            raise AdapterError("openanchor does not expose TokenCollector")
        return cls(**kwargs)

    def analytics(self, **kwargs: Any) -> Any:
        """Return an OpenAnchor ``Analytics`` instance."""
        module = self.load()
        cls = getattr(module, "Analytics", None)
        if cls is None:
            raise AdapterError("openanchor does not expose Analytics")
        return cls(**kwargs)


__all__ = ["OpenAnchorAdapter"]
