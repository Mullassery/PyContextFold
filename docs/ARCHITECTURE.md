# Architecture

PyContextFold is a **local-first, deterministic** context-optimization engine. It
reduces the size of source code, documentation, logs and structured text before
that text is handed to an LLM, while making every transformation explicit,
reportable and configurable.

It exists for two audiences and ships one core:

- A **Rust library + CLI** (`contextfold-core`, `contextfold-parsers`,
  `contextfold-cli`).
- A **Python package** (`pycontextfold`) built with PyO3/maturin.

Nothing leaves the machine. There is no network access, no telemetry and no
model dependency.

## Crate layering

```text
        ┌──────────────────────────┐     ┌───────────────────────────┐
        │  contextfold-cli         │     │  contextfold-py (PyO3)    │
        │  clap binary `contextfold`│    │  module `pycontextfold._core`│
        └────────────┬─────────────┘     └─────────────┬─────────────┘
                     │                                   │
                     └───────────────┬───────────────────┘
                                     ▼
                          ┌───────────────────────┐
                          │  contextfold-parsers  │   tree-sitter analyzers
                          │  (tree-sitter 0.25)   │   Python/Rust/JS/TS/TSX/Go
                          └───────────┬───────────┘
                                      ▼
                          ┌───────────────────────┐
                          │   contextfold-core    │   NO tree-sitter dependency
                          │  engine · profiles ·  │
                          │  edits · budgets ·    │
                          │  reports              │
                          └───────────────────────┘
```

The boundaries are deliberate and enforced by dependency direction:

- **`contextfold-core`** owns the domain model: language detection, the profile
  and rule system, edit algebra, the offset map, budget accounting, the report
  schema and validation. It depends on **no parser**; it defines the
  `LanguageAnalyzer` trait and consumes implementations of it.
- **`contextfold-parsers`** depends on core and provides tree-sitter-backed
  `LanguageAnalyzer` implementations plus `standard_registry()` /
  `standard_engine()`.
- **`contextfold-cli`** and **`contextfold-py`** depend on both and contain no
  transformation logic of their own.

This means the core can be unit-tested and property-tested without any grammar,
and new languages can be added by implementing one trait.

## The fold pipeline

`Engine::fold(FoldRequest)` runs a fixed, deterministic pipeline:

1. **Detect language** — explicit `language` wins; otherwise file extension;
   otherwise conservative content heuristics (`parse_detection`).
2. **Parse** — the registered analyzer produces an `Analysis` (comment spans,
   docstring spans, string spans, import spans, error-handling spans and
   declarations with body spans). A parse failure is **not** fatal: it becomes a
   `ParseFailed` status and the input is returned byte-for-byte with a warning.
3. **Build protected ranges** — caller-supplied ranges plus whole lines
   containing any configured marker substring (default
   `contextfold:keep`, `@contextfold-keep`).
4. **Apply structure edits** — per the profile: comment removal, docstring
   removal, interface-only body elision. Every candidate is skipped when it
   overlaps a protected range, an import (if `protect_imports`), error handling
   (if `protect_error_handling`) or a string literal.
5. **Apply whitespace edits** — trailing-whitespace trimming and blank-line
   policy, line-oriented and string/heredoc-aware.
6. **Account** — record each rule's applied count and bytes removed, compute the
   offset map, gather warnings, and measure the output against the optional
   budget.

Two-stage application matters: structure edits can move text, so whitespace
edits are computed against the *already-transformed* text (re-analysed when the
structure stage changed anything) and merged through the same offset map so byte
accounting stays correct.

### Edit algebra (`transform::edit`)

All transformations are expressed as `Edit { span, replacement, rule }` values
over the original bytes and applied left-to-right:

- `apply_edits` sorts by start offset, drops edits that overlap an
  already-committed edit (deterministically, earlier start wins), validates
  character boundaries, and returns an `ApplyOutcome` with the resulting text, a
  count of applied and dropped edits, bytes removed and an `OffsetMap`.
- `OffsetMap` maps original offsets to new offsets (`map`, `map_span`) so that
  protection ranges computed on the original source survive re-analysis.
- `overlaps_sorted` performs `O(log n)` protected-range checks against a merged,
  sorted span set, keeping the pipeline linear in input size.

### Model & report (`model.rs`)

`FoldResult` is `{ output, report }`. `Report` is deliberately explicit and
serialisable:

- `engine_version`, `profile`, `profile_version`, `profile_schema_version`
- `detected_language`, `parse_status` (`parsed` / `parse_failed` /
  `unsupported` / `fallback`)
- `behavior_preserving`, `semantic_equivalence` (**always**
  `"not_guaranteed"`), `syntax_valid`
- `input` / `output` `SizeStats` (bytes, chars, lines) and `reduction_ratio`
- per-rule `RuleRecord`s (rule id, human name, application count, bytes removed,
  lossy flag, description)
- `warnings` (e.g. `parse_failed`, `budget_not_met`, `lossy_rule_blocked`)
- optional `budget` report and `protected_bytes`

## Budgets

`Budget::bytes`, `Budget::characters` or `Budget::tokens`. Byte/character budgets
are exact and always available. A **token** budget requires a caller-supplied
`Tokenizer` (core ships the trait, never a specific model tokenizer), so the
engine reports `exact_tokens: true` only when one was provided and **never**
misreports byte counts as tokens.

## Determinism

Given the same input, profile and options, the output and report are identical.
Spans are sorted, edits are resolved by a total order, and no randomness,
hashing-order or time-dependence enters the pipeline. This is asserted by
property tests.
