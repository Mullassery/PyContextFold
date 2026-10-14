# PyContextFold

**Local-first, structure-aware context optimization for LLM consumption.**

PyContextFold transforms source code, technical documentation, logs and
structured text into compact representations. It is a *transformation engine for
content you already have* — not an inference orchestrator, retrieval engine,
token-counting library, PDF processor, or agent framework.

The core is written in Rust. Python is a thin, typed interface over the same
native engine. There is also a standalone Rust library and CLI that do not
require Python at runtime.

```text
            ┌──────────────────────────────────────────────────────┐
   input    │  parse → transform → prune → validate → report        │   output
 ─────────► │              (contextfold-core, Rust)                 │ ─────────►
            └──────────────────────────────────────────────────────┘
                     ▲ Tree-sitter grammars (contextfold-parsers)
```

## What it owns (and what it deliberately does not)

**Owns:** content-aware parsing, structural transformations, redundancy
reduction, configurable preservation policies, budget-constrained folding,
validation of transformed output, and transformation reports.

**Does not own** (and never re-implements, imports, or depends on): provider
tokenization/cost (PyTokenCalc), context discovery/retrieval (PyStreamMCP),
inference orchestration (PyInferenceManager), PDF extraction (PyStreamPDF),
vector retrieval evaluation (PyVectorHound), agent tracing (PyAgentHound), or
OpenAnchor's token-intelligence middleware. Stable *interfaces* are exposed for
optional integration, but there are no cross-repository dependencies.

## Guarantees

- **Deterministic.** The same input, profile, engine version and registry
  produce byte-identical output.
- **Conservative by default.** The `safe` profile never removes executable
  statements, imports, conditions or error handling.
- **Honest about loss.** Lossy rules are labelled in the report. The engine
  **never claims semantic equivalence** — only, optionally, syntactic validity.
- **Local-first.** No network access. Source content is never logged by default.
- **Non-destructive.** Inputs are never overwritten unless you explicitly opt in
  (`--in-place`).

## Install

### Rust (library + CLI)

```bash
cargo build --release
# CLI binary at target/release/contextfold
cargo install --path crates/contextfold-cli
```

### Python

```bash
python -m venv .venv && source .venv/bin/activate
pip install maturin
maturin develop --release
# or build a wheel:
maturin build --release
```

Requires Python ≥ 3.10 (the wheel is built `abi3-py310`).

## Quick start

### CLI

```bash
# safe profile, stdin → stdout, JSON report to stderr
echo 'print("hi")  # comment' | contextfold -p safe
contextfold app.py -p safe --report report.json
contextfold app.py -p interface-only --allow-lossy
cat service.log | contextfold -p logs
```

### Python

```python
import pycontextfold as pcf

result = pcf.fold(source, profile="safe", path="app.py")
print(result.output)
print(result.report.reduction_ratio, result.report.syntax_valid)

# typed request object
req = pcf.FoldRequest(source, profile="interface-only", language="python")
res = pcf.Engine().fold_request(req)
```

## Profiles

| Profile          | Lossy | Summary |
|------------------|:-----:|---------|
| `safe`           | no    | Remove comments, collapse blank-line runs, trim trailing whitespace. Never removes code, imports, conditions or error handling. Docstrings preserved. |
| `code-review`    | no    | Preserve implementation logic **and** comments/docstrings; whitespace-only normalisation. |
| `interface-only` | yes   | Keep imports, declarations, signatures and docstrings; replace function bodies with valid placeholders. |
| `documentation`  | yes   | Reduce redundant Markdown/prose; preserve headings, code fences, links and normative keywords. |
| `logs`           | yes   | Collapse consecutive duplicate log events, retaining configured counts. |
| `budgeted`       | yes   | Aggressive deterministic ordering to reach a size/token budget. |

Profiles are versioned (`PROFILE_SCHEMA_VERSION`, surfaced in every report).
See [`docs/PROFILES.md`](docs/PROFILES.md) for per-profile guarantees.

## Token budgets

PyContextFold accepts a **target budget** but does not ship a provider
tokenizer catalogue. Supply a tokenizer implementing `count(text) -> int`
through the binding, or use byte/character budgets (clearly reported as
approximations, never as token counts):

```python
class MyTokenizer:
    name = "my-tok"
    def count(self, text: str) -> int:
        ...

req = pcf.FoldRequest(source, profile="budgeted",
                      budget_tokens=500, tokenizer=MyTokenizer())
res = pcf.Engine().fold_request(req)
```

When a budget cannot be met under the configured loss policy, the report
contains `warnings: ["budget_not_met"]`; the engine does not silently drop code.

## Architecture

```
crates/
  contextfold-core      transformation pipeline + public Rust API (no Tree-sitter)
  contextfold-parsers   Tree-sitter integration + format detection
  contextfold-cli       standalone CLI
  contextfold-py        PyO3 bindings (module: pycontextfold._core)
src/pycontextfold       Python package (thin re-export + typed surface)
tests/                  Python + preservation/integration tests
crates/*/tests          Rust unit/integration tests
benches/                reproducible benchmarks
docs/                   architecture, profiles, guarantees, limitations
```

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/PROFILES.md`](docs/PROFILES.md)
- [`docs/GUARANTEES.md`](docs/GUARANTEES.md)
- [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md)
- [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md)
- [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md)

## License

Apache-2.0.
