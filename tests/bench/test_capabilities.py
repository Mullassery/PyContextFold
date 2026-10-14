from __future__ import annotations

import pytest

from pycontextfold.bench.capabilities import EMPTY, Capability, CapabilitySet, of


def test_of_and_membership():
    caps = of(Capability.OPTIMIZE_TEXT, Capability.CHUNK_TEXT)
    assert Capability.OPTIMIZE_TEXT in caps
    assert Capability.ESTIMATE_COST not in caps
    assert len(caps) == 2
    assert bool(caps)


def test_values_are_sorted_and_stable():
    caps = CapabilitySet([Capability.OPTIMIZE_TEXT, Capability.CHUNK_TEXT])
    assert caps.values() == ("chunk_text", "optimize_text")


def test_missing_and_supports():
    caps = of(Capability.OPTIMIZE_TEXT)
    assert caps.supports([Capability.OPTIMIZE_TEXT])
    assert not caps.supports([Capability.OPTIMIZE_TEXT, Capability.CHUNK_TEXT])
    assert caps.missing([Capability.OPTIMIZE_TEXT, Capability.CHUNK_TEXT]) == (
        Capability.CHUNK_TEXT,
    )


def test_duplicates_are_collapsed():
    caps = CapabilitySet([Capability.OPTIMIZE_TEXT, Capability.OPTIMIZE_TEXT])
    assert len(caps) == 1


def test_equality_with_plain_sets():
    caps = of(Capability.OPTIMIZE_TEXT)
    assert caps == {Capability.OPTIMIZE_TEXT}
    assert hash(caps) == hash(frozenset({Capability.OPTIMIZE_TEXT}))


def test_empty_set_is_falsy():
    assert EMPTY == set()
    assert not EMPTY
    assert "CapabilitySet" in repr(EMPTY)


def test_rejects_non_capability():
    with pytest.raises(TypeError):
        CapabilitySet(["optimize_text"])  # type: ignore[list-item]


def test_union():
    combined = of(Capability.OPTIMIZE_TEXT).union(of(Capability.CHUNK_TEXT))
    assert combined.supports([Capability.OPTIMIZE_TEXT, Capability.CHUNK_TEXT])
