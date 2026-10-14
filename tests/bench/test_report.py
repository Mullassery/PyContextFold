from __future__ import annotations

from pathlib import Path

from pycontextfold.bench.models import MetricResult
from pycontextfold.bench.report import render_metric_rows, render_report, write_report
from pycontextfold.bench.runs import AdapterRun, DocumentRun, RunResult


def _run() -> RunResult:
    docs = (
        DocumentRun(
            document_id="py-basic",
            adapter="contextfold",
            method="safe",
            status="ok",
            metrics=(
                MetricResult(name="size_reduction", value=0.25, unit="ratio"),
                MetricResult.unavailable("exact_tokens", "no tokenizer"),
            ),
            output_bytes=100,
            lossy=False,
        ),
        DocumentRun(
            document_id="bad",
            adapter="contextfold",
            status="failed",
            error="<script>alert(1)</script>",
        ),
    )
    adapter = AdapterRun(
        adapter="contextfold",
        version="0.1.0",
        documents=docs,
        aggregate={
            "size_reduction": MetricResult(name="size_reduction", value=0.25, unit="ratio"),
            "exact_tokens": MetricResult.unavailable("exact_tokens", "no tokenizer"),
        },
    )
    return RunResult(
        experiment={"name": "demo"},
        dataset="synthetic",
        dataset_version="1",
        dataset_hash="abc123",
        config_hash="def456",
        seed=0,
        adapters=(adapter,),
    )


def test_render_is_self_contained_html():
    html = render_report(_run())
    assert html.startswith("<!doctype html>")
    assert html.rstrip().endswith("</html>")
    assert "<style>" in html
    assert "<script>" in html


def test_render_has_no_external_assets():
    html = render_report(_run())
    for forbidden in ("http://", "https://", "<link", "src="):
        assert forbidden not in html


def test_render_is_deterministic():
    a = render_report(_run())
    b = render_report(_run())
    assert a == b


def test_generated_at_is_optional_and_rendered():
    assert "Generated:" not in render_report(_run())
    assert "Generated: 2026-01-01" in render_report(_run(), generated_at="2026-01-01")


def test_unavailable_metrics_shown_as_na():
    html = render_report(_run())
    assert "n/a" in html
    assert "no tokenizer" in html


def test_html_is_escaped():
    html = render_report(_run())
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_failed_document_row_marked_unavailable():
    html = render_report(_run())
    assert 'data-available="false"' in html
    assert 'data-available="true"' in html


def test_metadata_present():
    html = render_report(_run())
    assert "abc123" in html
    assert "def456" in html
    assert "Reproduction metadata" in html


def test_custom_title():
    html = render_report(_run(), title="My Report")
    assert "<title>My Report</title>" in html


def test_write_report(tmp_path: Path):
    target = tmp_path / "report.html"
    write_report(_run(), target)
    content = target.read_text(encoding="utf-8")
    assert content.startswith("<!doctype html>")
    assert content.endswith("\n")


def test_render_metric_rows():
    rows = render_metric_rows(
        [MetricResult(name="x", value=0.5, unit="ratio"), MetricResult.unavailable("y", "why")]
    )
    assert "<tr>" in rows
    assert "50.00%" in rows
    assert "n/a" in rows
