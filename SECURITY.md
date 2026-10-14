# Security Policy

## Scope

PyContextFold is an offline, local content-transformation engine. It performs no
network I/O, makes no model calls, and does not execute the content it processes.
It parses untrusted text with tree-sitter grammars and applies bounded,
deterministic edits.

Because it is not a security boundary, **do not** rely on it to remove secrets,
redact PII, sanitise untrusted code for execution, or enforce policy. See
`docs/GUARANTEES.md`.

## Reporting a vulnerability

If you believe you have found a security issue (for example, a parser panic or
unbounded memory growth on crafted input), please report it privately:

- Open a [GitHub security advisory](https://github.com/Mullassery/PyContextFold/security/advisories/new), or
- Email the maintainer at <mullassery@gmail.com>.

Please include a minimal reproducer (input bytes and the profile/options used).
Do not open a public issue for suspected vulnerabilities until a fix is
available.

## Supported versions

This project is pre-1.0; only the latest released version is supported with
security fixes.

## What we consider in scope

- Panics or aborts in any crate on arbitrary input.
- Unbounded memory or CPU growth (algorithmic denial of service) on crafted
  input.
- Memory-safety issues in the Rust core or the PyO3 boundary.

Crashes in third-party tree-sitter grammars are in scope for us to *contain*
(report a fallback rather than abort) and should also be reported upstream.
