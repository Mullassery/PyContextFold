"""Fake-module contract tests for the optional ecosystem adapters.

These tests inject synthetic modules into ``sys.modules`` to check adapter
logic. They are **not** evidence that a sibling package works. Real cross-repo
coverage lives in ``tests/bench/test_ecosystem_adapters_real.py``; see
``docs/BENCH_ADAPTERS.md`` for the tested/untested matrix.
"""

from __future__ import annotations

import sys
import types

import pytest

from pycontextfold.bench.adapters import (
    OpenAnchorAdapter,
    PyAgentHoundAdapter,
    PyAPICheckAdapter,
    PyInferenceManagerAdapter,
    PyStreamAIAdapter,
    PyStreamMCPAdapter,
    PyStreamPDFAdapter,
    PyTokenCalcAdapter,
    PyVectorHoundAdapter,
)
from pycontextfold.bench.adapters.base import AdapterError
from pycontextfold.bench.capabilities import Capability
from pycontextfold.bench.models import Document


def _module(name: str, **attrs) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__version__ = attrs.pop("__version__", "0.test")
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


def _install(monkeypatch, module: types.ModuleType) -> None:
    monkeypatch.setitem(sys.modules, module.__name__, module)


# --------------------------------------------------------------------------- #
# PyTokenCalc
# --------------------------------------------------------------------------- #


def test_pytokencalc_measurer(monkeypatch):
    module = _module(
        "pytokencalc",
        count_tokens=lambda text, model=None: len(text.split()),
        estimate_cost=lambda tokens, model=None: tokens * 0.001,
        PRICING_TABLE={"gpt-x": {}},
    )
    _install(monkeypatch, module)
    adapter = PyTokenCalcAdapter()
    assert adapter.is_available()
    assert adapter.resolve_version() == "0.test"

    measurer = adapter.measurer()
    assert measurer.exact is True
    assert measurer.count("a b c") == 3
    assert adapter.count_tokens("a b", "gpt-x") == 2
    assert adapter.estimate_cost(10, "gpt-x") == pytest.approx(0.01)
    assert adapter.available_models() == ("gpt-x",)


def test_pytokencalc_missing(monkeypatch):
    import pycontextfold.bench.adapters.base as base

    monkeypatch.setattr(base, "_module_available", lambda name: name != "pytokencalc")
    monkeypatch.setattr(base, "load_optional", lambda name: None if name == "pytokencalc" else __import__(name))
    adapter = PyTokenCalcAdapter()
    assert not adapter.is_available()
    with pytest.raises(AdapterError):
        adapter.measurer()


# --------------------------------------------------------------------------- #
# PyAPICheck
# --------------------------------------------------------------------------- #


def test_pyapicheck_inventory_and_ground_truth(monkeypatch):
    module = _module(
        "pyapicheck",
        discover_directory=lambda path: [
            {"qualified_name": "pkg.a"},
            {"name": "pkg.b"},
            {"name": "pkg.a"},  # duplicate
            {"other": "ignored"},
        ],
    )
    _install(monkeypatch, module)
    adapter = PyAPICheckAdapter()
    assert adapter.inventory("/tmp/x") == ("pkg.a", "pkg.b")
    gt = adapter.ground_truth("doc", "/tmp/x")
    assert gt.must_preserve == ("pkg.a", "pkg.b")
    assert gt.labels["source"] == "pyapicheck"


def test_pyapicheck_object_items(monkeypatch):
    class Item:
        def __init__(self, name):
            self.name = name

    module = _module("pyapicheck", discover=lambda path: [Item("a"), Item("b")])
    _install(monkeypatch, module)
    assert PyAPICheckAdapter().inventory("p") == ("a", "b")


# --------------------------------------------------------------------------- #
# PyStreamPDF
# --------------------------------------------------------------------------- #


def test_pystreampdf_extract_and_chunk(monkeypatch):
    class Handle:
        text = "hello pdf"

    class Chunk:
        def __init__(self, text):
            self.text = text

    class SemanticChunker:
        def __init__(self, target_tokens=500):
            self.target_tokens = target_tokens

        def chunk_content(self, content, element_type, page_start, page_end, **kw):
            return [Chunk(content[:5]), Chunk(content[5:])]

    module = _module("pystreampdf", open=lambda path: Handle(), SemanticChunker=SemanticChunker)
    _install(monkeypatch, module)
    adapter = PyStreamPDFAdapter()
    doc = adapter.extract("/tmp/a.pdf")
    assert doc.text == "hello pdf"
    assert doc.media_type == "application/pdf"
    chunks = adapter.chunk(doc)
    assert "".join(c.text for c in chunks) == "hello pdf"


def test_pystreampdf_requires_text(monkeypatch):
    module = _module("pystreampdf", open=lambda path: object())
    _install(monkeypatch, module)
    with pytest.raises(AdapterError):
        PyStreamPDFAdapter().extract("/tmp/a.pdf")


# --------------------------------------------------------------------------- #
# PyVectorHound
# --------------------------------------------------------------------------- #


def test_pyvectorhound_dict_metrics(monkeypatch):
    module = _module(
        "pyvectorhound", evaluate=lambda **kw: {"recall@5": 0.8, "ndcg": 0.6, "junk": "x"}
    )
    _install(monkeypatch, module)
    adapter = PyVectorHoundAdapter()
    assert adapter.retrieval_metrics() == {"recall@5": 0.8, "ndcg": 0.6}


def test_pyvectorhound_object_metrics(monkeypatch):
    class Result:
        recall_at_5 = 0.9
        ndcg = 0.5

    module = _module("pyvectorhound", evaluate=lambda **kw: Result())
    _install(monkeypatch, module)
    metrics = PyVectorHoundAdapter().retrieval_metrics()
    assert metrics["recall_at_5"] == 0.9
    assert metrics["ndcg"] == 0.5


def test_pyvectorhound_contract_missing(monkeypatch):
    module = _module("pyvectorhound")
    _install(monkeypatch, module)
    with pytest.raises(AdapterError):
        PyVectorHoundAdapter().retrieval_metrics()


# --------------------------------------------------------------------------- #
# PyAgentHound
# --------------------------------------------------------------------------- #


def test_pyagenthound_dict_metrics(monkeypatch):
    module = _module("pyagenthound", evaluate=lambda cases, **kw: {"passed": 3, "failed": 1})
    _install(monkeypatch, module)
    adapter = PyAgentHoundAdapter()
    assert adapter.agent_metrics([1, 2, 3, 4]) == {"passed": 3.0, "failed": 1.0}


def test_pyagenthound_nested_evaluate(monkeypatch):
    evaluation = types.ModuleType("pyagenthound.evaluation")
    evaluation.evaluate = lambda cases, **kw: {"pass_rate": 0.75}
    module = _module("pyagenthound")
    module.evaluation = evaluation
    _install(monkeypatch, module)
    assert PyAgentHoundAdapter().agent_metrics([]) == {"pass_rate": 0.75}


def test_pyagenthound_tracer(monkeypatch):
    class AgentHound:
        def __init__(self, endpoint=None):
            self.endpoint = endpoint

    module = _module("pyagenthound", AgentHound=AgentHound)
    _install(monkeypatch, module)
    tracer = PyAgentHoundAdapter().tracer(endpoint="http://x")
    assert tracer.endpoint == "http://x"


# --------------------------------------------------------------------------- #
# PyInferenceManager
# --------------------------------------------------------------------------- #


def test_pyinferencemanager_score(monkeypatch):
    class Orchestrator:
        def run(self, prompt, **kwargs):
            return {"output": "0.5"}

    module = _module("pyinferencemanager", Orchestrator=Orchestrator)
    _install(monkeypatch, module)
    adapter = PyInferenceManagerAdapter()
    assert adapter.complete("hi") == "0.5"
    assert adapter.score("hi") == pytest.approx(0.5)


def test_pyinferencemanager_non_numeric_score(monkeypatch):
    class Orchestrator:
        def run(self, prompt, **kwargs):
            return "not a number"

    module = _module("pyinferencemanager", Orchestrator=Orchestrator)
    _install(monkeypatch, module)
    with pytest.raises(AdapterError):
        PyInferenceManagerAdapter().score("hi")


# --------------------------------------------------------------------------- #
# PyStreamAI
# --------------------------------------------------------------------------- #


def test_pystreamai_complete_and_score(monkeypatch):
    module = _module("pystreamai", complete=lambda prompt, **kw: "0.25")
    _install(monkeypatch, module)
    adapter = PyStreamAIAdapter()
    assert adapter.complete("q") == "0.25"
    assert adapter.score("q") == pytest.approx(0.25)


def test_pystreamai_score_function(monkeypatch):
    module = _module("pystreamai", score=lambda prompt, **kw: 0.9)
    _install(monkeypatch, module)
    assert PyStreamAIAdapter().score("q") == pytest.approx(0.9)


# --------------------------------------------------------------------------- #
# PyStreamMCP
# --------------------------------------------------------------------------- #


def test_pystreammcp_discovery_registry(monkeypatch):
    class SourceRegistry:
        def discover(self, *args, **kwargs):
            return [{"id": "a", "text": "hello"}, "plain string"]

    discovery = types.ModuleType("pystreammcp.discovery")
    discovery.SourceRegistry = SourceRegistry
    module = _module("pystreammcp")
    module.discovery = discovery
    _install(monkeypatch, module)

    documents = PyStreamMCPAdapter().discover()
    assert [d.text for d in documents] == ["hello", "plain string"]
    assert documents[0].id == "a"
    assert all(isinstance(d, Document) for d in documents)


def test_pystreammcp_top_level_discover(monkeypatch):
    module = _module("pystreammcp", discover=lambda **kw: ["x", "y"])
    _install(monkeypatch, module)
    documents = PyStreamMCPAdapter().discover()
    assert [d.text for d in documents] == ["x", "y"]


# --------------------------------------------------------------------------- #
# OpenAnchor
# --------------------------------------------------------------------------- #


def test_openanchor_constructors(monkeypatch):
    class TokenCollector:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class Analytics:
        pass

    module = _module("openanchor", TokenCollector=TokenCollector, Analytics=Analytics)
    _install(monkeypatch, module)
    adapter = OpenAnchorAdapter()
    collector = adapter.token_collector(flush=True)
    assert collector.kwargs == {"flush": True}
    assert isinstance(adapter.analytics(), Analytics)


def test_openanchor_missing_contract(monkeypatch):
    module = _module("openanchor")
    _install(monkeypatch, module)
    with pytest.raises(AdapterError):
        OpenAnchorAdapter().token_collector()


# --------------------------------------------------------------------------- #
# Registry integration
# --------------------------------------------------------------------------- #


def test_all_ecosystem_adapters_registered():
    from pycontextfold.bench.adapters import default_registry

    names = default_registry().names()
    for expected in (
        "baseline",
        "contextfold",
        "pytokencalc",
        "pyapicheck",
        "pystreampdf",
        "pyvectorhound",
        "pyagenthound",
        "pyinferencemanager",
        "pystreamai",
        "pystreammcp",
        "openanchor",
    ):
        assert expected in names


def test_availability_reflects_injection(monkeypatch):
    from pycontextfold.bench.adapters import default_registry

    adapter = default_registry().get("pytokencalc")
    _install(monkeypatch, _module("pytokencalc", count_tokens=lambda text, model=None: 1))
    assert adapter.info().available is True
    assert adapter.info().version == "0.test"


def test_capability_lookup_for_ecosystem():
    from pycontextfold.bench.adapters import default_registry

    registry = default_registry()
    assert registry.find(Capability.EXTRACT_PDF) == ("pystreampdf",)
    assert registry.find(Capability.API_INVENTORY) == ("pyapicheck",)
    assert registry.find(Capability.AGENT_METRICS) == ("pyagenthound",)
    assert registry.find(Capability.COUNT_TOKENS_EXACT) == ("pytokencalc",)


def test_token_measurer_falls_back_when_absent(monkeypatch):
    import pycontextfold.bench.adapters.base as base
    from pycontextfold.bench.adapters import default_registry, token_measurer

    monkeypatch.setattr(base, "_module_available", lambda name: name != "pytokencalc")
    monkeypatch.setattr(base, "load_optional", lambda name: None if name == "pytokencalc" else __import__(name))
    measurer = token_measurer(default_registry())
    assert measurer.exact is False


def test_token_measurer_uses_pytokencalc_when_present(monkeypatch):
    from pycontextfold.bench.adapters import default_registry, token_measurer

    _install(monkeypatch, _module("pytokencalc", count_tokens=lambda text, model=None: len(text)))
    measurer = token_measurer(default_registry())
    assert measurer.exact is True
    assert measurer.count("abcd") == 4


@pytest.mark.optional
@pytest.mark.skipif(
    "pytokencalc" not in sys.modules, reason="real pytokencalc not installed"
)
def test_real_pytokencalc_optional():  # pragma: no cover - opt-in
    adapter = PyTokenCalcAdapter()
    assert adapter.is_available()
    assert adapter.count_tokens("hello world") >= 1
