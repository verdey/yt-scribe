"""Configuration file support for yt-scribe.

Loads defaults from .yt-scribe.toml if present. CLI flags always override.
Searches for config in: current directory, then home directory.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

log = logging.getLogger("yt-scribe")

CONFIG_FILENAME = ".yt-scribe.toml"

KNOWN_KEYS = {"output", "languages", "enrich", "format"}


def find_config() -> Path | None:
    """Search for .yt-scribe.toml in cwd then home directory.

    Returns the path to the first config file found, or None.
    """
    candidates = [
        Path.cwd() / CONFIG_FILENAME,
        Path.home() / CONFIG_FILENAME,
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def load_config(path: Path | None = None) -> dict:
    """Load and parse a .yt-scribe.toml config file.

    If *path* is None, searches for a config file using find_config().
    Returns an empty dict if no config file is found, if the TOML parser
    is unavailable, or if the file cannot be parsed.
    """
    if tomllib is None:
        log.debug("TOML parser not available, skipping config file")
        return {}

    if path is None:
        path = find_config()

    if path is None:
        return {}

    try:
        with open(path, "rb") as f:
            config = tomllib.load(f)
    except Exception as e:
        log.warning("Failed to parse config file %s: %s", path, e)
        return {}

    # Warn on unknown keys
    for key in config:
        if key not in KNOWN_KEYS:
            log.warning("Unknown config key '%s' in %s", key, path)

    # Expand ~ in output path
    if "output" in config and isinstance(config["output"], str):
        config["output"] = str(Path(config["output"]).expanduser())

    log.debug("Loaded config from %s: %s", path, config)
    return config


# Hardcoded defaults that match the original CLI behavior.
_HARDCODED_DEFAULTS: dict[str, object] = {
    "lang": ["en"],
    "enrich": False,
    "output": None,  # cli.py handles its own default (./transcripts/)
}

# Maps config-file key -> argparse attribute name.
_CONFIG_KEY_TO_ARG = {
    "languages": "lang",
    "enrich": "enrich",
    "output": "output",
}


def apply_config_defaults(args: argparse.Namespace, config: dict) -> None:
    """Apply config-file defaults to any CLI arg that is still None.

    Precedence: CLI flag > config file > hardcoded default.
    """
    for config_key, arg_name in _CONFIG_KEY_TO_ARG.items():
        current = getattr(args, arg_name, None)
        if current is not None:
            continue  # user passed an explicit CLI flag

        if config_key in config:
            value = config[config_key]
            # Coerce output to Path
            if arg_name == "output" and isinstance(value, str):
                value = Path(value)
            setattr(args, arg_name, value)
        else:
            # Fall back to hardcoded default
            default = _HARDCODED_DEFAULTS.get(arg_name)
            if default is not None:
                setattr(args, arg_name, default)
