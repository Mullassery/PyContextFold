# Profiles

A **profile** is a named, versioned bundle of rules plus preservation and loss
policies. Profiles make the trade-off between size reduction and information
loss explicit and reviewable. The built-in profiles are intentionally
conservative; lossy behaviour only ever happens when it is named.

## Built-in profiles

| Profile | Lossy | Comments | Docstrings | Blank lines | Extra rules |
|---|---|---|---|---|---|
| `safe` | no | remove | **preserved** | collapse runs → 1 | — |
| `code-review` | no | keep | preserved | collapse runs → 1 | — |
| `interface-only` | **yes** | keep | preserved | collapse runs → 1 | replace function/method bodies with valid placeholders |
| `documentation` | **yes** | keep | preserved | collapse runs → 1 | Markdown: remove adjacent duplicate lines |
| `logs` | **yes** | keep | preserved | collapse runs → 1 | collapse consecutive duplicate log events (retain 1) + marker |
| `budgeted` | **yes** | remove | remove | remove all | log collapsing + Markdown dedupe |

All profiles trim trailing whitespace (Markdown profiles preserve hard line
breaks of two or more spaces and never touch fenced code blocks).

### `safe` — the default

Removes comments, collapses runs of blank lines to a single blank line and trims
trailing whitespace. Executable statements, imports, conditionals, loops and
error handling are **never** removed. Docstrings are deliberately preserved: they
are the highest-value in-file documentation and removing them is what makes the
other profiles lossy.

### `code-review`

Keeps every comment and docstring; only normalises whitespace. Use it when a
reviewer wants the original intent, but compressed vertically.

### `interface-only`

Keeps imports, declarations, signatures and docstrings and replaces implementation
bodies with the language-appropriate placeholder:

- Python: `...  # [contextfold: implementation omitted]`
- Brace languages (Rust/JS/TS/TSX/Go): `{ /* [contextfold: implementation omitted] */ }`

Bodies that contain protected error handling (when `protect_error_handling` is
on, the default) or that overlap a protected range are left intact. The result is
still parseable (`syntax_valid: true`) but **not** behaviour-preserving — the
report sets `behavior_preserving: false`.

### `documentation`

Markdown/prose reduction. Preserves headings, fenced code blocks, links, block
quotes and any line containing a normative keyword (`must`, `should`, `required`,
…). Removes *adjacent* duplicate lines and normalises blank lines. Duplicate
lines separated by other content are intentionally **not** removed.

### `logs`

Collapses runs of consecutive duplicate log events, keeping one copy and emitting
`[contextfold: N repeated log line(s) collapsed]`. Two log lines are "duplicates"
when their normalised keys (timestamps, durations, hex ids, addresses replaced)
match. Distinct events are never merged.

### `budgeted`

The aggressive profile: removes comments and docstrings, removes all blank lines,
and applies log/Markdown reductions, in a fixed deterministic order. Intended to
be paired with a byte/character/token budget.

## Overrides

The Python surface lets you choose a profile and adjust preservation/budget
options per call, without defining a new profile:

```python
import pycontextfold as pcf

engine = pcf.Engine()
req = pcf.FoldRequest(
    source,
    profile="safe",
    path="module.py",
    budget_bytes=4096,                        # byte/char budgets are exact
    protected_ranges=[(0, 128)],              # keep the license header
    protected_line_markers=["contextfold:keep", "generated"],
)
res = engine.fold_request(req)
print(res.report.to_dict())
```

The convenience function `pcf.fold(...)` accepts the same profile, path,
language, `allow_lossy`, `budget_bytes`, `budget_chars`, `protected_ranges` and
`protected_line_markers` options.

In Rust use `Profile::named_with_overrides(name, ProfileOverrides { .. })`, which
also lets you override individual **rules** (`comments`, `docstrings`,
`blank_lines`, `trim_trailing_whitespace`, `interface_only`,
`collapse_log_repeats`, `markdown_dedupe`) in addition to the preservation
settings (`protect_imports`, `protect_error_handling`, `protected_ranges`,
`protected_line_markers`).

## Custom profiles

Because `Profile` is a plain serialisable struct, applications can load their own
from JSON/TOML and pass them to the engine. A custom profile should set
`loss.allow_lossy = true` explicitly if it enables any lossy rule; otherwise the
rule is blocked and a `lossy_rule_blocked` warning is emitted.

## Protection

Independently of the profile, spans can be protected from every transformation:

- **Caller ranges** — exact byte spans via `protected_ranges`.
- **Marker lines** — any line containing a configured marker substring
  (default: `contextfold:keep`, `@contextfold-keep`) is kept verbatim.
- **Imports** — protected when `protect_imports` is true.
- **Error handling** — protected when `protect_error_handling` is true.

`report.protected_bytes` reports how many bytes were protected.
