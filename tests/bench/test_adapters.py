from __future__ import annotations

import pytest

from pycontextfold.bench.adapters import (
    AdapterError,
    AdapterRegistry,
    BaselineAdapter,
    ContextFoldAdapter,
    default_registry,
)
from pycontextfold.bench.adapters.base import BaseAdapter
from pycontextfold.bench.capabilities import Capability, of
from pycontextfold.bench.models import Document, OptimizationRequest


def test_baseline_is_identity():
    adapter = BaselineAdapter()
    doc = Document(id="d", text="hello  # comment\n")
    result = adapter.optimize(OptimizationRequest(doc))
    assert result.output == doc.text
    assert result.lossy is False


def test_baseline_chunks():
    adapter = BaselineAdapter(chunker="fixed_chars", chunk_size=2)
    doc = Document(id="d", text="abcd")
    chunks = adapter.chunk(doc)
    assert [c.text for c in chunks] == ["ab", "cd"]


def test_baseline_rejects_unknown_chunker():
    adapter = BaselineAdapter()
    with pytest.raises(KeyError):
        adapter.chunk(Document(id="d", text="x"), chunker="nope")


def test_base_adapter_optimize_raises():
    class Empty(BaseAdapter):
        name = "empty"

    with pytest.raises(AdapterError):
        Empty().optimize(OptimizationRequest(Document(id="d", text="x")))


def test_contextfold_optimizes_and_reports():
    adapter = ContextFoldAdapter()
    assert adapter.is_available()
    doc = Document(id="d", text="x = 1  # comment\ny = 2\n", path="a.py")
    result = adapter.optimize(OptimizationRequest(doc, method="safe"))
    assert "# comment" not in result.output
    assert result.metadata["adapter"] == "contextfold"
    assert result.metadata["detected_language"] == "python"


def test_registry_register_and_lookup():
    reg = AdapterRegistry()
    reg.register(BaselineAdapter())
    assert "baseline" in reg
    assert reg.get("baseline").name == "baseline"
    assert len(reg) == 1


def test_registry_rejects_duplicate():
    reg = AdapterRegistry([BaselineAdapter()])
    with pytest.raises(ValueError):
        reg.register(BaselineAdapter())


def test_registry_replace():
    reg = AdapterRegistry([BaselineAdapter()])
    replacement = BaselineAdapter()
    reg.register(replacement, replace=True)
    assert reg.get("baseline") is replacement


def test_registry_requires_name():
    class Nameless(BaseAdapter):
        pass

    with pytest.raises(ValueError):
        AdapterRegistry().register(Nameless())


def test_registry_unknown_name():
    reg = AdapterRegistry()
    with pytest.raises(KeyError):
        reg.get("nope")


def test_registry_find_by_capability():
    reg = AdapterRegistry([BaselineAdapter()])
    assert reg.find(Capability.CHUNK_TEXT) == ("baseline",)
    assert reg.find(Capability.EXTRACT_PDF) == ()


def test_default_registry_has_builtins():
    reg = default_registry()
    assert {"baseline", "contextfold"} <= set(reg.names())
    assert default_registry() is reg


def test_adapter_info_for_optional_dependency():
    class NeedsMissing(BaseAdapter):
        name = "needs-missing"
        requires = ("definitely_not_a_real_module_xyz",)
        capabilities = of(Capability.OPTIMIZE_TEXT)

    adapter = NeedsMissing()
    info = adapter.info()
    assert info.available is False
    assert "definitely_not_a_real_module_xyz" in info.detail
