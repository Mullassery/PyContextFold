"""Adapter for PyAPICheck — public API-surface inventory.

PyAPICheck enumerates the public API of a source tree. The benchmark uses that
inventory as *ground truth*: names that must survive folding.

Contract (must hold for the installed PyAPICheck):

- ``discover_directory(path) -> inventory`` or ``discover(path)``; the returned
  inventory is an iterable of items, each a mapping (or object) that exposes a
  name via ``name`` or ``qualified_name``.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..capabilities import Capability, of
from ..models import GroundTruth
from .base import AdapterError, BaseAdapter, module_version


def _extract_name(item: Any) -> str | None:
    if isinstance(item, dict):
        for key in ("qualified_name", "name", "id", "path"):
            value = item.get(key)
            if isinstance(value, str) and value:
                return value
        return None
    for attr in ("qualified_name", "name"):
        value = getattr(item, attr, None)
        if isinstance(value, str) and value:
            return value
    return None


class PyAPICheckAdapter(BaseAdapter):
    name = "pyapicheck"
    requires = ("pyapicheck",)
    capabilities = of(Capability.API_INVENTORY)

    def resolve_version(self) -> str:
        return module_version(self.requires[0])

    def inventory(self, path: str) -> tuple[str, ...]:
        """Return the sorted, de-duplicated public API names under ``path``."""
        module = self.load()
        discover = getattr(module, "discover_directory", None) or getattr(
            module, "discover", None
        )
        if discover is None:
            raise AdapterError(
                "pyapicheck does not expose discover_directory/discover"
            )
        items: Iterable[Any] = discover(path)
        names = {name for item in items if (name := _extract_name(item))}
        return tuple(sorted(names))

    def ground_truth(self, document_id: str, path: str) -> GroundTruth:
        """Build a :class:`GroundTruth` preserving every discovered API name."""
        return GroundTruth(
            document_id=document_id,
            must_preserve=self.inventory(path),
            labels={"source": "pyapicheck"},
        )


__all__ = ["PyAPICheckAdapter"]
