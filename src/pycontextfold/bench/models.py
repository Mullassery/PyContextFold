"""Versioned data models for the benchmark platform.

Everything here is built from the standard library only. Models are immutable
(dataclasses with ``frozen=True``) and round-trip through plain ``dict`` so run
artifacts stay portable JSON.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .capabilities import Capability, CapabilitySet

DATASET_SCHEMA_VERSION = 1
"""Bump when the on-disk dataset/experiment schema changes incompatibly."""


# --------------------------------------------------------------------------- #
# Inputs: documents, ground truth, datasets
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Document:
    """A single unit of content to optimize."""

    id: str
    text: str
    path: str | None = None
    media_type: str | None = None
    language: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Document.id must be a non-empty string")

    @property
    def byte_size(self) -> int:
        return len(self.text.encode("utf-8"))

    @property
    def char_size(self) -> int:
        return len(self.text)

    @property
    def line_count(self) -> int:
        return self.text.count("\n") + (0 if self.text.endswith("\n") else 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "path": self.path,
            "media_type": self.media_type,
            "language": self.language,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Document:
        return cls(
            id=str(data["id"]),
            text=str(data["text"]),
            path=data.get("path"),
            media_type=data.get("media_type"),
            language=data.get("language"),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True)
class GroundTruth:
    """What a correct transformation must keep or remove for one document."""

    document_id: str
    must_preserve: tuple[str, ...] = ()
    must_drop: tuple[str, ...] = ()
    max_reduction: float | None = None
    labels: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.document_id:
            raise ValueError("GroundTruth.document_id must be non-empty")
        if self.max_reduction is not None and not (0.0 <= self.max_reduction <= 1.0):
            raise ValueError("GroundTruth.max_reduction must be within [0, 1]")

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "must_preserve": list(self.must_preserve),
            "must_drop": list(self.must_drop),
            "max_reduction": self.max_reduction,
            "labels": dict(self.labels),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> GroundTruth:
        max_reduction = data.get("max_reduction")
        return cls(
            document_id=str(data["document_id"]),
            must_preserve=tuple(data.get("must_preserve") or ()),
            must_drop=tuple(data.get("must_drop") or ()),
            max_reduction=None if max_reduction is None else float(max_reduction),
            labels=dict(data.get("labels") or {}),
        )


@dataclass(frozen=True)
class Dataset:
    """A named, versioned collection of documents plus optional ground truth."""

    name: str
    documents: tuple[Document, ...]
    version: str = "1"
    description: str = ""
    ground_truth: Mapping[str, GroundTruth] = field(default_factory=dict)
    schema_version: int = DATASET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Dataset.name must be non-empty")
        ids = [d.id for d in self.documents]
        if len(ids) != len(set(ids)):
            raise ValueError("Dataset contains duplicate document ids")

    def __len__(self) -> int:
        return len(self.documents)

    def __iter__(self):
        return iter(self.documents)

    def get(self, document_id: str) -> Document:
        for doc in self.documents:
            if doc.id == document_id:
                return doc
        raise KeyError(document_id)

    def ground_truth_for(self, document_id: str) -> GroundTruth | None:
        return self.ground_truth.get(document_id)

    @property
    def total_bytes(self) -> int:
        return sum(d.byte_size for d in self.documents)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "documents": [d.to_dict() for d in self.documents],
            "ground_truth": {
                key: gt.to_dict() for key, gt in sorted(self.ground_truth.items())
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Dataset:
        return cls(
            name=str(data["name"]),
            version=str(data.get("version", "1")),
            description=str(data.get("description", "")),
            documents=tuple(Document.from_dict(d) for d in data.get("documents", ())),
            ground_truth={
                str(k): GroundTruth.from_dict(v)
                for k, v in (data.get("ground_truth") or {}).items()
            },
            schema_version=int(data.get("schema_version", DATASET_SCHEMA_VERSION)),
        )


# --------------------------------------------------------------------------- #
# Adapter I/O
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class AdapterInfo:
    """A description of an adapter, independent of whether it is installed."""

    name: str
    capabilities: CapabilitySet
    version: str = "0"
    available: bool = True
    detail: str = ""
    requires: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "available": self.available,
            "capabilities": list(self.capabilities.values()),
            "requires": list(self.requires),
            "detail": self.detail,
        }


@dataclass(frozen=True)
class OptimizationRequest:
    """A request to reduce one document."""

    document: Document
    method: str = "safe"
    options: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OptimizationResult:
    """The output of optimizing one document along with provenance."""

    document_id: str
    output: str
    method: str = ""
    lossy: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.document_id == "":
            raise ValueError("OptimizationResult.document_id must be non-empty")


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class MetricResult:
    """One measured quantity for one document (or an aggregate).

    ``available=False`` records that a metric *could not be computed* — for
    example because an optional adapter is missing. The ``detail`` explains why.
    """

    name: str
    value: float | None = None
    unit: str = ""
    available: bool = True
    detail: str = ""

    def __post_init__(self) -> None:
        if self.available and self.value is None:
            raise ValueError("an available MetricResult must carry a value")

    @classmethod
    def unavailable(cls, name: str, detail: str) -> MetricResult:
        return cls(name=name, value=None, available=False, detail=detail)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "available": self.available,
            "detail": self.detail,
        }


# --------------------------------------------------------------------------- #
# Experiment configuration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ExperimentConfig:
    """Declarative description of a benchmark run."""

    name: str
    dataset: str
    adapters: tuple[str, ...]
    metrics: tuple[str, ...] = ()
    seed: int = 0
    options: Mapping[str, Any] = field(default_factory=dict)
    schema_version: int = DATASET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("ExperimentConfig.name must be non-empty")
        if not self.dataset:
            raise ValueError("ExperimentConfig.dataset must be non-empty")
        if not self.adapters:
            raise ValueError("ExperimentConfig.adapters must be non-empty")
        if self.seed < 0:
            raise ValueError("ExperimentConfig.seed must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "dataset": self.dataset,
            "adapters": list(self.adapters),
            "metrics": list(self.metrics),
            "seed": self.seed,
            "options": dict(self.options),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ExperimentConfig:
        return cls(
            name=str(data["name"]),
            dataset=str(data["dataset"]),
            adapters=tuple(data.get("adapters") or ()),
            metrics=tuple(data.get("metrics") or ()),
            seed=int(data.get("seed", 0)),
            options=dict(data.get("options") or {}),
            schema_version=int(data.get("schema_version", DATASET_SCHEMA_VERSION)),
        )


def required_capabilities_for(metric: str) -> tuple[Capability, ...]:
    """Return the capabilities a named metric requires.

    Metrics that only need text (size/token reduction, preservation) require the
    target adapter's optimization capability and are handled by the runner; the
    entries here describe metrics that need a *sibling* adapter.
    """
    table: dict[str, tuple[Capability, ...]] = {
        "exact_tokens": (Capability.COUNT_TOKENS_EXACT,),
        "cost": (Capability.ESTIMATE_COST,),
        "retrieval": (Capability.RETRIEVAL_METRICS,),
        "agent": (Capability.AGENT_METRICS,),
        "api_surface": (Capability.API_INVENTORY,),
        "quality": (Capability.QUALITY_SCORING,),
    }
    return table.get(metric, ())


def _unique_preserving_order(items: Sequence[str]) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for item in items:
        seen[item] = None
    return tuple(seen)


__all__ = [
    "DATASET_SCHEMA_VERSION",
    "AdapterInfo",
    "Dataset",
    "Document",
    "ExperimentConfig",
    "GroundTruth",
    "MetricResult",
    "OptimizationRequest",
    "OptimizationResult",
    "required_capabilities_for",
]
