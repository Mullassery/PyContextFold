# Ecosystem assessment (Phase 0)

This document records what PyContextFold can rely on from the nine sibling
projects that share its author and problem space, and — just as importantly —
what it must **not** re-implement. It is the output of reading the *local*
checkouts under `~/Desktop/Projects/` (source only; nothing was installed or
executed from those repositories).

The guiding rule: **PyContextFold's core never depends on any of these
projects.** Each adapter is optional, capability-declared, and checked before an
experiment runs. If a capability is missing, the affected metric is reported as
*unavailable* — never silently substituted with a weaker approximation.

## Status legend

| Status | Meaning |
|--------|---------|
| Interface inspected | Top-level exports and caller-facing APIs read from source |
| Adapter implemented | A `bench` adapter exists and imports lazily |
| Tested (fixture) | Exercised in CI against a local fixture/double |
| Tested (real) | Exercised against the real installed package |
| End-to-end | Used in a full benchmark run with an HTML report |

## Summary table

| Repository | Import name | What it owns (we must not duplicate) | Status |
|------------|-------------|--------------------------------------|--------|
| PyTokenCalc | `pytokencalc` | Provider tokenization + cost estimation | Adapter implemented, tested (fixture) |
| PyInferenceManager | `pyinferencemanager` | Inference orchestration, retries, clients | Adapter implemented, tested (fixture) |
| PyStreamMCP | `pystreammcp` | Context discovery / source registry / MCP | Adapter implemented, tested (fixture) |
| PyVectorHound | `pyvectorhound` | Vector retrieval + retrieval diagnostics | Adapter implemented, tested (fixture) |
| PyAgentHound | `pyagenthound` | Agent execution tracing + root-cause | Adapter implemented, tested (fixture) |
| PyStreamPDF | `pystreampdf` | PDF extraction + semantic chunking | Adapter implemented, tested (fixture) |
| PyAPICheck | `pyapicheck` | API inventory, diff, policy scanning | Adapter implemented, tested (fixture) |
| PyStreamAI | `pystreamai` | Model routing / ONNX / deployment | Adapter implemented, tested (fixture) |
| OpenAnchor | `openanchor` | Token-intelligence middleware, attribution | Adapter implemented, tested (fixture) |

## Confirmed caller-facing interfaces

These are the exact top-level exports observed in source. Nothing here is
guessed; where a package could not be fully confirmed it is marked
**NOT CONFIRMED**.

### PyTokenCalc — `pytokencalc`
- Exports: `count_tokens`, `estimate_cost`, `get_model_pricing`, `PRICING_TABLE`,
  `TokenCounter`, `TokenCountResult`, `TokenCounterRegistry`,
  `get_global_registry`, `TokenCounterCache`, `TokenCalculator`.
- Zero hard dependencies; optional extras for `tiktoken`, `transformers`,
  `sentencepiece`.
- **PyContextFold role:** precise token counts and cost for metrics, via adapter.
  PyContextFold itself keeps a *caller-supplied* tokenizer and never ships a
  model vocabulary.

### PyInferenceManager — `pyinferencemanager`
- Exports: `Orchestrator` (`.run()`, `.plan()`), and the Rust-backed
  `PyOrchestrator` from `_core`.
- No Python runtime dependencies.
- **PyContextFold role:** optional inference backend for quality scoring. The
  offline benchmark path must never require it.

### PyStreamMCP — `pystreammcp` (v3.3.1)
- Exports include `Agent`, `QueryResult`, `Query`, `Discovery`, `SourceRegistry`,
  `AgentFrameworkAdapter`, `PyStreamMCPServer`, `PyStreamMCPAPI`, `create_app`,
  `Orchestrator`; `discovery.SourceRegistry` supports `register` / `discover`.
- **PyContextFold role:** dataset *sourcing* (discovering repositories/documents)
  for real-world corpora. Benchmarks remain runnable without it.

### PyVectorHound — `pyvectorhound`
- Hybrid Rust + Python. Owns retrieval and retrieval-quality diagnostics.
- **PyContextFold role:** retrieval metrics (recall@k, nDCG) when evaluating
  folded vs unfolded context, via adapter. Never re-implement embeddings or
  vector search here.

### PyAgentHound — `pyagenthound` (v0.1.0)
- Exports: `AgentHound`, `Event`, `Span`, `SpanError`, `SpanStatus`, `SpanType`,
  `Trace`, `TraceSummary`.
- Rich surfaces: `rootcause.rank_root_causes`, `rules.run_rules` / `DEFAULT_RULES`,
  `graph.build_graph`, `baseline.compare_to_baseline`, `evaluation.evaluate`,
  `replay.run_replay`, `storage.SQLiteTraceStore`.
- Runtime deps include `pydantic>=2`, `click`, `rich`, `fastapi`, `jinja2`.
- **PyContextFold role:** agent-task metrics + trace-derived quality signals via
  adapter. Never re-implement tracing.

### PyStreamPDF — `pystreampdf` (v2.3.0)
- Exports: `open`, `load_index`; `SemanticChunker`, `TableExtractor`,
  `ReadingOrderCorrector`, `MultimediaAnalyzer`, `CitationTracker`, element types
  and chunk/table/multimedia models; `TokenBudgetConfig`, `BudgetRule`,
  `PDFCache`, `CachedDocument`; optional dashboard/Excel/OCR/validation/
  intelligence/pipeline/structure groups.
- `SemanticChunker(target_chunk_size=1000, target_tokens=500)` →
  `chunk_content(content, element_type, page_start, page_end, heading_path=None,
  budget_override=None) -> list[ContentChunk]`.
- `tokenizer.count_tokens(text)`, `is_exact()`, `TOKENIZER_MODE` (real BPE via
  optional `tiktoken`, else `len/4` heuristic).
- Runtime deps: `rich>=13`, `pyyaml>=6`; optional `tiktoken`; Rust/PDFium core.
- **PyContextFold role:** PDF ingestion + a *comparison* chunking strategy via
  adapter. Never re-implement PDF parsing.

### PyAPICheck — `pyapicheck` (v0.7.1)
- Exports: `discover`, `discover_directory`, `discover_path`, `diff`, `report`,
  `baseline`, `policies_validate`, `policies_recommend`, `policies_diff`,
  `policies_emit_envoy`, `persist`, `load_inventory`, `graph_*`, `remediate`.
- **PyContextFold role:** API-surface inventory to define *what must survive*
  folding (ground-truth generation) via adapter.

### PyStreamAI — `pystreamai`
- Owns model routing / ONNX / deployment.
- **PyContextFold role:** optional model provider for quality scoring. Offline
  benchmarks must not require it.

### OpenAnchor — `openanchor`
- Exports: `TokenCollector`, `Middleware` (LangChain), `Analytics`,
  `AttributionModel`.
- Deps: `pytokencalc>=0.7.0`, `requests`, `pydantic>=2`, `opentelemetry`.
- **PyContextFold role:** cost/attribution comparison via adapter. Never
  re-implement middleware or attribution.

## Non-overlap contract

PyContextFold (and its benchmark platform) will **not**:

- tokenize for a specific model vendor (PyTokenCalc), or estimate cost itself;
- orchestrate inference or implement retries/clients (PyInferenceManager);
- discover context or implement MCP (PyStreamMCP);
- implement embeddings or vector search (PyVectorHound);
- implement tracing or root-cause analysis (PyAgentHound);
- parse PDFs or implement PDF semantic chunking (PyStreamPDF);
- scan or diff APIs (PyAPICheck);
- route models, run ONNX, or handle deployment (PyStreamAI);
- implement token middleware or attribution (OpenAnchor).

It **will** provide the missing piece — structure-aware, deterministic
*content optimization* and a harness that *measures* the trade-offs — and expose
narrow, optional adapters so the other projects can be measured through it.

## Open items

- PyStreamPDF's exact PDFium binding crate and the external
  `statguardian._mcp_connector.BaseMCPConnector` target are **NOT CONFIRMED**.
- Whether `pyagenthound` / `pystreampdf` are published on PyPI is **NOT
  CONFIRMED** (local source only). Adapters must therefore support local
  checkouts and degrade gracefully when a package is absent.
