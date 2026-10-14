"""Optional adapters and the registry that tracks them."""

from __future__ import annotations

from .base import AdapterError, BaseAdapter
from .baseline import BaselineAdapter
from .contextfold import ContextFoldAdapter
from .registry import AdapterRegistry, default_registry

__all__ = [
    "AdapterError",
    "AdapterRegistry",
    "BaseAdapter",
    "BaselineAdapter",
    "ContextFoldAdapter",
    "default_registry",
]
