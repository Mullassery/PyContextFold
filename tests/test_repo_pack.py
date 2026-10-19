"""Repository packing tests on a synthetic tree."""

from __future__ import annotations

from pathlib import Path

import pycontextfold as pcf


def _repo(tmp_path: Path) -> Path:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "app.py").write_text("# c\ndef add(a, b):\n    return a + b\n")
    (tmp_path / "README.md").write_text("# Demo\n\nSome docs.\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("ignored")
    (tmp_path / "binary.bin").write_bytes(b"\x00\x01")
    (tmp_path / ".gitignore").write_text("*.log\n")
    (tmp_path / "debug.log").write_text("ignored")
    return tmp_path


def test_pack_discovers_text_and_respects_ignores(tmp_path):
    root = _repo(tmp_path)
    pack = pcf.pack_repository(root, profile="safe", model="gpt-4o")
    paths = {f.path for f in pack.files}
    assert "pkg/app.py" in paths
    assert "README.md" in paths
    assert "node_modules/x.js" not in paths
    assert "debug.log" not in paths
    assert "binary.bin" not in paths
    assert "def add" in pack.bundle


def test_pack_is_deterministic(tmp_path):
    root = _repo(tmp_path)
    a = pcf.pack_repository(root, profile="safe")
    b = pcf.pack_repository(root, profile="safe")
    assert a.bundle == b.bundle
    assert [f.path for f in a.files] == [f.path for f in b.files]


def test_write_pack(tmp_path):
    pack = pcf.pack_repository(_repo(tmp_path), profile="safe")
    out = tmp_path / "bundle.md"
    manifest = tmp_path / "manifest.txt"
    pcf.write_pack(pack, out, manifest)
    assert "def add" in out.read_text()
    assert "pkg/app.py" in manifest.read_text()


def test_pack_without_tokenizer_still_packs(tmp_path, monkeypatch):
    from pycontextfold import repo, tokenizers

    def unavailable(*args, **kwargs):
        raise tokenizers.TokenizerUnavailable("no tokenizer installed")

    monkeypatch.setattr(repo, "tokenizer_for", unavailable)
    pack = pcf.pack_repository(_repo(tmp_path), profile="safe", model="gpt-4o")
    assert "pkg/app.py" in {f.path for f in pack.files}
    assert all(f.tokens_out is None for f in pack.files)
    assert "tokens=unknown" in pack.manifest
