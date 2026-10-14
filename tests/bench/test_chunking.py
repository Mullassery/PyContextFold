from __future__ import annotations

import pytest

from pycontextfold.bench.chunking import (
    CHUNKERS,
    chunk,
    chunk_fixed_bytes,
    chunk_fixed_chars,
    chunk_lines,
    chunk_paragraphs,
)


def test_fixed_chars_lossless_coverage():
    text = "abcdefghij"
    chunks = chunk_fixed_chars(text, size=3)
    assert [c.text for c in chunks] == ["abc", "def", "ghi", "j"]
    assert "".join(c.text for c in chunks) == text
    assert [(c.start, c.end) for c in chunks] == [(0, 3), (3, 6), (6, 9), (9, 10)]


def test_fixed_chars_indices_and_sizes():
    chunks = chunk_fixed_chars("hello", size=2)
    assert [c.index for c in chunks] == [0, 1, 2]
    assert chunks[0].char_size == 2
    assert chunks[0].byte_size == 2


def test_empty_text_yields_no_chunks():
    assert chunk_fixed_chars("", size=4) == ()
    assert chunk_fixed_bytes("", size=4) == ()
    assert chunk_lines("", max_lines=2) == ()
    assert chunk_paragraphs("", max_chars=10) == ()


def test_fixed_chars_rejects_bad_size():
    with pytest.raises(ValueError):
        chunk_fixed_chars("abc", size=0)


def test_fixed_bytes_never_splits_multibyte():
    text = "aébc"  # 'é' is two UTF-8 bytes
    chunks = chunk_fixed_bytes(text, size=3)
    assert "".join(c.text for c in chunks) == text
    assert all(c.byte_size <= 3 for c in chunks)
    assert all("�" not in c.text for c in chunks)


def test_lines_grouping_lossless():
    text = "1\n2\n3\n4\n5\n"
    chunks = chunk_lines(text, max_lines=2)
    assert "".join(c.text for c in chunks) == text
    assert [c.text for c in chunks] == ["1\n2\n", "3\n4\n", "5\n"]


def test_paragraphs_group_and_cover():
    text = "para one\n\npara two\n\npara three\n"
    chunks = chunk_paragraphs(text, max_chars=1000)
    assert "".join(c.text for c in chunks) == text


def test_paragraphs_split_when_over_budget():
    text = "aaaa\n\nbbbb\n\ncccc\n"
    chunks = chunk_paragraphs(text, max_chars=6)
    assert len(chunks) >= 2
    assert "".join(c.text for c in chunks) == text


def test_chunk_dispatch_and_unknown():
    assert chunk("fixed_chars", "abcd", size=2)[0].text == "ab"
    with pytest.raises(KeyError):
        chunk("does-not-exist", "x")


def test_registry_contains_expected():
    assert set(CHUNKERS) == {"fixed_chars", "fixed_bytes", "paragraphs", "lines"}
