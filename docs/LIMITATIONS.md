# Limitations

PyContextFold is deliberately conservative, but it is not magic. Known
limitations, in roughly descending order of how likely you are to hit them:

## Language coverage

- **Supported code languages**: Python, Rust, JavaScript, TypeScript, TSX and Go,
  via tree-sitter grammars. Detection also recognises Markdown, log files, JSON
  and plain text.
- Everything else is treated as unsupported: the input is returned unchanged
  with an `unsupported` (or `fallback`) status and a warning. There is no
  best-effort regex parser for unknown languages.
- Grammar versions are pinned; constructs introduced after those versions may
  parse with errors, which triggers the conservative no-op fallback rather than a
  partial transformation.

## Parser behaviour

- A file that only *partially* parses is treated as a parse failure for the
  *whole* file: the engine refuses to transform it. This trades reduction for
  safety.
- Tree-sitter is error-tolerant, so "parses successfully" means "the grammar
  produced a tree", not "the code is valid". `syntax_valid` reflects a re-parse
  of the output, not a compiler.

## Transformation semantics

- **Comments may carry meaning.** The `safe` profile removes comments. Tools that
  rely on comments (type pragmas, linter directives, `# noqa`, `// nolint`,
  docstring-based test discovery, license headers) can be affected. Protect the
  relevant lines with a marker, a `protected_range`, or use `code-review`.
- **Docstrings.** Preserved in `safe`/`code-review`/`interface-only`; removed only
  by `budgeted` (or an explicit override). When removed, framework behaviour that
  reads docstrings at runtime is not modelled.
- **`interface-only` is lossy and heuristic.** It replaces bodies with
  placeholders. It does not understand decorators, abstract methods, generators
  or type-only bodies and may elide a body you wanted. Protected ranges should be
  used selectively.
- **Markdown dedupe is adjacency-based.** Only *adjacent* duplicate lines are
  removed. Repeated paragraphs separated by other content are left in place to
  avoid deleting structure.
- **Log collapsing uses normalised keys.** Two log lines are "repeats" when
  timestamps, durations, hex ids and addresses are normalised away. This can
  merge lines you considered distinct, and it never merges lines with different
  messages.
- **JSON is not semantically transformed.** The `safe` profile only removes
  insignificant whitespace (minifies). Key order is preserved; nothing is
  reordered or deduplicated.

## Budgets and tokens

- Byte and character budgets are exact. Token budgets require a caller-supplied
  `Tokenizer`; without one, no token count is produced.
- The engine does **not** ship or bundle a model tokenizer, and it does not know
  about chat-template overhead, special tokens or per-message framing.
- `budgeted` reaches a budget by applying a fixed sequence of rules; it does not
  guarantee a specific numeric target and may report `budget_not_met`.

## Platform / packaging

- The `contextfold-py` crate is an `extension-module`; it cannot be built with a
  plain `cargo build` on macOS/Linux. Use `maturin develop` / `maturin build`, or
  `cargo check` for type-checking only.
- Wheels are abi3 (`abi3-py310`), built for CPython 3.10+. The Rust library and
  CLI have no Python dependency.

## Non-goals

- No semantic equivalence guarantee, no secret/PII redaction, no policy
  enforcement, no network service, no bundled model, no file watching, no
  streaming parser. See `GUARANTEES.md` for the full non-goals list.
