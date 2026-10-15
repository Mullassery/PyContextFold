"""Adapter for PyStreamPDF — PDF text extraction and semantic chunking.

The benchmark uses PyStreamPDF to turn PDFs into :class:`Document`s and to obtain
an independent chunking strategy for comparison. PDF parsing is never
re-implemented here.

Contract (must hold for the installed PyStreamPDF):

- ``open(path) -> document`` where ``document`` exposes extracted text via
  ``.text`` (or a ``.text`` callable / ``.extract_text()``).
- ``SemanticChunker(...)`` with a ``chunk_content(...)`` method, used for
  chunk-level comparison when available.
"""

from __future__ import annotations

from typing import Any

from ..capabilities import Capability, of
from ..chunking import Chunk
from ..models import Document
from .base import AdapterError, BaseAdapter, module_version


def _document_text(handle: Any) -> str:
    text = getattr(handle, "text", None)
    if callable(text):
        text = text()
    if isinstance(text, str):
        return text
    extract = getattr(handle, "extract_text", None)
    if callable(extract):
        value = extract()
        if isinstance(value, str):
            return value
    raise AdapterError(
        "PyStreamPDF document object exposes neither .text nor .extract_text()"
    )


class PyStreamPDFAdapter(BaseAdapter):
    name = "pystreampdf"
    requires = ("pystreampdf",)
    capabilities = of(Capability.EXTRACT_PDF, Capability.CHUNK_TEXT)

    def resolve_version(self) -> str:
        return module_version(self.requires[0])

    def extract(self, path: str, document_id: str | None = None) -> Document:
        """Extract a PDF into a :class:`Document`."""
        module = self.load()
        opener = getattr(module, "open", None) or getattr(module, "load_index", None)
        if opener is None:
            raise AdapterError("pystreampdf does not expose open/load_index")
        handle = opener(path)
        text = _document_text(handle)
        return Document(
            id=document_id or path,
            text=text,
            path=path,
            media_type="application/pdf",
            metadata={"source": "pystreampdf"},
        )

    def chunk(self, document: Document, **options: Any) -> tuple[Chunk, ...]:
        module = self.load()
        chunker_cls = getattr(module, "SemanticChunker", None)
        if chunker_cls is None:
            raise AdapterError("pystreampdf does not expose SemanticChunker")
        target_tokens = int(options.get("target_tokens", 500))
        chunker = chunker_cls(target_tokens=target_tokens)
        raw = chunker.chunk_content(
            document.text,
            options.get("element_type", "text"),
            options.get("page_start", 0),
            options.get("page_end", 0),
        )
        chunks: list[Chunk] = []
        cursor = 0
        for index, item in enumerate(raw):
            text = getattr(item, "text", None)
            if not isinstance(text, str):
                text = str(item)
            start = cursor
            end = start + len(text)
            cursor = end
            chunks.append(Chunk(index=index, text=text, start=start, end=end))
        return tuple(chunks)


__all__ = ["PyStreamPDFAdapter"]
