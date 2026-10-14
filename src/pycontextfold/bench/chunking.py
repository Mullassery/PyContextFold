"""Deterministic baseline chunkers.

These exist so that folded content can be compared against a neutral,
dependency-free baseline *and* so that chunk-level benchmarks have a reference
implementation. Chunkers are pure functions of ``(text, options)`` and are
byte-stable across runs. The fixed-size chunkers are *lossless in coverage*:
concatenating the chunks reproduces the input exactly.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Chunk:
    """A contiguous slice of a source string."""

    index: int
    text: str
    start: int
    end: int

    @property
    def char_size(self) -> int:
        return len(self.text)

    @property
    def byte_size(self) -> int:
        return len(self.text.encode("utf-8"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "char_size": self.char_size,
            "byte_size": self.byte_size,
        }


def _finalize(parts: list[tuple[int, int, str]]) -> tuple[Chunk, ...]:
    return tuple(
        Chunk(index=i, text=text, start=start, end=end)
        for i, (start, end, text) in enumerate(parts)
    )


def chunk_fixed_chars(text: str, size: int = 1000) -> tuple[Chunk, ...]:
    """Split into fixed-size character windows (lossless coverage)."""
    if size <= 0:
        raise ValueError("size must be positive")
    if not text:
        return ()
    return _finalize(
        [
            (start, min(start + size, len(text)), text[start : start + size])
            for start in range(0, len(text), size)
        ]
    )


def chunk_fixed_bytes(text: str, size: int = 1024) -> tuple[Chunk, ...]:
    """Split into windows of at most ``size`` UTF-8 bytes.

    Character boundaries are never split: a character that would overflow the
    window starts the next one.
    """
    if size <= 0:
        raise ValueError("size must be positive")
    if not text:
        return ()
    parts: list[tuple[int, int, str]] = []
    start = 0
    current: list[str] = []
    used = 0
    for i, ch in enumerate(text):
        width = len(ch.encode("utf-8"))
        if current and used + width > size:
            parts.append((start, i, "".join(current)))
            start = i
            current = []
            used = 0
        current.append(ch)
        used += width
    if current:
        parts.append((start, len(text), "".join(current)))
    return _finalize(parts)


def chunk_paragraphs(text: str, max_chars: int = 2000) -> tuple[Chunk, ...]:
    """Group blank-line-separated paragraphs up to ``max_chars`` each.

    A paragraph that on its own exceeds ``max_chars`` is emitted intact (never
    split) to keep the chunker lossless and deterministic.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if not text:
        return ()

    parts: list[tuple[int, int, str]] = []
    buf_start = 0
    buf_end = 0
    buf_len = 0
    i = 0
    n = len(text)
    while i < n:
        # find end of current paragraph (double newline)
        j = text.find("\n\n", i)
        para_end = n if j == -1 else j + 2
        para_len = para_end - i
        if buf_len and buf_len + para_len > max_chars:
            parts.append((buf_start, buf_end, text[buf_start:buf_end]))
            buf_start = i
            buf_end = para_end
            buf_len = para_len
        else:
            buf_end = para_end
            buf_len += para_len
        i = para_end
    if buf_end > buf_start:
        parts.append((buf_start, buf_end, text[buf_start:buf_end]))
    return _finalize(parts)


def chunk_lines(text: str, max_lines: int = 50) -> tuple[Chunk, ...]:
    """Group consecutive lines into windows of ``max_lines`` (lossless)."""
    if max_lines <= 0:
        raise ValueError("max_lines must be positive")
    if not text:
        return ()
    parts: list[tuple[int, int, str]] = []
    buf_start = 0
    count = 0
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "\n":
            end = i + 1
            count += 1
            if count == max_lines:
                parts.append((buf_start, end, text[buf_start:end]))
                buf_start = end
                count = 0
            i = end
        else:
            i += 1
    if buf_start < n:
        parts.append((buf_start, n, text[buf_start:n]))
    return _finalize(parts)


Chunker = Callable[..., tuple[Chunk, ...]]

CHUNKERS: Mapping[str, Chunker] = {
    "fixed_chars": chunk_fixed_chars,
    "fixed_bytes": chunk_fixed_bytes,
    "paragraphs": chunk_paragraphs,
    "lines": chunk_lines,
}


def chunk(name: str, text: str, **options: Any) -> tuple[Chunk, ...]:
    """Dispatch to a named chunker. Raises ``KeyError`` for unknown names."""
    try:
        func = CHUNKERS[name]
    except KeyError:  # pragma: no cover - defensive
        raise KeyError(
            f"unknown chunker {name!r}; known: {sorted(CHUNKERS)}"
        ) from None
    return func(text, **options)


__all__ = [
    "CHUNKERS",
    "Chunk",
    "Chunker",
    "chunk",
    "chunk_fixed_bytes",
    "chunk_fixed_chars",
    "chunk_lines",
    "chunk_paragraphs",
]
