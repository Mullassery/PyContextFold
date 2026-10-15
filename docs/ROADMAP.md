# Roadmap

PyContextFold started as a single-purpose optimization engine (the Rust core,
CLI and Python bindings shipped as v0.1.0). This roadmap extends it — in
**Python-first** fashion — into a context-optimization *and benchmarking*
platform, while keeping the existing Rust core as the embedded transformation
provider.

Guiding constraints:

- The core runs with **zero** ecosystem repositories installed.
- Adapters are optional, capability-declared and checked before use.
- Synthetic/offline benchmarks must run with **no credentials and no network**.
- Heavy dependencies are optional extras, never hard requirements.
- Reports are self-contained (single HTML file) and reproducible (seeded).

## Phases

### Phase 0 — Repository assessment ✅
- Read the nine sibling repositories and record confirmed interfaces.
- See [`ECOSYSTEM_ASSESSMENT.md`](ECOSYSTEM_ASSESSMENT.md).

### Phase 1 — Python benchmarking foundation 🚧
Pure-stdlib package `pycontextfold.bench`:
- Versioned data models (`Document`, `GroundTruth`, `Dataset`, `ExperimentConfig`,
  `RunResult`, `MetricResult`).
- Capability enum + declared capability sets.
- Adapter protocol + registry with lazy, optional imports.
- Deterministic baseline chunkers and a `ContextFoldAdapter` wrapping the core.
- Token-measurement abstraction (approximate by default, exact when a measurer
  is supplied) that reports `exact` honestly.
- Core metrics (size/token reduction, preservation recall, drop precision).
- Config loading (JSON always; TOML when `tomllib` is available) + validation.
- Synthetic dataset loader (no network).

### Phase 2 — Offline experiment runner ✅
- Seeded experiment runner that pairs a dataset with adapters and metrics.
- Deterministic `RunResult` serialization (stable key order, content hashes).
- Failure isolation: an adapter that errors is marked failed, not fatal.
- JSON run artifacts.

### Phase 3 — Self-contained HTML report ✅
- Single-file HTML with inline CSS/JS, no CDN, no external assets.
- Tables for size/token/cost reduction and preservation; per-document drill-down.
- Reproduction metadata (versions, seeds, config hash).

### Phase 4 — Optional ecosystem adapters ✅
- `pytokencalc` (exact tokens + cost), `pystreampdf` (PDF ingestion),
  `pyapicheck` (ground-truth API surface), `pyvectorhound` (retrieval metrics),
  `pyagenthound` (agent metrics), `pyinferencemanager` / `pystreamai` (optional
  quality scoring), `pystreammcp` (corpus sourcing), `openanchor` (attribution).
- Each tested against a fixture double; real-package tests marked `optional` and
  skipped when the package is absent.

### Phase 5 — Quality gates & CLI
- `pycontextfold bench run|report|datasets|adapters` subcommands.
- Regression gates: fail an experiment when reduction or preservation drops
  below a threshold.

### Phase 6 — Packaging, docs, release
- Extras: `pycontextfold[bench]`, `pycontextfold[pdf]`, `pycontextfold[agents]`.
- Cross-platform wheels (`maturin-action` in CI).
- Extend docs and CHANGELOG; cut a release.

## Explicit non-goals

- No re-implementation of sibling-project responsibilities (see the non-overlap
  contract in the assessment).
- No network or paid inference on the default path.
- No database or web frontend as a hard dependency.
