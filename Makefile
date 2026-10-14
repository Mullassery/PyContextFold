# PyContextFold developer tasks.
#
# Usage: `make <target>`. Requires a Rust toolchain (`rustup`), and for the
# Python targets a virtual environment with `maturin` and `pytest` installed.

PYTHON ?= python3
VENV ?= .venv
CARGO ?= cargo

.PHONY: help build test check fmt clippy lint bench python-dev python-test python-lint docs clean

help: ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

build: ## Build all Rust crates (debug).
	$(CARGO) build --workspace

test: ## Run the full Rust test suite.
	$(CARGO) test --workspace

check: ## Type-check the whole workspace.
	$(CARGO) check --workspace --all-targets

fmt: ## Format Rust sources.
	$(CARGO) fmt --all

clippy: ## Run clippy with warnings denied.
	$(CARGO) clippy --workspace --all-targets -- -D warnings

lint: fmt clippy ## Format and lint.
	$(CARGO) fmt --all -- --check

bench: ## Run the criterion benchmarks (text output only).
	$(CARGO) bench -p contextfold-bench -- --noplot

python-dev: ## Build and install the Python extension into $(VENV) (editable).
	$(VENV)/bin/maturin develop -m crates/contextfold-py/Cargo.toml

python-test: ## Run the Python test suite.
	$(VENV)/bin/python -m pytest tests/ -q

python-lint: ## Lint the Python package.
	$(VENV)/bin/ruff check src tests

docs: ## Build the Rust API docs.
	$(CARGO) doc --workspace --no-deps

clean: ## Remove build artefacts.
	$(CARGO) clean
	rm -rf dist
