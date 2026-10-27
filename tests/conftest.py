"""Shared test setup.

Every writable path in the app goes through ``paths.data_dir()``, which honours
``LO_SCOUT_HOME``. Pointing that at a temp directory per test keeps the sqlite
database and the thumbnail cache out of the developer's real home directory.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "lo-scout"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Give each test its own data directory."""
    monkeypatch.setenv("LO_SCOUT_HOME", str(tmp_path))
    return tmp_path
