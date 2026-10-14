# Guarantees

These are the properties PyContextFold aims to uphold. They are stated as
testable claims and are covered by unit, integration and property tests.

## Guarantees

1. **Local and offline.** No network access, no telemetry, no model calls. The
   crate graph contains no HTTP client.

2. **Deterministic.** The same input, profile and options yield byte-identical
   output and an equal report. (Property test: `transform_is_deterministic`.)

3. **Conservative on parse failure.** If an input does not parse cleanly, the
   engine makes **no** changes: the output equals the input byte-for-byte, the
   report status is `parse_failed`, and a `parse_failed` warning is emitted.

4. **No silent lossy transformations.** A rule that is explicitly lossy runs only
   when the profile's loss policy allows it. Otherwise it is skipped and a
   `lossy_rule_blocked` warning is recorded. Lossy profiles are named `LOSSY` and
   set `behavior_preserving: false`.

5. **Never silent.** Every transformation is reported: per-rule application
   counts and bytes removed are always available, as are input/output sizes and
   `protected_bytes`.

6. **Protection is honoured.** Protected ranges, marker lines, imports (when
   enabled) and error handling (when enabled) are never modified by any rule.
   (Tests: `protected_marker_line_survives`, `protected_ranges_are_respected`.)

7. **No overclaiming of equivalence.** `semantic_equivalence` is always the
   string `"not_guaranteed"`. The engine never claims behaviour preservation for
   lossy profiles, and `behavior_preserving` is `false` whenever a lossy rule is
   applied.

8. **Honest accounting.** Byte and character counts are exact. A token count is
   reported only when the caller supplies a `Tokenizer`; otherwise
   `exact_tokens` is `false`. Byte counts are never relabelled as tokens.

9. **Inputs are not modified unless asked.** `fold` and `fold_file` never write
   to their inputs. The CLI overwrites a file only with `--in-place`.

10. **Syntax remains valid when a profile claims it.** For `safe` and
    `interface-only`, code output is re-parseable; the report's `syntax_valid`
    is `true`. Docstring decoders and comments are handled so that removal does
    not strand delimiters.

11. **Bounded, non-pathological performance.** The transformation pipeline is
    effectively linear in input size for the supported languages (see
    `BENCHMARKS.md`); protection checks use a merged interval index rather than a
    linear scan.

## Non-guarantees

- **Semantic equivalence.** PyContextFold performs *structural* reduction. It
  does not execute, type-check or formally verify code and makes no claim that
  the transformed text means the same thing to a reader or a model. In
  particular, comment removal can delete information that only exists in
  comments, and `interface-only` deletes implementation bodies outright.
- **Token-exact budgets without a tokenizer.** Token counts are only as accurate
  as the tokenizer you provide.
- **Full-fidelity parsing of every language feature.** See `LIMITATIONS.md`.
- **Reversibility.** Folding is lossy by design for several profiles and is not
  an invertible encoding.
- **This is not a security boundary.** Do not rely on PyContextFold to remove
  secrets, redact PII or enforce policy. It is a context-size tool.
