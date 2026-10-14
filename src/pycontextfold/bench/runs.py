"""Result models for an experiment run.

These mirror :mod:`pycontextfold.bench.models` but describe *outputs*: what each
adapter did to each document and which metrics were observed. They are immutable
and round-trip through plain ``dict``/JSON so run artifacts stay portable.

Determinism: nothing here records wall-clock time. Reproducibility is captured
structurally through content hashes and the seed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .models import MetricResult

RUN_SCHEMA_VERSION = 1

STATUS_OK = "ok"
STATUS_FAILED = "failed"
STATUS_UNAVAILABLE = "unavailable"


def canonical_hash(value: Any) -> str:
    """A stable SHA-256 over a JSON-serialisable value (sorted keys)."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DocumentRun:
    """The outcome of applying one adapter to one document."""

    document_id: str
    adapter: str
    method: str = ""
    status: str = STATUS_OK
    metrics: tuple[MetricResult, ...] = ()
    output_bytes: int | None = None
    lossy: bool | None = None
    error: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in (STATUS_OK, STATUS_FAILED, STATUS_UNAVAILABLE):
            raise ValueError(f"invalid status {self.status!r}")

    def metric(self, name: str) -> MetricResult | None:
        for result in self.metrics:
            if result.name == name:
                return result
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "adapter": self.adapter,
            "method": self.method,
            "status": self.status,
            "output_bytes": self.output_bytes,
            "lossy": self.lossy,
            "error": self.error,
            "metrics": [m.to_dict() for m in self.metrics],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DocumentRun:
        return cls(
            document_id=str(data["document_id"]),
            adapter=str(data.get("adapter", "")),
            method=str(data.get("method", "")),
            status=str(data.get("status", STATUS_OK)),
            output_bytes=data.get("output_bytes"),
            lossy=data.get("lossy"),
            error=str(data.get("error", "")),
            metrics=tuple(MetricResult(**m) for m in data.get("metrics", ())),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True)
class AdapterRun:
    """All document runs for one adapter, plus aggregated metrics."""

    adapter: str
    version: str = "0"
    available: bool = True
    documents: tuple[DocumentRun, ...] = ()
    aggregate: Mapping[str, MetricResult] = field(default_factory=dict)
    error: str = ""

    @property
    def succeeded(self) -> int:
        return sum(1 for d in self.documents if d.status == STATUS_OK)

    @property
    def failed(self) -> int:
        return sum(1 for d in self.documents if d.status == STATUS_FAILED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "version": self.version,
            "available": self.available,
            "error": self.error,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "aggregate": {
                name: result.to_dict()
                for name, result in sorted(self.aggregate.items())
            },
            "documents": [d.to_dict() for d in self.documents],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AdapterRun:
        return cls(
            adapter=str(data["adapter"]),
            version=str(data.get("version", "0")),
            available=bool(data.get("available", True)),
            error=str(data.get("error", "")),
            aggregate={
                name: MetricResult(**result)
                for name, result in (data.get("aggregate") or {}).items()
            },
            documents=tuple(
                DocumentRun.from_dict(d) for d in data.get("documents", ())
            ),
        )


@dataclass(frozen=True)
class RunResult:
    """A complete, reproducible experiment artifact."""

    experiment: Mapping[str, Any]
    dataset: str
    dataset_hash: str
    config_hash: str
    adapters: tuple[AdapterRun, ...]
    dataset_version: str = "1"
    seed: int = 0
    schema_version: int = RUN_SCHEMA_VERSION

    def adapter(self, name: str) -> AdapterRun | None:
        for run in self.adapters:
            if run.adapter == name:
                return run
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "experiment": dict(self.experiment),
            "dataset": self.dataset,
            "dataset_version": self.dataset_version,
            "dataset_hash": self.dataset_hash,
            "config_hash": self.config_hash,
            "seed": self.seed,
            "adapters": [a.to_dict() for a in self.adapters],
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RunResult:
        return cls(
            experiment=dict(data.get("experiment") or {}),
            dataset=str(data.get("dataset", "")),
            dataset_version=str(data.get("dataset_version", "1")),
            dataset_hash=str(data.get("dataset_hash", "")),
            config_hash=str(data.get("config_hash", "")),
            seed=int(data.get("seed", 0)),
            adapters=tuple(
                AdapterRun.from_dict(a) for a in data.get("adapters", ())
            ),
            schema_version=int(data.get("schema_version", RUN_SCHEMA_VERSION)),
        )

    @classmethod
    def from_json(cls, text: str) -> RunResult:
        return cls.from_dict(json.loads(text))


def write_run(run: RunResult, path: str) -> None:
    """Write a run artifact as JSON with a trailing newline."""
    from pathlib import Path

    Path(path).write_text(run.to_json() + "\n", encoding="utf-8")


def read_run(path: str) -> RunResult:
    from pathlib import Path

    return RunResult.from_json(Path(path).read_text(encoding="utf-8"))


__all__ = [
    "RUN_SCHEMA_VERSION",
    "STATUS_FAILED",
    "STATUS_OK",
    "STATUS_UNAVAILABLE",
    "AdapterRun",
    "DocumentRun",
    "RunResult",
    "canonical_hash",
    "read_run",
    "write_run",
]
