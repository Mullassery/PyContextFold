"""Command-line interface for the benchmark platform.

Subcommands:

- ``run``       — execute an experiment from a config file; optionally write a
  run artifact, an HTML report and evaluate quality gates.
- ``report``    — render an existing run artifact as a self-contained HTML report.
- ``gates``     — evaluate gate thresholds from a config against a run artifact.
- ``adapters``  — list adapters, their capabilities and availability.
- ``datasets``  — write or print the built-in synthetic dataset.

Only the standard library is used. Invoke as ``python -m pycontextfold.bench``.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .adapters import default_registry
from .config import ConfigError, load_config
from .dataset import dataset_to_json, load_dataset, synthetic_dataset
from .gates import evaluate_gates, thresholds_from_config
from .report import write_report
from .runner import Runner
from .runs import read_run, write_run

_GATE_FAILURE_EXIT = 1
_USAGE_ERROR_EXIT = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pycontextfold-bench",
        description="Offline benchmark harness for PyContextFold.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run an experiment from a config file")
    run.add_argument("--config", required=True, help="experiment config (.json/.toml)")
    run.add_argument("--dataset", default=None, help="dataset path or 'synthetic'")
    run.add_argument("--method", default=None, help="profile/method override")
    run.add_argument("--out", default=None, help="write the run artifact here (.json)")
    run.add_argument("--report", default=None, help="write an HTML report here")
    run.add_argument(
        "--gate",
        action="store_true",
        help="evaluate gates from the config and exit non-zero on failure",
    )

    report = sub.add_parser("report", help="render a run artifact as HTML")
    report.add_argument("run", help="run artifact (.json)")
    report.add_argument("--out", required=True, help="output .html path")
    report.add_argument("--title", default=None)

    gates = sub.add_parser("gates", help="evaluate gates from a config against a run")
    gates.add_argument("run", help="run artifact (.json)")
    gates.add_argument("--config", required=True, help="config with gate thresholds")

    sub.add_parser("adapters", help="list adapters and capabilities")
    sub.add_parser("datasets", help="print or write the synthetic dataset")
    # attach dataset options
    datasets = sub.choices["datasets"]
    datasets.add_argument("--out", default=None, help="write dataset JSON here")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            return _cmd_run(args)
        if args.command == "report":
            return _cmd_report(args)
        if args.command == "gates":
            return _cmd_gates(args)
        if args.command == "adapters":
            return _cmd_adapters(args)
        if args.command == "datasets":
            return _cmd_datasets(args)
    except (ConfigError, FileNotFoundError, KeyError, ValueError) as exc:
        print(f"error: {exc}")
        return _USAGE_ERROR_EXIT
    parser.error(f"unknown command {args.command!r}")
    return _USAGE_ERROR_EXIT


def _resolve_dataset(reference: str):
    if reference == "synthetic" or reference == "":
        return synthetic_dataset()
    path = Path(reference)
    if path.exists():
        return load_dataset(path)
    if reference in {"synthetic"}:
        return synthetic_dataset()
    raise FileNotFoundError(f"dataset not found: {reference}")


def _cmd_run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    dataset = _resolve_dataset(args.dataset or config.dataset)
    run = Runner().run(dataset, config, method=args.method)

    print(
        f"experiment {config.name!r}: {len(run.adapters)} adapter(s) on "
        f"{len(dataset)} document(s)"
    )
    for adapter in run.adapters:
        state = "available" if adapter.available else "unavailable"
        print(
            f"  {adapter.adapter:20} {state:11} ok={adapter.succeeded} "
            f"failed={adapter.failed}"
        )

    if args.out:
        write_run(run, args.out)
        print(f"wrote run artifact: {args.out}")
    if args.report:
        write_report(run, args.report)
        print(f"wrote report: {args.report}")

    thresholds = thresholds_from_config(config)
    if args.gate or thresholds:
        return _report_gates(run, thresholds) if thresholds else _no_gates()
    return 0


def _no_gates() -> int:
    print("no gates configured")
    return 0


def _report_gates(run, thresholds) -> int:
    report = evaluate_gates(run, thresholds)
    for outcome in report.outcomes:
        status = "PASS" if outcome.passed else "FAIL"
        value = "n/a" if outcome.value is None else f"{outcome.value:.4g}"
        print(f"  gate {status} {outcome.adapter}/{outcome.metric}={value} ({outcome.reason})")
    if not report.passed:
        print(f"gates failed: {len(report.failures())} of {len(report.outcomes)}")
        return _GATE_FAILURE_EXIT
    print(f"gates passed: {len(report.outcomes)}")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    run = read_run(args.run)
    write_report(run, args.out, title=args.title)
    print(f"wrote report: {args.out}")
    return 0


def _cmd_gates(args: argparse.Namespace) -> int:
    run = read_run(args.run)
    config = load_config(args.config)
    thresholds = thresholds_from_config(config)
    if not thresholds:
        print("no gates configured")
        return 0
    return _report_gates(run, thresholds)


def _cmd_adapters(args: argparse.Namespace) -> int:
    registry = default_registry()
    print(f"{len(registry)} adapters:")
    for info in registry.infos():
        avail = "available" if info.available else "unavailable"
        caps = ", ".join(info.capabilities.values()) or "-"
        detail = f"  ({info.detail})" if info.detail else ""
        print(f"  {info.name:20} v{info.version:8} {avail:11} [{caps}]{detail}")
    return 0


def _cmd_datasets(args: argparse.Namespace) -> int:
    dataset = synthetic_dataset()
    if args.out:
        Path(args.out).write_text(dataset_to_json(dataset) + "\n", encoding="utf-8")
        print(f"wrote dataset: {args.out}")
    else:
        print(dataset_to_json(dataset))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
