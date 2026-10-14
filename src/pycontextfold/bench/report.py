"""Self-contained HTML report for an experiment run.

The report is a single ``.html`` file: all CSS (and the tiny bit of JS) is
inlined, there are no external assets, no CDN and no network requests. It can be
opened offline, archived or attached to an issue.

Rendering is deterministic: given the same :class:`~pycontextfold.bench.runs.RunResult`
the output is byte-identical unless the caller passes ``generated_at``. No
timestamp is emitted by default.
"""

from __future__ import annotations

from collections.abc import Iterable
from html import escape

from .models import MetricResult
from .runs import AdapterRun, RunResult

_STYLE = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
       margin: 0; padding: 2rem; background: #fafafa; color: #1a1a1a; }
h1, h2, h3 { line-height: 1.2; }
h1 { font-size: 1.6rem; margin: 0 0 .25rem; }
h2 { font-size: 1.2rem; margin: 2rem 0 .75rem; }
code { background: #ececec; padding: .1rem .3rem; border-radius: 4px; }
table { border-collapse: collapse; width: 100%; margin: .5rem 0 1rem; background: #fff; }
th, td { border: 1px solid #ddd; padding: .35rem .6rem; text-align: left; }
th { background: #f0f0f0; font-weight: 600; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.muted { color: #666; }
.good { color: #0a7d33; }
.warn { color: #b36b00; }
.bad { color: #b00020; }
.na { color: #999; }
.badge { display: inline-block; padding: .05rem .45rem; border-radius: 999px;
         font-size: .8rem; border: 1px solid #ccc; }
.badge.ok { border-color: #0a7d33; color: #0a7d33; }
.badge.fail { border-color: #b00020; color: #b00020; }
.badge.unavail { border-color: #999; color: #666; }
details { margin: .5rem 0; background: #fff; border: 1px solid #ddd; border-radius: 6px; }
summary { cursor: pointer; padding: .6rem .8rem; font-weight: 600; }
details > .body { padding: 0 .8rem .8rem; }
header .meta { color: #444; font-size: .9rem; }
footer { margin-top: 2rem; color: #666; font-size: .85rem; }
@media (prefers-color-scheme: dark) {
  body { background: #121212; color: #e6e6e6; }
  table, details { background: #1c1c1c; }
  th { background: #262626; }
  th, td { border-color: #3a3a3a; }
  code { background: #2a2a2a; }
  footer, .muted, header .meta { color: #aaa; }
}
""".strip()

#: Escape hatch: a tiny script that lets the reader hide unavailable rows.
_SCRIPT = """
(function () {
  var toggle = document.getElementById('hide-unavailable');
  if (!toggle) return;
  toggle.addEventListener('change', function () {
    document.querySelectorAll('tr[data-available="false"]').forEach(function (row) {
      row.style.display = toggle.checked ? 'none' : '';
    });
  });
})();
""".strip()


def _fmt_ratio(value: float) -> str:
    return f"{value * 100:.2f}%"


def _fmt_metric(metric: MetricResult) -> str:
    if not metric.available or metric.value is None:
        detail = escape(metric.detail) if metric.detail else "unavailable"
        return f'<span class="na" title="{detail}">n/a</span>'
    value = metric.value
    if metric.unit == "ratio":
        css = "good" if value > 0 else "muted"
        return f'<span class="{css}">{_fmt_ratio(value)}</span>'
    return f"{value:g}"


def _metric_columns(run: RunResult) -> tuple[str, ...]:
    order: dict[str, None] = {}
    for adapter in run.adapters:
        for name in adapter.aggregate:
            order[name] = None
        for document in adapter.documents:
            for metric in document.metrics:
                order[metric.name] = None
    return tuple(order)


def _status_badge(status: str) -> str:
    if status == "ok":
        return '<span class="badge ok">ok</span>'
    if status == "failed":
        return '<span class="badge fail">failed</span>'
    return f'<span class="badge unavail">{escape(status)}</span>'


def _summary_table(run: RunResult) -> str:
    columns = _metric_columns(run)
    head = (
        "<tr><th>Adapter</th><th>Status</th>"
        "<th class='num'>Docs</th><th class='num'>OK</th><th class='num'>Failed</th>"
        + "".join(f"<th class='num'>{escape(c)}</th>" for c in columns)
        + "</tr>"
    )
    rows = []
    for adapter in run.adapters:
        if adapter.available:
            status = '<span class="badge ok">available</span>'
            docs = str(len(adapter.documents))
            ok = str(adapter.succeeded)
            failed = str(adapter.failed)
        else:
            status = '<span class="badge unavail">unavailable</span>'
            docs = "0"
            ok = "0"
            failed = "0"
        cells = "".join(
            f"<td class='num'>{_fmt_metric(adapter.aggregate.get(c, MetricResult.unavailable(c, 'not computed')))}</td>"
            for c in columns
        )
        rows.append(
            f"<tr><td><code>{escape(adapter.adapter)}</code></td><td>{status}</td>"
            f"<td class='num'>{docs}</td><td class='num'>{ok}</td><td class='num'>{failed}</td>"
            f"{cells}</tr>"
        )
    return f"<table class='summary'><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table>"


def _aggregate_table(adapter: AdapterRun) -> str:
    rows = []
    for name, metric in sorted(adapter.aggregate.items()):
        detail = escape(metric.detail)
        rows.append(
            f"<tr><td><code>{escape(name)}</code></td>"
            f"<td class='num'>{_fmt_metric(metric)}</td>"
            f"<td class='muted'>{detail}</td></tr>"
        )
    return (
        "<table><thead><tr><th>Metric</th><th class='num'>Value</th>"
        "<th>Detail</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _document_table(adapter: AdapterRun) -> str:
    columns = _metric_columns_for_adapter(adapter)
    head = (
        "<tr><th>Document</th><th>Status</th><th class='num'>Output bytes</th>"
        "<th>Lossy</th>"
        + "".join(f"<th class='num'>{escape(c)}</th>" for c in columns)
        + "</tr>"
    )
    rows = []
    for document in adapter.documents:
        if document.status == "ok":
            lossy = "yes" if document.lossy else "no"
            out = str(document.output_bytes) if document.output_bytes is not None else "-"
            cells = "".join(
                f"<td class='num'>{_fmt_metric(document.metric(c) or MetricResult.unavailable(c, 'not computed'))}</td>"
                for c in columns
            )
        else:
            lossy = "-"
            out = "-"
            cells = "".join("<td class='num na'>-</td>" for _ in columns)
        error = (
            f' <span class="muted" title="{escape(document.error)}">(!)</span>'
            if document.error
            else ""
        )
        available = "true" if document.status == "ok" else "false"
        rows.append(
            f'<tr data-available="{available}">'
            f"<td><code>{escape(document.document_id)}</code>{error}</td>"
            f"<td>{_status_badge(document.status)}</td>"
            f"<td class='num'>{out}</td><td>{lossy}</td>{cells}</tr>"
        )
    return (
        "<table><thead>" + head + "</thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _metric_columns_for_adapter(adapter: AdapterRun) -> tuple[str, ...]:
    order: dict[str, None] = {}
    for name in adapter.aggregate:
        order[name] = None
    for document in adapter.documents:
        for metric in document.metrics:
            order[metric.name] = None
    return tuple(order)


def _adapter_section(adapter: AdapterRun) -> str:
    state = "available" if adapter.available else "unavailable"
    error = (
        f'<p class="bad">Error: {escape(adapter.error)}</p>' if adapter.error else ""
    )
    doc_table = _document_table(adapter) if adapter.documents else "<p class='muted'>No documents were processed.</p>"
    return (
        "<details open><summary>{name} <span class='badge {css}'>{state}</span>"
        " <span class='muted'>v{version}</span></summary><div class='body'>"
        "{error}<h3>Aggregate metrics</h3>{agg}<h3>Documents</h3>{docs}"
        "</div></details>"
    ).format(
        name=escape(adapter.adapter),
        css="ok" if adapter.available else "unavail",
        state=state,
        version=escape(adapter.version),
        error=error,
        agg=_aggregate_table(adapter),
        docs=doc_table,
    )


def _metadata_rows(run: RunResult) -> str:
    experiment = run.experiment or {}
    rows: list[tuple[str, str]] = [
        ("Experiment", str(experiment.get("name", "-"))),
        ("Dataset", f"{run.dataset} (v{run.dataset_version})"),
        ("Seed", str(run.seed)),
        ("Dataset hash", run.dataset_hash),
        ("Config hash", run.config_hash),
        ("Run schema", str(run.schema_version)),
    ]
    for adapter in run.adapters:
        rows.append((f"Adapter: {adapter.adapter}", f"v{adapter.version}"))
    items = "".join(
        f"<tr><th>{escape(k)}</th><td><code>{escape(v)}</code></td></tr>" for k, v in rows
    )
    return f"<table class='meta'><tbody>{items}</tbody></table>"


def render_report(
    run: RunResult,
    *,
    title: str | None = None,
    generated_at: str | None = None,
) -> str:
    """Render a :class:`RunResult` as a single self-contained HTML document."""
    experiment = run.experiment or {}
    heading = title or f"PyContextFold benchmark: {experiment.get('name', run.dataset)}"
    subtitle = (
        f"Dataset <strong>{escape(run.dataset)}</strong> · "
        f"{len(run.adapters)} adapter(s) · seed {run.seed}"
    )
    stamp = (
        f'<p class="muted">Generated: {escape(generated_at)}</p>' if generated_at else ""
    )
    sections = "".join(_adapter_section(a) for a in run.adapters)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(heading)}</title>
<style>
{_STYLE}
</style>
</head>
<body>
<header>
<h1>{escape(heading)}</h1>
<p class="meta">{subtitle}</p>
{stamp}
</header>

<h2>Summary</h2>
{_summary_table(run)}

<h2>Adapters</h2>
<p><label><input type="checkbox" id="hide-unavailable"> Hide failed/unavailable document rows</label></p>
{sections}

<footer>
<h2>Reproduction metadata</h2>
{_metadata_rows(run)}
<p>PyContextFold reports are deterministic: no timestamp is embedded unless
explicitly provided. Unavailable metrics are shown as <span class="na">n/a</span>
and are never substituted with an approximation.</p>
</footer>
<script>
{_SCRIPT}
</script>
</body>
</html>
"""


def write_report(
    run: RunResult,
    path: str,
    *,
    title: str | None = None,
    generated_at: str | None = None,
) -> None:
    """Write the report to ``path`` as UTF-8 HTML with a trailing newline."""
    from pathlib import Path

    html = render_report(run, title=title, generated_at=generated_at)
    Path(path).write_text(html + "\n", encoding="utf-8")


def render_metric_rows(metrics: Iterable[MetricResult]) -> str:
    """Small helper used by tests and callers: render metric results as table rows."""
    return "".join(
        f"<tr><td>{escape(m.name)}</td><td>{_fmt_metric(m)}</td></tr>"
        for m in metrics
    )


__all__ = ["render_metric_rows", "render_report", "write_report"]
