"""Repository packing mode: fold a whole repository into an LLM-ready bundle.

Deterministic and local-first. Files are discovered with simple ignore rules,
folded through the same Rust profiles as single-file folding, and emitted as a
Markdown bundle plus a machine-readable manifest with byte/token counts.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from . import fold_file
from .tokenizers import TokenizerUnavailable, tokenizer_for

DEFAULT_IGNORES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "target",
    "dist",
    "build",
}

TEXT_SUFFIXES = {
    ".py",
    ".pyi",
    ".rs",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".go",
    ".java",
    ".kt",
    ".c",
    ".h",
    ".cc",
    ".cpp",
    ".hpp",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".md",
    ".rst",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".sql",
    ".sh",
    ".css",
    ".html",
    ".xml",
    ".ini",
    ".cfg",
    ".conf",
}


@dataclass
class PackedFile:
    path: str
    bytes_in: int
    bytes_out: int
    tokens_out: int | None
    folded: bool


@dataclass
class RepoPack:
    root: str
    files: list[PackedFile] = field(default_factory=list)
    bundle: str = ""
    manifest: str = ""

    @property
    def total_tokens(self) -> int:
        return sum(f.tokens_out or 0 for f in self.files)

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "files": [f.__dict__ for f in self.files],
            "total_tokens": self.total_tokens,
            "bytes_in": sum(f.bytes_in for f in self.files),
            "bytes_out": sum(f.bytes_out for f in self.files),
        }


def _ignored(rel: PurePosixPath, patterns: Iterable[str]) -> bool:
    if any(part in DEFAULT_IGNORES for part in rel.parts):
        return True
    text = str(rel)
    for pattern in patterns:
        pattern = pattern.strip()
        if not pattern or pattern.startswith("#"):
            continue
        negate = pattern.startswith("!")
        if negate:
            pattern = pattern[1:]
        matched = PurePosixPath(text).match(pattern) or rel.name == pattern
        if matched and not negate:
            return True
    return False


def _load_ignore(root: Path, ignore_files: Iterable[str]) -> list[str]:
    patterns: list[str] = []
    for name in ignore_files:
        path = root / name
        if path.is_file():
            patterns.extend(
                path.read_text(encoding="utf-8", errors="replace").splitlines()
            )
    return patterns


def pack_repository(
    root: str | Path,
    *,
    profile: str = "safe",
    model: str = "gpt-4o",
    tokenizer=None,
    include_suffixes: Iterable[str] | None = None,
    extra_ignores: Iterable[str] = (),
    ignore_files: Iterable[str] = (".gitignore", ".contextfoldignore"),
    max_file_bytes: int = 1_000_000,
) -> RepoPack:
    root = Path(root).resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    suffixes = set(include_suffixes or TEXT_SUFFIXES)
    patterns = _load_ignore(root, ignore_files) + list(extra_ignores)
    tok = None
    if tokenizer is not None:
        tok = tokenizer
    else:
        try:
            tok = tokenizer_for(model)
        except (ImportError, KeyError, OSError, ValueError, TokenizerUnavailable):
            tok = None

    packed: list[PackedFile] = []
    sections: list[str] = [f"# Repository: {root.name}\n"]
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = PurePosixPath(path.relative_to(root).as_posix())
        if _ignored(rel, patterns) or path.suffix.lower() not in suffixes:
            continue
        try:
            if path.stat().st_size > max_file_bytes:
                continue
            raw = path.read_bytes()
            text = raw.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        result = fold_file(str(path), profile=profile)
        folded = result.output
        tokens = tok.count(folded) if tok is not None else None
        packed.append(
            PackedFile(
                path=str(rel),
                bytes_in=len(raw),
                bytes_out=len(folded.encode("utf-8")),
                tokens_out=tokens,
                folded=folded != text,
            )
        )
        sections.append(f"## {rel}\n\n````text\n{folded.rstrip()}\n````\n")

    manifest_lines = ["# ContextFold manifest", ""]
    for item in packed:
        tokens = item.tokens_out if item.tokens_out is not None else "unknown"
        manifest_lines.append(
            f"- {item.path}: {item.bytes_in} -> {item.bytes_out} bytes, tokens={tokens}"
        )
    return RepoPack(
        root=str(root),
        files=packed,
        bundle="\n".join(sections),
        manifest="\n".join(manifest_lines) + "\n",
    )


def write_pack(
    pack: RepoPack, output: str | Path, manifest: str | Path | None = None
) -> None:
    output = Path(output)
    output.write_text(pack.bundle, encoding="utf-8")
    if manifest:
        Path(manifest).write_text(pack.manifest, encoding="utf-8")


__all__ = ["PackedFile", "RepoPack", "pack_repository", "write_pack"]
