"""Adapter over the PyContextFold core (this package).

It is the reference optimization provider: deterministic, local-first and
dependency-free. The import of the native ``_core`` module happens lazily so the
benchmark package can be imported (and its registry inspected) even in an
environment where the extension has not been built.
"""

from __future__ import annotations

from typing import Any

from ..capabilities import Capability, of
from ..models import Document, OptimizationRequest, OptimizationResult
from .base import AdapterError, BaseAdapter

#: Option keys accepted from ``OptimizationRequest.options`` for the core.
_PASSTHROUGH_OPTIONS = (
    "language",
    "allow_lossy",
    "budget_bytes",
    "budget_chars",
    "budget_tokens",
    "protected_ranges",
    "protected_line_markers",
)


class ContextFoldAdapter(BaseAdapter):
    name = "contextfold"
    capabilities = of(Capability.OPTIMIZE_TEXT, Capability.CHUNK_TEXT)

    def __init__(self) -> None:
        try:
            import pycontextfold as _pcf

            self._pcf = _pcf
            self.version = getattr(_pcf, "__version__", "0")
        except ImportError:  # pragma: no cover - only when the extension is absent
            self._pcf = None
            self.version = "0"

    def is_available(self) -> bool:
        return self._pcf is not None

    def availability_detail(self) -> str:
        if self._pcf is None:
            return "pycontextfold native core (_core) is not importable"
        return ""

    def optimize(self, request: OptimizationRequest) -> OptimizationResult:
        if self._pcf is None:
            raise AdapterError("pycontextfold core is not available")

        document = request.document
        options = {k: v for k, v in request.options.items() if k in _PASSTHROUGH_OPTIONS}

        try:
            fold_request = self._pcf.FoldRequest(
                document.text,
                profile=request.method or "safe",
                path=document.path,
                **options,
            )
            result = self._pcf.Engine().fold_request(fold_request)
        except self._pcf.ContextFoldError as exc:
            raise AdapterError(f"core fold failed: {exc}") from exc

        report = result.report
        return OptimizationResult(
            document_id=document.id,
            output=result.output,
            method=report.profile,
            lossy=result.lossy,
            metadata={
                "adapter": self.name,
                "engine_version": report.engine_version,
                "profile": report.profile,
                "detected_language": report.detected_language,
                "parse_status": report.parse_status,
                "behavior_preserving": report.behavior_preserving,
                "reduction_ratio": report.reduction_ratio,
                "report": report.to_dict(),
            },
        )

    def chunk(self, document: Document, **options: Any):
        from ..chunking import chunk

        name = options.get("chunker", "fixed_chars")
        size = options.get("size", 1000)
        return chunk(name, document.text, size=size)


__all__ = ["ContextFoldAdapter"]
