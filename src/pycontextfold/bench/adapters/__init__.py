"""Optional adapters and the registry that tracks them.

Two classes of adapter live here:

- **Core** (``baseline``, ``contextfold``) — dependency-free, always available.
- **Ecosystem** (``pytokencalc``, ``pystreampdf``, ...) — optional bridges to
  sibling projects. They are registered but self-report ``available=False`` when
  their dependency is absent, and import it lazily only when used.
"""

from __future__ import annotations

from .base import AdapterError, BaseAdapter, load_optional, require
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
from .registry import AdapterRegistry, core_registry, default_registry


def token_measurer(registry: AdapterRegistry | None = None, model: str | None = None):
    """Return an exact measurer from PyTokenCalc if available, else the default.

    This is the intended bridge: benchmarks stay exact when PyTokenCalc is
    installed and degrade to a clearly-labelled approximation when it is not.
    """
    from ..tokens import DEFAULT_MEASURER

    reg = registry if registry is not None else default_registry()
    if "pytokencalc" not in reg:
        return DEFAULT_MEASURER
    adapter = reg.get("pytokencalc")
    if not adapter.is_available():
        return DEFAULT_MEASURER
    return adapter.measurer(model)

__all__ = [
    "AdapterError",
    "AdapterRegistry",
    "BaseAdapter",
    "BaselineAdapter",
    "ContextFoldAdapter",
    "OpenAnchorAdapter",
    "PyAPICheckAdapter",
    "PyAgentHoundAdapter",
    "PyInferenceManagerAdapter",
    "PyStreamAIAdapter",
    "PyStreamMCPAdapter",
    "PyStreamPDFAdapter",
    "PyTokenCalcAdapter",
    "PyVectorHoundAdapter",
    "core_registry",
    "default_registry",
    "load_optional",
    "require",
    "token_measurer",
]
