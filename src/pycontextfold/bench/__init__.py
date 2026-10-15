"""PyContextFold benchmarking platform (offline-first, dependency-light).

This subpackage measures the trade-offs of context optimization: how much is
removed (size/char/token reduction) and how much that matters (ground-truth
preservation). It is deliberately independent from any ecosystem project: the
core package runs these tools with nothing else installed, and optional adapters
to sibling projects (PyTokenCalc, PyStreamPDF, ...) are capability-declared and
loaded lazily.

Phase 1 provides the foundation: models, capabilities, the adapter protocol +
registry, deterministic baselines, token measurement and metrics. Phase 2 adds
the offline experiment runner (:mod:`pycontextfold.bench.runner`) and portable
run-result artifacts (:mod:`pycontextfold.bench.runs`). Phase 3 adds a
self-contained HTML report (:mod:`pycontextfold.bench.report`). Phase 4 adds
optional, capability-declared ecosystem adapters. Phase 5 adds quality gates
(:mod:`pycontextfold.bench.gates`) and a CLI (:mod:`pycontextfold.bench.cli`).
"""

from __future__ import annotations

from . import (
    adapters,
    chunking,
    config,
    dataset,
    gates,
    metrics,
    models,
    report,
    runner,
    runs,
    tokens,
)
from .capabilities import Capability, CapabilitySet
from .gates import GateOutcome, GateReport, Threshold, evaluate_gates
from .models import (
    DATASET_SCHEMA_VERSION,
    AdapterInfo,
    Dataset,
    Document,
    ExperimentConfig,
    GroundTruth,
    MetricResult,
    OptimizationRequest,
    OptimizationResult,
)
from .report import render_report, write_report
from .runner import Runner, run_experiment
from .runs import AdapterRun, DocumentRun, RunResult

__all__ = [
    "DATASET_SCHEMA_VERSION",
    "AdapterInfo",
    "AdapterRun",
    "Capability",
    "CapabilitySet",
    "Dataset",
    "Document",
    "DocumentRun",
    "ExperimentConfig",
    "GateOutcome",
    "GateReport",
    "GroundTruth",
    "MetricResult",
    "OptimizationRequest",
    "OptimizationResult",
    "RunResult",
    "Runner",
    "Threshold",
    "adapters",
    "chunking",
    "config",
    "dataset",
    "evaluate_gates",
    "gates",
    "metrics",
    "models",
    "render_report",
    "report",
    "run_experiment",
    "runner",
    "runs",
    "tokens",
    "write_report",
]
