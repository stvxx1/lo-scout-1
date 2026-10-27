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
def isolated_home(request, tmp_path, monkeypatch):
    """Give each test its own data directory and no API credentials.

    ``LO_SCOUT_SECRETS_DIR`` matters as much as ``LO_SCOUT_HOME``: without it the
    key resolver would find the developer's real ``.streamlit/secrets.toml`` and
    any test that forgot to stub the network would start calling ThePornDB.
    Live tests are the exception -- their whole job is to use the real thing.
    """
    monkeypatch.setenv("LO_SCOUT_HOME", str(tmp_path))
    if request.node.get_closest_marker("live"):
        monkeypatch.delenv("LO_SCOUT_SECRETS_DIR", raising=False)
        return tmp_path

    monkeypatch.setenv("LO_SCOUT_SECRETS_DIR", str(tmp_path))
    monkeypatch.delenv("PORNDB_API_KEY", raising=False)
    monkeypatch.delenv("STASHDB_API_KEY", raising=False)
    return tmp_path
