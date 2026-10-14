"""End-to-end tests for the Python bindings.

These exercise the native Rust engine through the thin Python surface. They are
intentionally behavioural: they assert preservation guarantees and safe-failure
behaviour rather than internal details.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import pycontextfold as pcf

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_version_is_exposed():
    assert isinstance(pcf.__version__, str)
    assert pcf.__version__


def test_profiles_listing():
    names = pcf.profiles()
    assert "safe" in names
    assert "interface-only" in names
    assert "logs" in names


def test_profile_info():
    info = pcf.profile_info("interface-only")
    assert info["name"] == "interface-only"
    assert info["loss"]["allow_lossy"] is True
    assert "LOSSY" in info["description"]


def test_supported_languages():
    langs = set(pcf.supported_languages())
    assert {"python", "rust", "javascript", "typescript", "go", "markdown", "log", "json"} <= langs


def test_detect_language_by_extension():
    assert pcf.detect_language("x = 1\n", path="a.py") == "python"
    assert pcf.detect_language("fn main() {}\n", path="a.rs") == "rust"


def test_fold_safe_removes_comments_preserves_docstrings():
    src = fixture("sample.py")
    res = pcf.fold(src, profile="safe", path="sample.py")
    assert res.report.detected_language == "python"
    assert res.report.parse_status == "parsed"
    assert res.report.syntax_valid is True
    assert res.report.behavior_preserving is True
    assert res.report.semantic_equivalence == "not_guaranteed"
    assert "Module docstring" in res.output
    assert "A line comment" not in res.output
    assert "import os" in res.output
    assert "return a + b" in res.output
    assert res.report.reduction_ratio > 0
    assert res.lossy is False


def test_fold_interface_only_is_lossy_and_valid():
    src = fixture("sample.py")
    res = pcf.fold(src, profile="interface-only", path="sample.py")
    assert res.lossy is True
    assert res.report.behavior_preserving is False
    assert res.report.syntax_valid is True
    assert "[contextfold: implementation omitted]" in res.output
    assert "return a + b" not in res.output
    assert "import os" in res.output


def test_report_to_dict_and_json():
    res = pcf.fold("# c\nx = 1\n", profile="safe", language="python")
    d = res.report.to_dict()
    assert d["profile"] == "safe"
    assert d["semantic_equivalence"] == "not_guaranteed"
    parsed = json.loads(res.report.to_json())
    assert parsed["engine_version"] == pcf.__version__


def test_typed_request_and_engine():
    engine = pcf.Engine()
    req = pcf.FoldRequest(
        "# c\nx = 1\n", profile="safe", language="python", path="a.py"
    )
    res = engine.fold_request(req)
    assert res.output == "x = 1\n"


def test_fold_file_does_not_modify_source(tmp_path: Path):
    src = "# comment\nx = 1\n"
    p = tmp_path / "a.py"
    p.write_text(src, encoding="utf-8")
    res = pcf.fold_file(str(p), profile="safe")
    assert "comment" not in res.output
    # source file is untouched
    assert p.read_text(encoding="utf-8") == src


def test_unknown_profile_raises():
    with pytest.raises(pcf.UnknownProfileError):
        pcf.fold("x = 1\n", profile="does-not-exist", language="python")


def test_unknown_language_raises():
    with pytest.raises(ValueError):
        pcf.fold("x = 1\n", profile="safe", language="not-a-language")


def test_protected_marker_line_survives():
    src = fixture("protected.py")
    res = pcf.fold(src, profile="safe", path="protected.py")
    assert "Protected banner: contextfold:keep" in res.output
    assert "removable comment" not in res.output
    assert res.report.protected_bytes > 0


def test_protected_ranges_are_respected():
    src = "a = 1  # keepme\nb = 2  # dropme\n"
    # Protect the first line (bytes 0..len of first line).
    first_line = src.index("\n") + 1
    res = pcf.fold(
        src,
        profile="safe",
        language="python",
        protected_ranges=[(0, first_line)],
    )
    assert "# keepme" in res.output
    assert "# dropme" not in res.output


def test_malformed_input_fails_safe():
    src = fixture("malformed.py")
    res = pcf.fold(src, profile="safe", path="malformed.py")
    assert res.report.parse_status == "parse_failed"
    assert res.output == src
    assert any(w["code"] == "parse_failed" for w in res.report.to_dict()["warnings"])


def test_unicode_roundtrip():
    src = fixture("unicode.py")
    res = pcf.fold(src, profile="safe", path="unicode.py")
    assert "héllo wörld 🌍 日本語" in res.output
    assert res.report.syntax_valid is True


def test_empty_input():
    res = pcf.fold("", profile="safe", language="python")
    assert res.output == ""
    assert res.report.input_bytes == 0


def test_markdown_documentation_profile():
    src = fixture("sample.md")
    res = pcf.fold(src, profile="documentation", path="sample.md")
    assert res.report.detected_language == "markdown"
    assert res.output.count("This is an introduction paragraph") == 1
    # code fence preserved verbatim
    assert "x = 1   " in res.output


def test_logs_profile_collapses_repeats():
    src = fixture("sample.log")
    res = pcf.fold(src, profile="logs", path="sample.log")
    assert "collapsed" in res.output
    assert "INFO done" in res.output
    assert res.lossy is True


def test_json_minified():
    src = fixture("sample.json")
    res = pcf.fold(src, profile="safe", path="sample.json")
    assert res.report.detected_language == "json"
    assert ",   " not in res.output
    assert json.loads(res.output) == json.loads(src)


def test_budget_bytes_is_approximate_not_tokens():
    res = pcf.fold("x = 1\n" * 100, profile="safe", language="python", budget_bytes=10)
    b = res.report.to_dict()["budget"]
    assert b["metric"] == "bytes"
    assert b["exact_tokens"] is False
    assert b["met"] is False
    assert any(w["code"] == "budget_not_met" for w in res.report.to_dict()["warnings"])


class _WhitespaceTokenizer:
    name = "whitespace-tok"

    def count(self, text: str) -> int:
        return len(text.split())


def test_caller_supplied_tokenizer():
    engine = pcf.Engine()
    req = pcf.FoldRequest(
        "a b c d e f g h i j\n",
        profile="safe",
        language="python",
        budget_tokens=3,
        tokenizer=_WhitespaceTokenizer(),
    )
    res = engine.fold_request(req)
    b = res.report.to_dict()["budget"]
    assert b["metric"] == "tokens"
    assert b["exact_tokens"] is True
    assert b["tokenizer"] == "whitespace-tok"


def test_budget_tokens_requires_tokenizer():
    engine = pcf.Engine()
    req = pcf.FoldRequest("a b c\n", profile="safe", language="python", budget_tokens=3)
    with pytest.raises(pcf.InvalidConfigError):
        engine.fold_request(req)
