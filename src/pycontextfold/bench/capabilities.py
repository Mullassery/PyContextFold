"""Capability declarations for benchmark adapters.

An adapter advertises exactly what it can do. The runner checks these flags
before invoking an adapter so that a *missing* capability produces an explicit
``unavailable`` metric rather than a silently weaker substitute.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum


class Capability(str, Enum):
    """A single thing an adapter may be able to do."""

    OPTIMIZE_TEXT = "optimize_text"
    """Reduce the size of a text document (the PyContextFold core capability)."""

    CHUNK_TEXT = "chunk_text"
    """Split text into retrieval-sized chunks."""

    EXTRACT_PDF = "extract_pdf"
    """Extract text/content from a PDF document."""

    COUNT_TOKENS_EXACT = "count_tokens_exact"
    """Count tokens precisely for a specific model vocabulary."""

    ESTIMATE_COST = "estimate_cost"
    """Estimate monetary cost for a token/price model."""

    RETRIEVAL_METRICS = "retrieval_metrics"
    """Compute retrieval-quality metrics (recall@k, nDCG, ...)."""

    AGENT_TRACING = "agent_tracing"
    """Record or consume agent execution traces."""

    AGENT_METRICS = "agent_metrics"
    """Derive task-quality metrics from agent traces."""

    API_INVENTORY = "api_inventory"
    """Enumerate the public API surface of a source tree."""

    QUALITY_SCORING = "quality_scoring"
    """Score output quality, optionally using an inference backend."""

    SOURCE_DISCOVERY = "source_discovery"
    """Discover documents/corpora from sources."""

    COST_ATTRIBUTION = "cost_attribution"
    """Attribute token/cost usage across calls or components."""


class CapabilitySet:
    """An immutable, ordered, hashable set of :class:`Capability` values.

    Provides membership checks and explanations without pulling in a third-party
    dependency.
    """

    __slots__ = ("_members",)

    def __init__(self, members: Iterable[Capability] = ()) -> None:
        seen: dict[Capability, None] = {}
        for member in members:
            if not isinstance(member, Capability):
                raise TypeError(
                    f"capability must be a Capability, got {type(member).__name__}"
                )
            seen[member] = None
        self._members: frozenset[Capability] = frozenset(seen)

    def __contains__(self, item: object) -> bool:
        return item in self._members

    def __iter__(self):
        return iter(sorted(self._members, key=lambda c: c.value))

    def __len__(self) -> int:
        return len(self._members)

    def __bool__(self) -> bool:
        return bool(self._members)

    def __repr__(self) -> str:
        inner = ", ".join(c.value for c in self)
        return f"CapabilitySet({inner})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CapabilitySet):
            return self._members == other._members
        if isinstance(other, (set, frozenset)):
            return self._members == frozenset(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._members)

    def values(self) -> tuple[str, ...]:
        """Return the capability values as a sorted tuple of strings."""
        return tuple(c.value for c in self)

    def union(self, other: CapabilitySet) -> CapabilitySet:
        return CapabilitySet(self._members | other._members)

    def missing(self, required: Iterable[Capability]) -> tuple[Capability, ...]:
        """Return the required capabilities this set does *not* provide."""
        return tuple(c for c in required if c not in self._members)

    def supports(self, required: Iterable[Capability]) -> bool:
        """Whether every required capability is present."""
        return not self.missing(required)


EMPTY = CapabilitySet()
"""A capability set that supports nothing."""


def of(*capabilities: Capability) -> CapabilitySet:
    """Convenience constructor: ``of(Capability.OPTIMIZE_TEXT, ...)``."""
    return CapabilitySet(capabilities)


__all__ = ["EMPTY", "Capability", "CapabilitySet", "of"]
