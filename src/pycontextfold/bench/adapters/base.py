"""Adapter protocol and base class.

An adapter is a thin, optional bridge to one component of the ecosystem (or to a
neutral baseline). Implementations live in this subpackage and are registered in
:mod:`pycontextfold.bench.adapters.registry`. Adapters never take hard
dependencies on sibling projects: they detect availability and fail with an
:class:`AdapterError` when a capability is requested but unavailable.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from abc import ABC
from types import ModuleType
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

    def resolve_version(self) -> str:
        """Return the adapter version. Overridden to read a package version."""
        return self.version

    def load(self) -> ModuleType:
        """Import and return the adapter's primary optional module.

        Raises :class:`AdapterError` when it is not installed.
        """
        if not self.requires:
            raise AdapterError(f"{self.name!r} declares no required module")
        module = load_optional(self.requires[0])
        if module is None:
            raise AdapterError(
                f"{self.name!r} is unavailable: optional dependency "
                f"{self.requires[0]!r} is not installed"
            )
        return module

    def info(self) -> AdapterInfo:
        available = self.is_available()
        return AdapterInfo(
            name=self.name,
            version=self.resolve_version(),
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
    # A module already imported (or injected, e.g. in tests) counts as available
    # without re-resolving it on disk.
    if module_name in sys.modules and sys.modules[module_name] is not None:
        return True
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def load_optional(module_name: str) -> ModuleType | None:
    """Import an optional dependency, or return ``None`` if it is missing."""
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


def require(module: ModuleType, attr: str, adapter: BaseAdapter) -> Any:
    """Return ``module.attr`` or raise a descriptive :class:`AdapterError`."""
    obj = getattr(module, attr, None)
    if obj is None:
        raise AdapterError(
            f"{adapter.name!r} requires {module.__name__}.{attr}; "
            "the installed version does not expose it"
        )
    return obj


def module_version(module_name: str, default: str = "0") -> str:
    """Best-effort ``__version__`` lookup that avoids importing when possible."""
    module = sys.modules.get(module_name)
    if module is None:
        module = load_optional(module_name)
    if module is None:
        return default
    return str(getattr(module, "__version__", default))


__all__ = [
    "AdapterError",
    "BaseAdapter",
    "load_optional",
    "module_version",
    "require",
]
