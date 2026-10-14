"""The neutral baseline adapter.

It performs *no* reduction (identity) and only chunking. It exists as a control:
any measured reduction relative to the baseline is attributable to the adapter
under test, not to the harness.
"""

from __future__ import annotations

from typing import Any

from ..capabilities import Capability, of
from ..chunking import Chunk, chunk
from ..models import Document, OptimizationRequest, OptimizationResult
from .base import BaseAdapter


class BaselineAdapter(BaseAdapter):
    name = "baseline"
    version = "1"
    capabilities = of(Capability.OPTIMIZE_TEXT, Capability.CHUNK_TEXT)

    def __init__(self, chunker: str = "fixed_chars", chunk_size: int = 1000) -> None:
        self._chunker = chunker
        self._chunk_size = chunk_size

    def optimize(self, request: OptimizationRequest) -> OptimizationResult:
        return OptimizationResult(
            document_id=request.document.id,
            output=request.document.text,
            method=request.method,
            lossy=False,
            metadata={"adapter": self.name, "identity": True},
        )

    def chunk(self, document: Document, **options: Any) -> tuple[Chunk, ...]:
        name = options.get("chunker", self._chunker)
        size = options.get("size", self._chunk_size)
        return chunk(name, document.text, size=size)


__all__ = ["BaselineAdapter"]
