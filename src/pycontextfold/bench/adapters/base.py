"""Adapter protocol and base class.

An adapter is a thin, optional bridge to one component of the ecosystem (or to a
neutral baseline). Implementations live in this subpackage and are registered in
:mod:`pycontextfold.bench.adapters.registry`. Adapters never take hard
dependencies on sibling projects: they detect availability and fail with an
:class:`AdapterError` when a capability is requested but unavailable.
"""

from __future__ import annotations

import importlib.util
from abc import ABC
from typing import Any

from ..capabilities import EMPTY, CapabilitySet
from ..chunking import Chunk
from ..models import AdapterInfo, Document, OptimizationRequest, OptimizationResult


class AdapterError(RuntimeError):
    """Raised when an adapter cannot satisfy a requested operation."""


class BaseAdapter(ABC):
    """Base class for all adapters.

    Subclasses set :attr:`name`, optionally :attr:`version`, :attr:`requires`
    and :attr:`capabilities`, and override the operations they advertise.
    """

    name: str = "unnamed"
    version: str = "0"
    capabilities: CapabilitySet = EMPTY
    requires: tuple[str, ...] = ()

    def is_available(self) -> bool:
        """Whether every module in :attr:`requires` can be imported."""
        return all(_module_available(mod) for mod in self.requires)

    def availability_detail(self) -> str:
        missing = [m for m in self.requires if not _module_available(m)]
        if missing:
            return "missing optional dependency(ies): " + ", ".join(missing)
        return ""

    def info(self) -> AdapterInfo:
        available = self.is_available()
        return AdapterInfo(
            name=self.name,
            version=self.version,
            capabilities=self.capabilities,
            available=available,
            detail=self.availability_detail(),
            requires=self.requires,
        )

    def optimize(self, request: OptimizationRequest) -> OptimizationResult:
        raise AdapterError(f"{self.name!r} does not support optimize_text")

    def chunk(self, document: Document, **options: Any) -> tuple[Chunk, ...]:
        raise AdapterError(f"{self.name!r} does not support chunk_text")


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


__all__ = ["AdapterError", "BaseAdapter"]
