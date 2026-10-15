"""Adapter for PyStreamMCP — optional corpus/source discovery.

Source discovery belongs to PyStreamMCP. The benchmark can use it to populate a
dataset from real sources; it is never required, and no MCP logic is
re-implemented here.

Contract (must hold for the installed PyStreamMCP), one of:

- ``discovery.SourceRegistry`` with a ``discover(...)`` method, or
- a top-level ``discover(...)`` callable.

Discovered items are converted to :class:`Document`s when they expose text via a
string content field, ``.text`` or ``.content``.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..capabilities import Capability, of
from ..models import Document
from .base import AdapterError, BaseAdapter, module_version


def _item_to_document(index: int, item: Any) -> Document | None:
    if isinstance(item, str):
        return Document(id=f"mcp-{index}", text=item)
    if isinstance(item, dict):
        text = item.get("text") or item.get("content")
        if isinstance(text, str):
            return Document(
                id=str(item.get("id", f"mcp-{index}")),
                text=text,
                path=item.get("path"),
                metadata={"source": "pystreammcp"},
            )
        return None
    for attr in ("text", "content"):
        value = getattr(item, attr, None)
        if isinstance(value, str):
            return Document(
                id=str(getattr(item, "id", f"mcp-{index}")),
                text=value,
                metadata={"source": "pystreammcp"},
            )
    return None


class PyStreamMCPAdapter(BaseAdapter):
    name = "pystreammcp"
    requires = ("pystreammcp",)
    capabilities = of(Capability.SOURCE_DISCOVERY)

    def resolve_version(self) -> str:
        return module_version(self.requires[0])

    def _discover(self):
        module = self.load()
        discovery = getattr(module, "discovery", None)
        registry_cls = getattr(discovery, "SourceRegistry", None) if discovery else None
        if registry_cls is not None:
            registry = registry_cls()
            discover = getattr(registry, "discover", None)
            if callable(discover):
                return discover
        discover = getattr(module, "discover", None)
        if callable(discover):
            return discover
        raise AdapterError(
            "pystreammcp exposes neither discovery.SourceRegistry.discover nor discover"
        )

    def discover(self, *args: Any, **kwargs: Any) -> tuple[Document, ...]:
        """Discover sources and normalise them into documents."""
        items: Iterable[Any] = self._discover()(*args, **kwargs)
        documents: list[Document] = []
        for index, item in enumerate(items):
            document = _item_to_document(index, item)
            if document is not None:
                documents.append(document)
        return tuple(documents)


__all__ = ["PyStreamMCPAdapter"]
