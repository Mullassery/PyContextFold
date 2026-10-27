# Contributing

Thanks for your interest in PyContextFold. This project values **explicit,
minimal, well-tested** changes.

## Getting started

```bash
git clone ../PyContextFold
cd PyContextFold
cargo test --workspace            # Rust unit + integration + property tests

python -m venv .venv && source .venv/bin/activate
pip install maturin pytest
maturin develop -m crates/contextfold-py/Cargo.toml
python -m pytest tests/ -q        # Python tests
```

`make help` lists the common tasks.

## Before you commit

Run the same checks CI runs:

```bash
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

## Design principles

- **Explicitness over cleverness.** Transformations are `Edit` values with a
  `RuleId`; every change is accounted for in the report.
- **No silent loss.** Lossy rules require `loss.allow_lossy`; otherwise they are
  blocked with a warning.
- **Conservative on doubt.** If parsing fails or a span is protected, do nothing.
- **Determinism.** Never introduce iteration-order, time or randomness
  dependence.
- **Respect the crate boundaries.** `contextfold-core` must not gain a
  tree-sitter dependency; analyzers live in `contextfold-parsers`.
- **No cross-repository dependencies.** Do not import sibling tools' internals.

## Adding a language

1. Add a grammar dependency and a `LangSpec` in `contextfold-parsers`.
2. Register the analyzer in `standard_registry()`.
3. Add a fixture under `tests/fixtures/` and cover `safe` (syntax valid, comments
   removed) and `interface-only` (bodies elided, still parseable).
4. Update `docs/` and the supported-language list.

## Pull requests

- Keep PRs focused; one logical change each.
- Include tests for new behaviour and a changelog entry under `[Unreleased]`.
- Describe the behaviour change and any new guarantees or limitations.

By contributing you agree that your contributions are licensed under the
project's Apache-2.0 license.
