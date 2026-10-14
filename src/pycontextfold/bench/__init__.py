"""PyContextFold benchmarking platform (offline-first, dependency-light).

This subpackage measures the trade-offs of context optimization: how much is
removed (size/char/token reduction) and how much that matters (ground-truth
preservation). It is deliberately independent from any ecosystem project: the
core package runs these tools with nothing else installed, and optional adapters
to sibling projects (PyTokenCalc, PyStreamPDF, ...) are capability-declared and
loaded lazily.

Phase 1 (this module) provides the foundation: models, capabilities, the adapter
protocol + registry, deterministic baselines, token measurement and metrics.
"""

from __future__ import annotations

from . import adapters, chunking, config, dataset, metrics, models, tokens
from .capabilities import Capability, CapabilitySet
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

__all__ = [
    "DATASET_SCHEMA_VERSION",
    "AdapterInfo",
    "Capability",
    "CapabilitySet",
    "Dataset",
    "Document",
    "ExperimentConfig",
    "GroundTruth",
    "MetricResult",
    "OptimizationRequest",
    "OptimizationResult",
    "adapters",
    "chunking",
    "config",
    "dataset",
    "metrics",
    "models",
    "tokens",
]
