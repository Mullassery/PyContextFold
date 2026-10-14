# Integrations

PyContextFold is designed to be a drop-in pre-processing step in a local LLM
pipeline. It has no required dependencies and no network surface, so it composes
with whatever prompt-assembly, token-accounting or agent framework you already
use.

## Python

Install (from the repository):

```bash
python -m venv .venv && source .venv/bin/activate
pip install maturin
maturin develop -m crates/contextfold-py/Cargo.toml   # editable build
```

The convenience API:

```python
import pycontextfold as pcf

result = pcf.fold(source, profile="safe", path="app.py")
print(result.output)
print(result.report.detected_language)     # "python"
print(result.report.reduction_ratio)       # e.g. 0.19
print(result.report.to_dict())             # serialisable report
print(result.report.to_json())
```

Fold a file without ever modifying it:

```python
result = pcf.fold_file("app.py", profile="code-review")
open("app.folded.py", "w").write(result.output)
```

Introspection:

```python
pcf.profiles()                 # ['budgeted', 'code-review', ...]
pcf.profile_info("safe")       # {name, description, loss, ...}
pcf.supported_languages()      # [...]
pcf.detect_language("fn main() {}", path="a.rs")   # "rust"
```

For full control (tokenizer, budgets, protection) build a request and drive an
`Engine`:

```python
class WhitespaceTokenizer:
    name = "whitespace"
    def count(self, text: str) -> int:
        return len(text.split())

engine = pcf.Engine()
req = pcf.FoldRequest(
    source,
    profile="budgeted",
    language="python",
    budget_tokens=4000,
    tokenizer=WhitespaceTokenizer(),
    protected_line_markers=["contextfold:keep", "SPDX-License-Identifier"],
)
res = engine.fold_request(req)
assert res.report.to_dict()["budget"]["exact_tokens"] is True
```

Errors are typed: `UnknownProfileError`, `InvalidConfigError`,
`BudgetNotMetError`, all subclasses of `ContextFoldError`.

### Feeding a prompt pipeline

A typical integration folds each file just before assembling a prompt and reads
the report to decide whether the reduction was sufficient:

```python
def fold_for_prompt(path: str, budget: int) -> tuple[str, dict]:
    res = pcf.fold(
        open(path).read(),
        profile="safe",          # start conservative
        path=path,
        budget_bytes=budget,
    )
    report = res.report.to_dict()
    if not report["budget"]["met"]:
        # escalate to a lossy profile only when we must
        res = pcf.fold(open(path).read(), profile="budgeted", path=path,
                       budget_bytes=budget)
        report = res.report.to_dict()
    return res.output, report
```

Because `safe` is non-lossy and `budgeted` is explicitly lossy, the escalation is
visible in the report (`behavior_preserving: false`, `lossy` rules, warnings).

## CLI

The `contextfold` binary reads files or stdin and writes to stdout unless told
otherwise:

```bash
# stdin -> stdout
cat app.py | contextfold -p safe -L python

# file -> stdout, with a JSON report
contextfold -p interface-only --report report.json app.py > app.iface.py

# many files -> a directory
contextfold -p safe --output-dir folded/ src/**/*.py

# overwrite in place (explicit opt-in only)
contextfold -p safe --in-place app.py

# reach a byte budget, allowing lossy rules
contextfold -p budgeted --budget-bytes 8192 --allow-lossy big.log
```

Flags: `-p/--profile`, `-L/--language`, `-o/--output`, `--output-dir`,
`--in-place`, `--report <file>`, `--budget-bytes`, `--budget-chars`,
`--allow-lossy`, `-q/--quiet`.

## Rust

```toml
[dependencies]
contextfold-core = { path = "crates/contextfold-core" }
contextfold-parsers = { path = "crates/contextfold-parsers" }
```

```rust
use contextfold_core::model::FoldRequest;
use contextfold_parsers::standard_engine;

let engine = standard_engine();
let request = FoldRequest::new(source)
    .with_path("app.py")
    .with_profile("safe")
    .with_budget(contextfold_core::Budget::bytes(8192));
let result = engine.fold(request)?;
println!("{}", result.report.semantic_equivalence); // "not_guaranteed"
```

To add a language, implement `contextfold_core::LanguageAnalyzer` and register it
with `Registry::register`; the rest of the pipeline (profiles, edits, budgets,
reports) is reused unchanged. `contextfold-core` never depends on tree-sitter.

## Interoperability notes

- **Token accounting.** PyContextFold measures bytes/chars exactly and tokens only
  through a caller-supplied `Tokenizer`. If you already have a tokenizer (for the
  model you will actually use), implement `count(text) -> int` and pass it in —
  the engine will then report `exact_tokens: true`. This keeps PyContextFold
  honest and decoupled from any specific model vocabulary.
- **Determinism.** Output is deterministic, which makes it safe to cache folded
  results keyed by `(content hash, profile, options)`.
- **Comparison.** Because reports are structured, folded variants are easy to
  compare in a benchmark harness: keep `reduction_ratio`, `behavior_preserving`,
  `parse_status` and per-rule `RuleRecord`s.
