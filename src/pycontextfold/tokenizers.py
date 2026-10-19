"""Built-in tokenizer adapters for PyContextFold.

The Rust core deliberately does not ship a provider token catalogue.  This
module supplies optional, maintained adapters (tiktoken and Hugging Face
tokenizers) plus a model-name mapping so ``budget_tokens`` works out of the box.

The core remains dependency-free unless one of these adapters is used.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TokenizerUnavailable(RuntimeError):
    """Raised when a requested tokenizer backend is not installed."""


class TiktokenTokenizer:
    """OpenAI/tiktoken tokenizer with an optional encoding override."""

    def __init__(self, model: str = "gpt-4o", encoding_name: str | None = None):
        try:
            import tiktoken
        except ImportError as exc:
            raise TokenizerUnavailable(
                "tiktoken is not installed. Install with "
                "`pip install pycontextfold[tiktoken]`."
            ) from exc
        self.model = model
        try:
            self._encoding = (
                tiktoken.get_encoding(encoding_name)
                if encoding_name
                else tiktoken.encoding_for_model(model)
            )
        except KeyError as exc:
            raise TokenizerUnavailable(
                f"tiktoken has no encoding for model {model!r}; pass encoding_name=..."
            ) from exc
        self.name = f"tiktoken:{self._encoding.name}"

    def count(self, text: str) -> int:
        return len(self._encoding.encode(text, disallowed_special=()))


class HuggingFaceTokenizer:
    """Hugging Face ``tokenizers``/``transformers`` adapter."""

    def __init__(self, model: str, *, use_fast: bool = True, **kwargs: Any):
        try:
            from transformers import AutoTokenizer
        except ImportError as exc:
            raise TokenizerUnavailable(
                "transformers is not installed. Install with "
                "`pip install pycontextfold[hf]`."
            ) from exc
        self.model = model
        self._tokenizer = AutoTokenizer.from_pretrained(
            model, use_fast=use_fast, **kwargs
        )
        self.name = f"hf:{model}"

    def count(self, text: str) -> int:
        return len(self._tokenizer.encode(text, add_special_tokens=False))


# Conservative model -> encoding mapping. tiktoken resolves most OpenAI
# models itself; this covers common aliases and makes the intent explicit.
_TIKTOKEN_MODELS = {
    "gpt-4o": "o200k_base",
    "gpt-4o-mini": "o200k_base",
    "gpt-4.1": "o200k_base",
    "o1": "o200k_base",
    "o3": "o200k_base",
    "gpt-4": "cl100k_base",
    "gpt-4-turbo": "cl100k_base",
    "gpt-3.5-turbo": "cl100k_base",
    "text-embedding-3-small": "cl100k_base",
    "text-embedding-3-large": "cl100k_base",
}


def tokenizer_for(
    model: str = "gpt-4o",
    *,
    backend: str = "auto",
    encoding_name: str | None = None,
    **kwargs: Any,
):
    """Resolve a tokenizer for ``model``.

    backend:
        ``auto`` (tiktoken for known OpenAI models, otherwise Hugging Face),
        ``tiktoken`` or ``hf``.
    """
    backend = backend.lower()
    if backend == "tiktoken" or (backend == "auto" and model in _TIKTOKEN_MODELS):
        return TiktokenTokenizer(
            model=model,
            encoding_name=encoding_name or _TIKTOKEN_MODELS.get(model),
        )
    if backend in ("hf", "huggingface", "transformers", "auto"):
        return HuggingFaceTokenizer(model, **kwargs)
    raise ValueError(f"unknown tokenizer backend: {backend!r}")


def count_tokens(text: str, model: str = "gpt-4o", **kwargs: Any) -> int:
    """Count tokens with the best available adapter for ``model``."""
    return tokenizer_for(model, **kwargs).count(text)


def fold_with_model(
    content: str,
    *,
    model: str = "gpt-4o",
    budget_tokens: int,
    tokenizer: Any = None,
    profile: str = "budgeted",
    backend: str = "auto",
    encoding_name: str | None = None,
    **fold_kwargs: Any,
):
    """Fold ``content`` using a real tokenizer for ``budget_tokens``."""
    from . import Engine, FoldRequest

    tok = tokenizer or tokenizer_for(
        model, backend=backend, encoding_name=encoding_name
    )
    request = FoldRequest(
        content,
        profile=profile,
        budget_tokens=budget_tokens,
        tokenizer=tok,
        **fold_kwargs,
    )
    return Engine().fold_request(request)


def fold_file_with_model(
    path: str | Path,
    *,
    model: str = "gpt-4o",
    budget_tokens: int,
    tokenizer: Any = None,
    profile: str = "budgeted",
    backend: str = "auto",
    encoding_name: str | None = None,
    **fold_kwargs: Any,
):
    """Read ``path`` and fold it with a real tokenizer (never writes to disk)."""
    content = Path(path).read_text(encoding="utf-8")
    return fold_with_model(
        content,
        model=model,
        budget_tokens=budget_tokens,
        tokenizer=tokenizer,
        profile=profile,
        backend=backend,
        encoding_name=encoding_name,
        **fold_kwargs,
    )


__all__ = [
    "HuggingFaceTokenizer",
    "TiktokenTokenizer",
    "TokenizerUnavailable",
    "count_tokens",
    "fold_file_with_model",
    "fold_with_model",
    "tokenizer_for",
]
