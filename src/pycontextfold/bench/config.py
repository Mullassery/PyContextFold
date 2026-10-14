"""Experiment configuration loading and validation.

JSON is always supported. TOML is supported when :mod:`tomllib` is available
(Python 3.11+). No third-party parser is required.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ExperimentConfig


class ConfigError(ValueError):
    """Raised when a configuration cannot be parsed or validated."""


def config_from_dict(data: dict[str, Any]) -> ExperimentConfig:
    if not isinstance(data, dict):
        raise ConfigError("configuration must be a mapping")
    missing = [key for key in ("name", "dataset", "adapters") if key not in data]
    if missing:
        raise ConfigError(f"configuration missing required key(s): {', '.join(missing)}")
    try:
        return ExperimentConfig.from_dict(data)
    except (TypeError, ValueError) as exc:
        raise ConfigError(str(exc)) from exc


def config_to_dict(config: ExperimentConfig) -> dict[str, Any]:
    return config.to_dict()


def config_from_json(text: str) -> ExperimentConfig:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON configuration: {exc}") from exc
    return config_from_dict(data)


def config_to_json(config: ExperimentConfig, *, indent: int | None = 2) -> str:
    return json.dumps(config.to_dict(), indent=indent, sort_keys=False)


def _parse_toml(text: str) -> dict[str, Any]:
    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError as exc:  # pragma: no cover - 3.10 fallback
        raise ConfigError(
            "TOML configuration requires Python 3.11+ (tomllib); "
            "use JSON instead"
        ) from exc
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML configuration: {exc}") from exc


def load_config(path: str | Path) -> ExperimentConfig:
    """Load a configuration from a ``.json`` or ``.toml`` file."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        return config_from_json(text)
    if suffix == ".toml":
        return config_from_dict(_parse_toml(text))
    # Fall back to content sniffing.
    stripped = text.lstrip()
    if stripped.startswith("{"):
        return config_from_json(text)
    return config_from_dict(_parse_toml(text))


__all__ = [
    "ConfigError",
    "config_from_dict",
    "config_from_json",
    "config_to_dict",
    "config_to_json",
    "load_config",
]
