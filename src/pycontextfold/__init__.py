"""PyContextFold — structure-aware context optimization for LLM consumption.

PyContextFold transforms source code, documentation, logs and structured text
into compact representations. It is local-first and deterministic: it never
sends content to external services, never overwrites source files, and performs
all parsing, transformation, validation and reporting in a native Rust core.

The Python API is a thin, typed wrapper over that Rust core.

Example
-------
    >>> import pycontextfold as pcf
    >>> result = pcf.fold(source, profile="safe", path="app.py")
    >>> result.output
    '...'
    >>> result.report.reduction_ratio > 0
    True

Profiles are versioned and documented. See :func:`profiles` for the built-in
names and :func:`profile_info` for the guarantees each one makes.
"""

from ._core import (
    BudgetNotMetError,
    ContextFoldError,
    Engine,
    FoldRequest,
    FoldResult,
    InvalidConfigError,
    Report,
    UnknownProfileError,
    __version__,
    detect_language,
    fold,
    fold_file,
    profile_info,
    profiles,
    supported_languages,
)
from .repo import PackedFile, RepoPack, pack_repository, write_pack
from .tokenizers import (
    HuggingFaceTokenizer,
    TiktokenTokenizer,
    TokenizerUnavailable,
    count_tokens,
    fold_file_with_model,
    fold_with_model,
    tokenizer_for,
)

__all__ = [
    "BudgetNotMetError",
    "ContextFoldError",
    "Engine",
    "FoldRequest",
    "FoldResult",
    "HuggingFaceTokenizer",
    "InvalidConfigError",
    "PackedFile",
    "RepoPack",
    "Report",
    "TiktokenTokenizer",
    "TokenizerUnavailable",
    "UnknownProfileError",
    "__version__",
    "count_tokens",
    "detect_language",
    "fold",
    "fold_file",
    "fold_file_with_model",
    "fold_with_model",
    "pack_repository",
    "profile_info",
    "profiles",
    "supported_languages",
    "tokenizer_for",
    "write_pack",
]
