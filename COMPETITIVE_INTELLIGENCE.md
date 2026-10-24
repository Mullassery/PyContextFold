# Competitive intelligence in roadmap and upgrade work

**Policy date:** 2026-10-19

Competitive findings are an input to product decisions, not a one-off report.
Every pending roadmap item, new feature, and routine dependency upgrade should
check the repository's [`AUDIT_FINDINGS.md`](AUDIT_FINDINGS.md) before work
starts, and record the decision in the PR or changelog.

## Required check before building

1. **Read `AUDIT_FINDINGS.md`.** Find the relevant competitor row and the
   ranked next actions. If the finding is stale, update it with a dated source.
2. **Name the competitor and the user problem.** A feature is not justified by
   "competitor has it". State the workflow it unlocks, who needs it, and how
   often. Mark unverified demand as a hypothesis.
3. **Prefer reuse over new code.** Check whether an existing Mullassery repo
   already provides the capability (see `BUNDLES.md` in the profile repo and
   the bundle role file in this repo, when present). Typical reuse:
   - crawling/fetching/robots/SSRF → **MudFish**
   - architecture maps / PR diffs → **CodeAtlas**
   - data-quality contracts / validation → **StatGuardian**
   - token counting / cost tables → **PyTokenCalc**
   - dependency graph / advisories / SBOM → **PyDeepMesh**
   - segmentation / CLV / churn → **ClusterAudienceKit**
   - activation / lineage / PII → **PyReverseETL**
   - fleet state sync → **SyncFleet** (only after conflict resolution)
4. **Choose one disposition:** build, integrate, defer, or reject. Write it
   down. A rejection with a reason is a successful outcome.
5. **For routine upgrades**, check whether the upgrade closes a known
   competitor gap or breaks a differentiated capability. Run the tests that
   cover the affected path; do not merge a green build that silently changes a
   user-visible contract.

## PR / changelog checklist

- [ ] Competitor and source URL/date recorded (or "no direct competitor").
- [ ] User impact and frequency stated; unverified demand labelled.
- [ ] Reuse check done against sibling repos/bundles.
- [ ] Failure mode and rollback considered (especially auth, PII, cost).
- [ ] Docs/roadmap status updated honestly.
- [ ] Tests or a manual verification command included.

## Review cadence

- Refresh the competitor row when a release changes the capability.
- Re-check the full `AUDIT_FINDINGS.md` at least quarterly and before a major
  release.
- If a finding is wrong or stale, correct it in the same PR that relies on it.

## Non-goals

- Copying features for parity.
- Adding a dependency just because a competitor uses it.
- Treating star counts or download counts as proof of user need.

## OSS gap analysis — 2026-10-24

**Scope.** Covers PyContextFold v0.1.3 as implemented here: Rust tree-sitter
folding for six languages, explicit preservation/loss profiles, token and byte
budgets, repository packing, manifests, the CLI, and an offline benchmark.
Compared with OSS context-compression and repository-packaging tools.

### Comparable OSS projects

| Project | License | Activity | Why comparable |
|---|---|---|---|
| LLMLingua | MIT | PyPI 0.2.2 (2024); repo active 2026 | Prompt compression, including budgeted compression |
| Repomix | MIT | 1.18.1, 2026-09-21 | Repository packaging for LLM context |
| code2prompt | MIT | 4.3.0, docs.rs 2026-10-23 | Codebase-to-prompt generation with templates |
| gitingest | MIT | 0.3.1, 2025-07-31; repo 2026-10-24 | Repository ingestion into prompt-friendly text |

### Capability comparison

| Capability | PyContextFold | LLMLingua | Repomix | code2prompt | gitingest |
|---|---|---|---|---|---|
| AST-aware structural folding | Yes | No | Partial | No | No |
| Language-aware parsing | Partial | No | Partial | No | No |
| Repository packing | Yes | No | Yes | Yes | Yes |
| Ignore rules and binary skipping | Yes | No | Yes | Yes | Yes |
| Token-budget targeting | Yes | Yes | Partial | Partial | No |
| Behavior-preserving mode | Yes | No | Partial | No | No |
| Manifest or transformation report | Yes | No | Yes | Partial | Partial |
| Remote repository ingestion | No | No | Yes | Yes | Yes |
| CLI | Yes | No | Yes | Yes | Yes |

"Partial": Repomix's tree-sitter compression is optional and narrower; its
budget targeting was not verified. code2prompt counts output tokens but does not
fold structurally. gitingest packages text without AST analysis. PyContextFold
returns unsupported files unchanged rather than guessing at them.

### Gaps that matter (ranked)

1. **Language coverage is deliberately narrow.** Six analyzers, with unsupported
   files unchanged, means little reduction on Java, C/C++, C#, Ruby, PHP, Kotlin,
   or Swift. Add analyzers in demand order and make unsupported coverage visible.

2. **No remote repository ingestion.** `pack_repository` walks a local path;
   Repomix, code2prompt, and gitingest accept remote repositories. This is a
   distribution gap. Integrate a hardened fetcher (or reuse MudFish/gitingest)
   rather than writing clone, auth, and SSRF handling here.

3. **Benchmark evidence is synthetic and self-referential.** The offline harness
   is a start, but uses a synthetic dataset and in-repo adapters. Build a public,
   reproducible benchmark reporting token reduction and ground-truth preservation
   against Repomix and LLMLingua on pinned inputs.

4. **Exact token budgets need optional tokenizer adapters.** Model-specific
   budgets require `[tiktoken]`, `[hf]`, or a caller-supplied tokenizer; a plain
   install cannot verify exact model tokens. Keep the byte-budget fallback, but
   warn explicitly when "tokens" are approximate and show the tokenizer used in
   the report.

5. **Documentation and log folding are adjacency heuristics.** Markdown dedupe
   removes adjacent duplicate lines, and log collapsing groups normalized
   repeated events. They do not understand semantics, so near-duplicates survive
   and genuinely repeated normative text can be at risk. Keep these lossy
   profiles opt-in and document the limits rather than adding an opaque model.

### Where we are differentiated

- Folding is AST-aware and deterministic, with a behavior-preserving default and
  named loss policies instead of token-level truncation.
- Unmet budgets produce an explicit `budget_not_met` warning; code is never
  silently dropped.
- Repository packing honors `.gitignore`, `.contextfoldignore`, and binary/size
  limits, and emits a byte-identical manifest plus token counts.
- The Rust core runs locally and offline, with no model or network dependency.

### Disposition

- **Build:** analyzers for the next demanded languages; a public benchmark with
  pinned corpora and competitor baselines; explicit approximate-token warnings.
- **Integrate/reuse:** MudFish or gitingest for remote ingestion; PyTokenCalc
  for model tokenizers and cost-aware budgeting; optional LLMLingua as a lossy
  prose pass after structural folding, never as the default.
- **Defer/reject:** semantic dedupe, lossy-by-default compression, and a hosted
  context service. The defensible wedge is conservative, reviewable folding.

### Sources

- LLMLingua: https://github.com/microsoft/LLMLingua (MIT; PyPI 0.2.2, 2024).
- Repomix: https://github.com/yamadashy/repomix (MIT; 1.18.1, 2026-09-21).
- code2prompt: https://github.com/mufeedvh/code2prompt (MIT; 4.3.0, 2026-10-23).
- gitingest: https://github.com/coderamp-labs/gitingest (MIT; 0.3.1, 2025-07-31).
- Local: `README.md`, `docs/PROFILES.md`, `crates/contextfold-core/src/`,
  `crates/contextfold-cli/src/main.rs`.
