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

    return AdapterRegistry([BaselineAdapter(), ContextFoldAdapter()])


_default: AdapterRegistry | None = None


def default_registry() -> AdapterRegistry:
    """The process-wide registry with the required built-in adapters.

    Built-ins are the neutral baseline and the PyContextFold core adapter. Optional
    ecosystem adapters register themselves lazily (Phase 4).
    """
    global _default
    if _default is None:
        _default = _build_default_registry()
    return _default


__all__ = ["AdapterRegistry", "default_registry"]
