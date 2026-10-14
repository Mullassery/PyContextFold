# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

Initial release.

### Added

- **`contextfold-core`**: language detection, the profile/rule system, edit
  algebra with an offset map, the report schema, and budget accounting — with no
  tree-sitter dependency.
- **`contextfold-parsers`**: tree-sitter-backed analyzers for Python, Rust,
  JavaScript, TypeScript, TSX and Go, plus detection heuristics for Markdown,
  logs, JSON and text.
- **`contextfold-cli`**: the `contextfold` binary (stdin/file/directory input,
  `--in-place`, JSON reports, byte/character budgets).
- **`contextfold-py`** / **`pycontextfold`**: typed Python bindings
  (`fold`, `fold_file`, `Engine`, `FoldRequest`, `Report`, typed exceptions),
  an `abi3-py310` wheel via maturin.
- Six built-in profiles: `safe`, `code-review`, `interface-only`,
  `documentation`, `logs`, `budgeted`, all versioned and surfaced in reports.
- Preservation policies: protected ranges, marker lines, protected imports and
  protected error handling.
- Transformation reports with per-rule counts, bytes removed, input/output size
  stats, reduction ratio, warnings and an explicit `semantic_equivalence:
  not_guaranteed`.
- Tests: Rust unit/integration tests, property tests (determinism, edit algebra,
  whitespace invariants), CLI integration tests and a Python test suite.
- Reproducible criterion benchmarks and documentation under `docs/`.

[Unreleased]: https://github.com/Mullassery/PyContextFold/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Mullassery/PyContextFold/releases/tag/v0.1.0
