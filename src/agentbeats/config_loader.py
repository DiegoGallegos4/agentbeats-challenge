"""TOML-first configuration loader with optional env expansion and overrides."""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # Python 3.10 fallback
    import tomli as tomllib  # type: ignore


DEFAULT_CONFIG_PATH = Path("config/agentbeats.toml")
ENV_CONFIG_PATH = os.getenv("AGENTBEATS_CONFIG")
CONFIG_PATH = Path(ENV_CONFIG_PATH) if ENV_CONFIG_PATH else DEFAULT_CONFIG_PATH
_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _expand_env(value: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        var = match.group(1)
        return os.getenv(var, "")

    return _ENV_PATTERN.sub(_replace, value)


def _expand(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _expand(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand(v) for v in obj]
    if isinstance(obj, str):
        return _expand_env(obj)
    return obj


@lru_cache(maxsize=1)
def load_toml_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load and cache TOML config, expanding ${ENV_VAR} placeholders."""
    path = Path(config_path) if config_path else CONFIG_PATH
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    return _expand(data)


def get_config_value(keys: Iterable[str], default: Any = None, env_fallback: Optional[str] = None) -> Any:
    """
    Resolve a config value using nested keys (config first, optional env fallback).

    keys: iterable path like ["tools", "alpha_vantage", "api_key"]
    default: returned when not found
    env_fallback: if set, use this env var when config is missing
    """
    config = load_toml_config()
    node: Any = config
    for key in keys:
        if isinstance(node, dict) and key in node:
            node = node[key]
        else:
            node = None
            break
    if node is not None:
        return node
    if env_fallback:
        env_val = os.getenv(env_fallback)
        if env_val:
            return env_val
    return default
