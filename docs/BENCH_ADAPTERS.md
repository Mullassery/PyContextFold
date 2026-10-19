# Ecosystem adapters: what is tested

PyContextFold ships optional adapters for sibling packages in `bench/adapters/`.
There are **two different test layers**:

1. `tests/bench/test_ecosystem_adapters.py` — **fake-module contract tests**.
   They inject a synthetic module into `sys.modules` to check the adapter's
   internal logic. They are not evidence that the real sibling package works.
2. `tests/bench/test_ecosystem_adapters_real.py` — **real integration tests**.
   They import the installed sibling and exercise the adapter's real call path.

A skipped test means **not tested**, not supported.

## Real test matrix (verified 2026-10-19)

Environment: Python 3.12; siblings installed from PyPI into PyContextFold's
venv. Result: **7 passed, 2 skipped**.

| Adapter | Sibling | Real call verified | Not tested / gap |
|---|---|---|---|
| `PyTokenCalcAdapter` | pytokencalc 1.4.1 | `count_tokens("hello world", model="gpt-4o")`; `estimate_cost(...)` | provider-specific models beyond the pricing table |
| `PyAPICheckAdapter` | pyapicheck 0.8.0 | OpenAPI inventory (`GET /items`, `POST /items`) + ground truth | Python-source discovery (returned no items in a probe) |
| `OpenAnchorAdapter` | openanchor 0.6.2 | `TokenCollector()` construction | `Analytics` (needs an `AttributionModel` store) |
| `PyStreamMCPAdapter` | pystreammcp 3.3.4 | `SourceRegistry.discover("…", limit=1)` (empty registry) | source-backed discovery / MCP transport |
| `PyVectorHoundAdapter` | pyvectorhound 1.8.0 | `ranking.compute_reranker_metrics(...)` | Qdrant/embedding-backed retrieval evaluation |
| `PyAgentHoundAdapter` | pyagenthound 0.2.0 | import + version | **`agent_metrics` not tested** — needs `inspect-ai` and a model |
| `PyInferenceManagerAdapter` | pyinferencemanager 1.3.2 | import + version | **`complete`/`score` not tested** — needs a configured provider/model |
| `PyStreamPDFAdapter` | pystreampdf | — | **not tested** — cp311-only wheel; not installed on 3.12 |
| `PyStreamAIAdapter` | pystreamai | — | **not tested** — cp311-only wheel; not installed on 3.12 |

## Real API fixes made while testing

The real packages differed from the adapters' assumed contracts:

- **PyTokenCalc**: real `estimate_cost(model, input_tokens, output_tokens=0)`
  (the adapter's old positional call was wrong).
- **PyAPICheck**: real `discover_directory()` returns
  `{title, endpoints: [{method, path}, …]}`; the adapter now flattens endpoints.
- **PyAgentHound**: real entry point is `evaluate_with_inspect(traces, task, *,
  model, limit=None)`; the adapter now supports it (evaluation itself remains
  untested without `inspect-ai` + a model).
- **PyVectorHound**: no top-level `evaluate`/`evaluate_retrieval`; the adapter
  now uses `ranking.compute_reranker_metrics(...)`.

## Running the real tests

```bash
pip install pytokencalc pyapicheck pyagenthound openanchor pystreammcp \
            pyvectorhound pyinferencemanager
pytest tests/bench/test_ecosystem_adapters_real.py -q
```

To cover the two skipped adapters, use a Python 3.11 environment and install
`pystreampdf` and `pystreamai`; they still need their own fixtures/models for a
full call.
