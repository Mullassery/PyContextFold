"""Real cross-repo adapter tests against installed sibling packages.

These are **not** fake-module contract tests. Each test imports the actual
sibling package and exercises the adapter's real call path. Tests that cannot
run without a model/service are skipped with an explicit reason; a skip is not
evidence of support.
"""

from __future__ import annotations

import json

import pytest

from pycontextfold.bench.adapters import (
    OpenAnchorAdapter,
    PyAgentHoundAdapter,
    PyAPICheckAdapter,
    PyInferenceManagerAdapter,
    PyStreamMCPAdapter,
    PyTokenCalcAdapter,
    PyVectorHoundAdapter,
)


def test_pytokencalc_real_count_and_cost() -> None:
    pytest.importorskip("pytokencalc")
    adapter = PyTokenCalcAdapter()
    assert adapter.is_available()
    assert "gpt-4o" in adapter.available_models()

    tokens = adapter.count_tokens("hello world", model="gpt-4o")
    assert tokens > 0
    assert adapter.estimate_cost(tokens, model="gpt-4o") >= 0.0


def test_pyapicheck_real_openapi_inventory(tmp_path) -> None:
    pytest.importorskip("pyapicheck")
    spec = {
        "openapi": "3.0.3",
        "info": {"title": "demo", "version": "1"},
        "paths": {"/items": {"get": {}, "post": {}}},
    }
    (tmp_path / "openapi.json").write_text(json.dumps(spec), encoding="utf-8")

    adapter = PyAPICheckAdapter()
    assert adapter.is_available()
    names = adapter.inventory(str(tmp_path))
    assert "GET /items" in names
    assert "POST /items" in names

    ground_truth = adapter.ground_truth("demo", str(tmp_path))
    assert set(ground_truth.must_preserve) == set(names)


def test_openanchor_real_token_collector() -> None:
    pytest.importorskip("openanchor")
    adapter = OpenAnchorAdapter()
    assert adapter.is_available()
    assert adapter.token_collector() is not None


def test_pystreammcp_real_discovery() -> None:
    pytest.importorskip("pystreammcp")
    adapter = PyStreamMCPAdapter()
    assert adapter.is_available()
    assert isinstance(adapter.discover("no sources configured", limit=1), tuple)


def test_pyvectorhound_real_ranking_metrics() -> None:
    pytest.importorskip("pyvectorhound")
    adapter = PyVectorHoundAdapter()
    assert adapter.is_available()
    metrics = adapter.retrieval_metrics(
        ranked_document_ids=["a", "b", "c"],
        diversity_scores=[0.9, 0.8, 0.7],
        relevant_docs=["a", "c"],
        k=3,
    )
    assert metrics
    assert all(isinstance(value, float) for value in metrics.values())


def test_pyagenthound_real_import_and_version() -> None:
    pytest.importorskip("pyagenthound")
    adapter = PyAgentHoundAdapter()
    assert adapter.is_available()
    assert adapter.resolve_version()


def test_pyinferencemanager_real_import_and_version() -> None:
    pytest.importorskip("pyinferencemanager")
    adapter = PyInferenceManagerAdapter()
    assert adapter.is_available()
    assert adapter.resolve_version()


def test_pystreampdf_not_available_here() -> None:
    # Documented gap: pystreampdf publishes cp311-only wheels; this venv is 3.12.
    pytest.importorskip("pystreampdf", reason="pystreampdf not installed (cp311-only wheel)")


def test_pystreamai_not_available_here() -> None:
    pytest.importorskip("pystreamai", reason="pystreamai not installed (cp311-only wheel)")
