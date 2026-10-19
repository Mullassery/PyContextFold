"""Tokenizer adapter tests. tiktoken is optional; skip when unavailable."""

from __future__ import annotations

import pytest

import pycontextfold as pcf


def test_model_mapping_and_count():
    pytest.importorskip("tiktoken")
    tok = pcf.tokenizer_for("gpt-4o")
    assert tok.name.startswith("tiktoken:")
    assert tok.count("hello world") > 0


def test_count_tokens_convenience():
    pytest.importorskip("tiktoken")
    assert pcf.count_tokens("hello", model="gpt-4o") == 1


def test_fold_with_model_respects_budget():
    pytest.importorskip("tiktoken")
    source = "# comment\n" + "\n".join(f"x_{i} = {i}" for i in range(200))
    result = pcf.fold_with_model(source, model="gpt-4o", budget_tokens=200)
    budget = result.report.to_dict()["budget"]
    assert budget["tokenizer"].startswith("tiktoken:")
    assert budget["exact_tokens"] is True
    assert result.output


def test_missing_backend_is_actionable(monkeypatch):
    import pycontextfold.tokenizers as mod

    def unavailable(*args, **kwargs):
        raise mod.TokenizerUnavailable("pip install pycontextfold[tiktoken]")

    monkeypatch.setattr(mod, "TiktokenTokenizer", unavailable)
    with pytest.raises(mod.TokenizerUnavailable, match="pycontextfold\\[tiktoken\\]"):
        mod.tokenizer_for("gpt-4o")
