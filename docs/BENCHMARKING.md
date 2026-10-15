# Benchmarking & evaluation

This is the **evaluation platform** — it measures a transformation's effect on
size, tokens, cost, preservation and retrieval quality. It is different from
[`BENCHMARKS.md`](BENCHMARKS.md), which covers the Rust core's *performance*.

The platform lives in `pycontextfold.bench`. It is pure standard library and
runs fully **offline** (no network, no credentials, no paid inference).

## Quick start (CLI)

```bash
pycontextfold-bench adapters                 # list adapters + availability
pycontextfold-bench datasets --out ds.json   # emit the synthetic corpus
pycontextfold-bench run --config exp.json --report report.html --gate
pycontextfold-bench report run.json --out report.html
pycontextfold-bench gates run.json --config exp.json
```

`run` exits `1` when any gate fails, so it drops straight into CI. It also
accepts `--dataset PATH` to use a dataset file instead of the one in the config.

`python -m pycontextfold.bench …` is equivalent to the console script.

## Quick start (Python)

```python
from pycontextfold import bench

run = bench.run_experiment(
    bench.dataset.synthetic_dataset(),
    bench.ExperimentConfig(
        name="demo",
        dataset="synthetic",
        adapters=("baseline", "contextfold"),
        metrics=("size_reduction", "token_reduction", "preservation_recall"),
    ),
)
bench.write_report(run, "report.html")          # single-file, offline HTML
```

## Concepts

- **Dataset** — a versioned list of `Document`s plus optional `GroundTruth`
  (protected spans that must survive). `dataset.synthetic_dataset()` is a
  deterministic, offline corpus (code, prose, log, JSON).
- **Adapter** — wraps something that optimizes or chunks text. Built-ins:
  `baseline` (identity) and `contextfold` (the core engine). Optional adapters
  wrap sibling projects (see below).
- **Capability** — every adapter declares what it supports
  (`optimize_text`, `chunk_text`, `count_tokens_exact`, `estimate_cost`,
  `retrieval_metrics`, `agent_metrics`, `extract_pdf`, `api_inventory`,
  `quality_scoring`, `cost_attribution`). A metric that needs a missing
  capability is reported **unavailable**, never guessed.
- **Metric** — `MetricResult` with a name, value and unit, or an explicit
  `unavailable` status. Core metrics: size/char/token `reduction`,
  `preservation_recall`, `drop_precision`.
- **Run** — the deterministic result of pairing a dataset with adapters and
  metrics, serialized as JSON (`RunResult`, `write_run`/`read_run`) with content
  hashes and no wall-clock timestamps.

## Metrics and honesty

- Reduction is measured in **bytes, characters or tokens** and always labelled
  as such. A byte ratio is never called a token ratio.
- Token counts are **approximate by default**. Exact counts are used only when
  an exact measurer is available (PyTokenCalc, installed via the `tokens`
  extra); the measurer reports whether it is exact, and nothing labels an
  approximation as exact.
- Failure isolation: an adapter that raises is recorded as **failed**, and an
  adapter whose dependency is absent is **unavailable** — neither aborts a run.

## Optional ecosystem adapters

Each adapter activates automatically when its project is importable and is
otherwise reported `unavailable`. Install them individually with extras:

| Adapter | Extra | Provides |
|---|---|---|
| `pytokencalc` | `[tokens]` | exact tokens, cost estimation |
| `pystreampdf` | `[pdf]` | PDF text extraction / chunking |
| `pyagenthound` | `[agents]` | agent trace metrics |
| `pyapicheck` | `[api]` | API-inventory ground truth |
| `pyvectorhound` | `[retrieval]` | retrieval metrics |
| `pyinferencemanager`, `pystreamai` | `[inference]` | optional quality scoring |
| `openanchor` | `[middleware]` | cost attribution |
| `pystreammcp` | `[discovery]` | corpus sourcing |

`[ecosystem]` installs all of them. The core and the offline benchmark need
**none** of them. Adapters never re-implement a sibling's responsibility; they
delegate and check capabilities first.

## Quality gates

Gates turn a run into a regression check. Define them in the config:

```json
{
  "name": "ci",
  "dataset": "synthetic",
  "adapters": ["contextfold"],
  "metrics": ["size_reduction", "preservation_recall"],
  "options": {
    "gates": [
      {"metric": "preservation_recall", "minimum": 0.9},
      {"metric": "size_reduction", "adapter": "contextfold", "minimum": 0.1}
    ]
  }
}
```

A gate fails when the aggregated metric is below `minimum`, above `maximum`, or
**unavailable**. `adapter` scopes a gate to one adapter.

## Reports

`write_report` produces a **single self-contained HTML file**: inline CSS/JS, no
CDN or external assets. It contains a summary, per-adapter aggregates and a
per-document drill-down, plus reproduction metadata (versions, seeds, config and
dataset hashes). Output is deterministic unless a `generated_at` timestamp is
supplied.

## Reproducibility

Runs are seeded and content-hashed. Given the same dataset, config and versions,
`canonical_hash` is stable — which is what makes the gates meaningful across
machines and CI runs.
