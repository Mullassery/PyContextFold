# PyContextFold

[![PyPI](https://img.shields.io/pypi/v/pycontextfold.svg)](https://pypi.org/project/pycontextfold/)
[![Python versions](https://img.shields.io/pypi/pyversions/pycontextfold.svg)](https://pypi.org/project/pycontextfold/)
[![CI](https://github.com/Mullassery/PyContextFold/actions/workflows/tests.yml/badge.svg)](https://github.com/Mullassery/PyContextFold/actions/workflows/tests.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

**A Python library for structure-aware context optimization for LLM consumption.**

PyContextFold shrinks source code, technical documentation, logs and structured
text before you send them to an LLM — cutting token cost while keeping every
transformation explicit, configurable and reportable. It is a local-first
`pip install` with a fast, deterministic Rust core underneath, and it never
sends your content anywhere.

It is a *transformation engine for content you already have* — not an inference
orchestrator, retrieval engine, token-counting library, PDF processor, or agent
framework.

## Install

```bash
pip install pycontextfold
```

Requires Python ≥ 3.10 (the wheel is built `abi3-py310`). The core, the CLI and
the offline benchmark need nothing else. Optional ecosystem adapters activate
when their project is importable; install them individually, e.g.
`pip install "pycontextfold[tokens]"`, `[pdf]`, `[agents]`, or `[ecosystem]` for
all of them.

## Quick start

```python
import pycontextfold as pcf

result = pcf.fold(source, profile="safe", path="app.py")
print(result.output)                       # transformed text
print(result.report.detected_language)     # "python"
print(result.report.reduction_ratio)       # e.g. 0.19
print(result.report.syntax_valid)          # True
print(result.report.to_dict())             # serialisable report
```

Fold a file without ever modifying it:

```python
result = pcf.fold_file("app.py", profile="code-review")
open("app.folded.py", "w").write(result.output)
```

Introspection and full control:

```python
pcf.profiles()                  # ['budgeted', 'code-review', ...]
pcf.profile_info("safe")        # {name, description, loss, ...}
pcf.supported_languages()       # [...]
pcf.detect_language("fn main() {}", path="a.rs")   # "rust"

# Typed request object with budgets, protection and a caller-supplied tokenizer
req = pcf.FoldRequest(
    source,
    profile="budgeted",
    language="python",
    budget_bytes=4096,
    protected_ranges=[(0, 128)],          # keep the license header
    protected_line_markers=["contextfold:keep"],
)
res = pcf.Engine().fold_request(req)
```

Errors are typed — `UnknownProfileError`, `InvalidConfigError`,
`BudgetNotMetError` — all subclasses of `ContextFoldError`.

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
- **Non-destructive.** Inputs are never overwritten unless you explicitly opt in.

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
tokenizer catalogue. Supply a tokenizer implementing `count(text) -> int`, or
use byte/character budgets (clearly reported as approximations, never as token
counts):

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

## Benchmarking (offline, dependency-light)

The `pycontextfold.bench` subpackage measures the trade-offs of folding: how much
is removed (size/character/token reduction) versus how much matters (ground-truth
preservation). It runs with nothing else installed and never touches the network.

```python
from pycontextfold import bench

ds = bench.dataset.synthetic_dataset()
reg = bench.adapters.default_registry()
adapter = reg.get("contextfold")

for doc in ds:
    result = adapter.optimize(bench.OptimizationRequest(doc, method="safe"))
    metrics = bench.metrics.document_metrics(doc, result, ds.ground_truth_for(doc.id))
    print(doc.id, {m.name: round(m.value, 3) for m in metrics if m.available})
```

Optional ecosystem adapters (PyTokenCalc, PyStreamPDF, PyVectorHound, ...) are
capability-declared and imported lazily; a requested-but-missing capability is
reported as *unavailable* rather than silently substituted. See
[`docs/ROADMAP.md`](docs/ROADMAP.md) and
[`docs/ECOSYSTEM_ASSESSMENT.md`](docs/ECOSYSTEM_ASSESSMENT.md).

Run a whole experiment and emit a single-file HTML report (no CDN, fully
offline):

```python
from pycontextfold import bench

run = bench.run_experiment(
    bench.dataset.synthetic_dataset(),
    bench.ExperimentConfig(name="demo", dataset="synthetic",
                           adapters=("baseline", "contextfold")),
)
bench.write_report(run, "report.html")   # self-contained, deterministic
```

There is also a CLI (offline, stdlib only):

```bash
pycontextfold-bench adapters                                  # list + availability
pycontextfold-bench run --config exp.json --report report.html
pycontextfold-bench run --config exp.json --gate              # exit 1 on gate failure
pycontextfold-bench report run.json --out report.html
```

Gates turn a run into a regression check — an aggregated metric below its
threshold, or an unavailable metric, fails the run.

## Command-line tool (optional)

Installing the package gives you the Python library. The repository also ships a
standalone `contextfold` CLI and a Rust library for non-Python use:

```bash
cargo install --path crates/contextfold-cli
echo 'print("hi")  # comment' | contextfold -p safe
contextfold app.py -p safe --report report.json
```

## Architecture

```
src/pycontextfold       Python package (public, typed API)
src/pycontextfold/bench offline benchmarking platform (adapters, runner, report, gates, CLI)
crates/
  contextfold-core      transformation pipeline (no Tree-sitter)
  contextfold-parsers   Tree-sitter integration + format detection
  contextfold-cli       standalone CLI
  contextfold-py        PyO3 bindings (module: pycontextfold._core)
tests/                  Python + preservation/integration tests
tests/bench             benchmarking platform tests
crates/*/tests          Rust unit/integration tests
benches/                reproducible benchmarks
docs/                   architecture, profiles, guarantees, limitations
```

Python is the primary interface; the Rust core exists for speed, memory safety
and determinism. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Known issues and deferred work

**Blocked / failed:**
- Benchmark vs LLMLingua/Repomix with quality retention.

**Rejected / deferred:**
- Model inference/routing.

Full shipped/blocked/rejected detail: [`QUEUE_STATUS.md`](QUEUE_STATUS.md).

## Queue status

Shipped, blocked/failed, and rejected work for this repository is documented in
[`QUEUE_STATUS.md`](QUEUE_STATUS.md).

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/PROFILES.md`](docs/PROFILES.md)
- [`docs/GUARANTEES.md`](docs/GUARANTEES.md)
- [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md)
- [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md)
- [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md)
- [`docs/BENCHMARKING.md`](docs/BENCHMARKING.md)
- [`docs/ECOSYSTEM_ASSESSMENT.md`](docs/ECOSYSTEM_ASSESSMENT.md)
- [`docs/ROADMAP.md`](docs/ROADMAP.md)

## License

Apache-2.0.
