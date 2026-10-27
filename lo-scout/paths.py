"""Filesystem locations owned by lo-scout.

Everything writable lives under a single directory so it can be inspected or
deleted wholesale. ``LO_SCOUT_HOME`` overrides the default location, which is
what the tests use to keep their cache out of the real home directory.
"""

import os
from pathlib import Path


def data_dir() -> Path:
    """Return (creating if needed) the application data directory."""
    override = os.environ.get("LO_SCOUT_HOME")
    path = Path(override) if override else Path.home() / ".lo-scout"
    path.mkdir(parents=True, exist_ok=True)
    return path


def thumbs_dir() -> Path:
    """Return (creating if needed) the directory holding downscaled portraits."""
    path = data_dir() / "thumbs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    """Return the sqlite database path."""
    return data_dir() / "lo-scout.db"
