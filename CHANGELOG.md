# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`pycontextfold.bench`**: an offline-first benchmarking foundation.
  - Immutable, JSON-round-trippable models (`Document`, `GroundTruth`,
    `Dataset`, `ExperimentConfig`, `MetricResult`, `OptimizationResult`).
  - Capability declarations (`Capability`, `CapabilitySet`) so adapters advertise
    exactly what they support.
  - Adapter protocol + registry with lazy, optional imports and availability
    detection; built-in `baseline` (identity) and `contextfold` adapters.
  - Deterministic baseline chunkers (`fixed_chars`, `fixed_bytes`, `paragraphs`,
    `lines`) with lossless coverage.
  - Honest token-measurement abstraction (approximate by default, exact only when
    supplied).
  - Core metrics: size/char/token reduction, ground-truth preservation recall and
    drop precision — unavailable metrics are reported, never faked.
  - Deterministic synthetic dataset and JSON/TOML configuration loading.
- **`pycontextfold.bench.runner`**: the offline experiment runner. Seeded,
  deterministic, with failure isolation (per-document adapter errors and
  unregistered/unavailable adapters are recorded, not fatal) and JSON run
  artifacts (`RunResult`, `write_run`/`read_run`) carrying content hashes.
- **`pycontextfold.bench.report`**: a self-contained HTML report (`render_report`,
  `write_report`) — inline CSS/JS, no CDN or external assets, per-adapter and
  per-document tables, and reproduction metadata. Deterministic unless a
  timestamp is supplied.
- **`pycontextfold.bench.adapters`**: optional, capability-declared adapters for
  the nine sibling projects (`pytokencalc`, `pyapicheck`, `pystreampdf`,
  `pyvectorhound`, `pyagenthound`, `pyinferencemanager`, `pystreamai`,
  `pystreammcp`, `openanchor`). Each imports its dependency lazily, reports
  `available=False` when absent, and is tested against a fixture double. Adds
  `core_registry()` and the `token_measurer()` bridge (exact tokens when
  PyTokenCalc is present, otherwise a clearly-labelled approximation).
- **`pycontextfold.bench.gates`**: quality/regression gates
  (`Threshold`, `evaluate_gates`). An unavailable metric fails a gate rather than
  passing silently.
- **`pycontextfold.bench.cli`** + `python -m pycontextfold.bench`:
  `run|report|gates|adapters|datasets` subcommands, with a `pycontextfold-bench`
  console script. `run` can write a run artifact, an HTML report and evaluate
  gates (exit code 1 on failure).
- **Packaging**: optional per-project extras (`tokens`, `pdf`, `agents`, `api`,
  `retrieval`, `inference`, `middleware`, `discovery` and an `ecosystem` bundle)
  and a cross-platform wheel/sdist release workflow (`PyO3/maturin-action` with
  PyPI trusted publishing).
- `docs/ECOSYSTEM_ASSESSMENT.md` and `docs/ROADMAP.md`.

## [0.1.2] - 2026-10-18

### Fixed
- Avoid `BrokenPipe` panic in `contextfold-cli` test helper when child exits immediately on invalid flags (`unknown_profile_is_rejected`), and enforce Unix LF line endings across Rust sources (RECHECK-033).

## [0.1.1] - 2026-10-17

### Fixed
- Audit remediation: security hardening, correctness fixes, and lint/CI gates.

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
