"""Token measurement abstraction.

PyContextFold never ships a model vocabulary. Benchmarks measure tokens through a
:class:`TokenMeasurer`, and every measurement carries an ``exact`` flag so a
report never presents an approximation as a precise count. An exact measurer is
supplied by an optional adapter (e.g. PyTokenCalc); the defaults here are
explicitly approximate.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

DEFAULT_CHARS_PER_TOKEN = 4.0
"""Conservative approximation ratio used when no exact tokenizer is available."""


@runtime_checkable
class TokenMeasurer(Protocol):
    """Anything that can count tokens in a string."""

    name: str
    exact: bool

    def count(self, text: str) -> int:
        """Return the number of tokens in ``text``."""


@dataclass(frozen=True)
class ApproximateTokenMeasurer:
    """A ``chars / ratio`` approximation. ``exact`` is always ``False``."""

    chars_per_token: float = DEFAULT_CHARS_PER_TOKEN
    name: str = "approx"
    exact: bool = False

    def __post_init__(self) -> None:
        if self.chars_per_token <= 0:
            raise ValueError("chars_per_token must be positive")

    def count(self, text: str) -> int:
        if not text:
            return 0
        return max(1, round(len(text) / self.chars_per_token))


@dataclass(frozen=True)
class WhitespaceTokenMeasurer:
    """Count whitespace-delimited words. Deterministic but not exact."""

    name: str = "whitespace"
    exact: bool = False

    def count(self, text: str) -> int:
        return len(text.split())


@dataclass(frozen=True)
class CallableTokenMeasurer:
    """Wrap a caller-supplied function as a measurer.

    ``exact`` defaults to ``True`` because the caller is asserting their function
    counts real model tokens; set it to ``False`` if it does not.
    """

    func: Callable[[str], int]
    name: str = "callable"
    exact: bool = True

    def count(self, text: str) -> int:
        value = self.func(text)
        if value < 0:
            raise ValueError("token count must be non-negative")
        return int(value)


DEFAULT_MEASURER = ApproximateTokenMeasurer()
"""The project-wide default: approximate, clearly labelled."""


def count_tokens(measurer: TokenMeasurer, text: str) -> int:
    """Count tokens using ``measurer`` and validate the result."""
    value = measurer.count(text)
    if value < 0:
        raise ValueError(f"measurer {measurer.name!r} returned a negative count")
    return int(value)


__all__ = [
    "DEFAULT_CHARS_PER_TOKEN",
    "DEFAULT_MEASURER",
    "ApproximateTokenMeasurer",
    "CallableTokenMeasurer",
    "TokenMeasurer",
    "WhitespaceTokenMeasurer",
    "count_tokens",
]
