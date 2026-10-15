"""Adapter registry with capability-based lookup."""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from ..capabilities import Capability
from ..models import AdapterInfo
from .base import BaseAdapter


class AdapterRegistry:
    """A mutable registry of named adapters."""

    def __init__(self, adapters: Iterable[BaseAdapter] = ()) -> None:
        self._adapters: dict[str, BaseAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: BaseAdapter, *, replace: bool = False) -> None:
        name = adapter.name
        if not name or name == "unnamed":
            raise ValueError("adapter must set a non-empty name")
        if name in self._adapters and not replace:
            raise ValueError(f"adapter {name!r} is already registered")
        self._adapters[name] = adapter

    def unregister(self, name: str) -> None:
        self._adapters.pop(name, None)

    def __contains__(self, name: object) -> bool:
        return name in self._adapters

    def __len__(self) -> int:
        return len(self._adapters)

    def __iter__(self) -> Iterator[BaseAdapter]:
        return iter(self._adapters[name] for name in self.names())

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))

    def get(self, name: str) -> BaseAdapter:
        try:
            return self._adapters[name]
        except KeyError:
            raise KeyError(
                f"unknown adapter {name!r}; registered: {list(self.names())}"
            ) from None

    def find(self, capability: Capability) -> tuple[str, ...]:
        """Return the names of adapters advertising ``capability``."""
        return tuple(
            name
            for name in self.names()
            if capability in self._adapters[name].capabilities
        )

    def infos(self) -> tuple[AdapterInfo, ...]:
        return tuple(self._adapters[name].info() for name in self.names())


def _build_default_registry() -> AdapterRegistry:
    from .baseline import BaselineAdapter
    from .contextfold import ContextFoldAdapter
    from .openanchor import OpenAnchorAdapter
    from .pyagenthound import PyAgentHoundAdapter
    from .pyapicheck import PyAPICheckAdapter
    from .pyinferencemanager import PyInferenceManagerAdapter
    from .pystreamai import PyStreamAIAdapter
    from .pystreammcp import PyStreamMCPAdapter
    from .pystreampdf import PyStreamPDFAdapter
    from .pytokencalc import PyTokenCalcAdapter
    from .pyvectorhound import PyVectorHoundAdapter

    return AdapterRegistry(
        [
            BaselineAdapter(),
            ContextFoldAdapter(),
            PyTokenCalcAdapter(),
            PyAPICheckAdapter(),
            PyStreamPDFAdapter(),
            PyVectorHoundAdapter(),
            PyAgentHoundAdapter(),
            PyInferenceManagerAdapter(),
            PyStreamAIAdapter(),
            PyStreamMCPAdapter(),
            OpenAnchorAdapter(),
        ]
    )


def _build_core_registry() -> AdapterRegistry:
    """Only the dependency-free adapters (baseline + core)."""
    from .baseline import BaselineAdapter
    from .contextfold import ContextFoldAdapter

    return AdapterRegistry([BaselineAdapter(), ContextFoldAdapter()])


_default: AdapterRegistry | None = None


def default_registry() -> AdapterRegistry:
    """The process-wide registry with all built-in and ecosystem adapters.

    Ecosystem adapters are always registered but self-report ``available=False``
    when their optional dependency is missing, so listing the registry never
    requires any sibling package to be installed.
    """
    global _default
    if _default is None:
        _default = _build_default_registry()
    return _default


def core_registry() -> AdapterRegistry:
    """A fresh registry containing only the dependency-free adapters."""
    return _build_core_registry()


__all__ = ["AdapterRegistry", "core_registry", "default_registry"]
