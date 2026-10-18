# Audit findings — 2026-10-19

This file records the repository-specific findings from the portfolio audit
conducted on 2026-10-19. It is documentation only; no code or release artifacts
were changed in this pass unless explicitly noted under "Implementation status".

Sources: the repository's own README/source/workflows, GitHub metadata and
Actions runs, PyPI metadata, and official competitor documentation. Claims are
marked as verified, inferred, or open questions. "Absent" means not found in the
inspected repository/docs, not proof that it cannot exist.

## What it is

Structure-aware context optimization for LLM consumption: deterministic folding of code/docs/logs with explicit, reportable loss and token budgets.

## Verified strengths

- Rust core; deterministic; `safe` profile never removes executable code; loss reporting; `budget_not_met`; offline benchmark harness; CLI; 25 tests; fuzz target.
- Good scope discipline: no inference/provider routing.

## Verified gaps and user-facing risks

- No published benchmark against LLMLingua/Repomix; quality retention unproven; macOS arm64 wheel only.
- Very young; few integrations.

## Direct competitors

- LLMLingua (research-backed prompt compression, LangChain/LlamaIndex), Repomix (codebase packing), code2prompt/gitingest.

## Ranked next actions

- P1: benchmark vs LLMLingua/Repomix with answer-quality retention (M).
- P2: LangChain/LlamaIndex adapters (M).

## Do not build

- Model inference or provider routing; out of scope by design.

## Evidence gaps / validation needed

- No end-to-end quality measurement; no large-repo corpus.

## Recommended disposition

Maintain as a focused utility; the benchmark is the adoption gate.

## Implementation status

No code changes in this pass.
