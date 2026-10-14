from __future__ import annotations

import pytest

from pycontextfold.bench.tokens import (
    DEFAULT_MEASURER,
    ApproximateTokenMeasurer,
    CallableTokenMeasurer,
    TokenMeasurer,
    WhitespaceTokenMeasurer,
    count_tokens,
)


def test_approximate_is_not_exact():
    measurer = ApproximateTokenMeasurer(chars_per_token=4)
    assert measurer.exact is False
    assert measurer.count("") == 0
    assert measurer.count("abcdefgh") == 2


def test_approximate_rejects_bad_ratio():
    with pytest.raises(ValueError):
        ApproximateTokenMeasurer(chars_per_token=0)


def test_whitespace_counts_words():
    measurer = WhitespaceTokenMeasurer()
    assert measurer.count("a b  c") == 3
    assert measurer.count("") == 0
    assert measurer.exact is False


def test_callable_measurer_defaults_to_exact():
    measurer = CallableTokenMeasurer(lambda text: len(text))
    assert measurer.exact is True
    assert measurer.count("abcd") == 4


def test_callable_rejects_negative():
    measurer = CallableTokenMeasurer(lambda text: -1)
    with pytest.raises(ValueError):
        count_tokens(measurer, "x")


def test_count_tokens_validates():
    assert count_tokens(CallableTokenMeasurer(lambda t: 5), "hello") == 5


def test_default_measurer_is_approximate():
    assert DEFAULT_MEASURER.exact is False
    assert isinstance(DEFAULT_MEASURER, ApproximateTokenMeasurer)


def test_protocol_runtime_check():
    assert isinstance(ApproximateTokenMeasurer(), TokenMeasurer)
    assert isinstance(WhitespaceTokenMeasurer(), TokenMeasurer)
