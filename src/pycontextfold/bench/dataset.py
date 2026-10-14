"""Dataset schema helpers and a deterministic synthetic corpus.

The synthetic dataset exists so that offline benchmarks are reproducible and
require no network or credentials. It is intentionally small but exercises the
code, prose, log and structured-text paths.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .models import Dataset, Document, GroundTruth

SYNTHETIC_DATASET_NAME = "synthetic"
SYNTHETIC_DATASET_VERSION = "1"

_SYNTHETIC_PY = '''\
"""Synthetic module used by the offline benchmark."""

# A leading comment that the safe profile may remove.
import os


def add(a, b):
    """Return the sum of a and b."""
    # implementation detail
    return a + b


def main():
    print(add(1, 2))
    print(os.getcwd())


if __name__ == "__main__":
    main()
'''

_SYNTHETIC_MD = """\
# Synthetic document

This paragraph explains the synthetic corpus. It contains several sentences and
is repeated content that a documentation profile may reduce.

## Details

- first item
- second item
- third item

```python
print("code fences must survive")
```
"""

_SYNTHETIC_LOG = "2026-01-01T00:00:00Z INFO starting\n2026-01-01T00:00:01Z INFO health ok\n2026-01-01T00:00:02Z INFO health ok\n2026-01-01T00:00:03Z INFO health ok\n2026-01-01T00:00:04Z INFO health ok\n2026-01-01T00:00:05Z ERROR timeout\n2026-01-01T00:00:06Z ERROR timeout\n2026-01-01T00:00:07Z INFO done"

_SYNTHETIC_JSON = json.dumps(
    {"name": "synthetic", "items": [1, 2, 3], "nested": {"enabled": True}},
    indent=2,
) + "\n"


def _synthetic_documents() -> tuple[Document, ...]:
    return (
        Document(
            id="py-basic",
            text=_SYNTHETIC_PY,
            path="synthetic.py",
            media_type="text/x-python",
            language="python",
        ),
        Document(
            id="md-basic",
            text=_SYNTHETIC_MD,
            path="synthetic.md",
            media_type="text/markdown",
            language="markdown",
        ),
        Document(
            id="log-basic",
            text=_SYNTHETIC_LOG,
            path="synthetic.log",
            media_type="text/plain",
            language="log",
        ),
        Document(
            id="json-basic",
            text=_SYNTHETIC_JSON,
            path="synthetic.json",
            media_type="application/json",
            language="json",
        ),
    )


def _synthetic_ground_truth() -> dict[str, GroundTruth]:
    return {
        "py-basic": GroundTruth(
            document_id="py-basic",
            must_preserve=("def add(a, b):", "return a + b", "import os"),
            must_drop=("# implementation detail",),
        ),
        "md-basic": GroundTruth(
            document_id="md-basic",
            must_preserve=("# Synthetic document", "print(\"code fences must survive\")"),
        ),
        "log-basic": GroundTruth(
            document_id="log-basic",
            must_preserve=("ERROR timeout", "INFO done"),
        ),
    }


def synthetic_dataset(
    name: str = SYNTHETIC_DATASET_NAME, version: str = SYNTHETIC_DATASET_VERSION
) -> Dataset:
    """Build the deterministic synthetic dataset."""
    return Dataset(
        name=name,
        version=version,
        description="Deterministic offline corpus (code, prose, log, JSON).",
        documents=_synthetic_documents(),
        ground_truth=_synthetic_ground_truth(),
    )


def dataset_from_dict(data: dict[str, Any]) -> Dataset:
    return Dataset.from_dict(data)


def dataset_to_json(dataset: Dataset, *, indent: int | None = 2) -> str:
    return json.dumps(dataset.to_dict(), indent=indent, sort_keys=False)


def dataset_from_json(text: str) -> Dataset:
    return Dataset.from_dict(json.loads(text))


def load_dataset(path: str | Path) -> Dataset:
    """Load a dataset from a JSON file."""
    return dataset_from_json(Path(path).read_text(encoding="utf-8"))


def write_dataset(dataset: Dataset, path: str | Path) -> None:
    Path(path).write_text(dataset_to_json(dataset) + "\n", encoding="utf-8")


def iter_documents(documents: Iterable[Document]) -> Iterable[tuple[int, Document]]:
    yield from enumerate(documents)


__all__ = [
    "SYNTHETIC_DATASET_NAME",
    "SYNTHETIC_DATASET_VERSION",
    "dataset_from_dict",
    "dataset_from_json",
    "dataset_to_json",
    "iter_documents",
    "load_dataset",
    "synthetic_dataset",
    "write_dataset",
]
