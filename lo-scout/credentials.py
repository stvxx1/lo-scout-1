"""Where the API keys live, for every source that needs one.

Keys are never written into this repository. A key is read, in order, from its
environment variable, ``$LO_SCOUT_HOME/secrets.toml``, and
``.streamlit/secrets.toml`` beside the working directory, the app, or the user's
home -- all gitignored or outside the tree.

``LO_SCOUT_SECRETS_DIR`` pins the search to a single directory. The tests use it
so a developer's real key on disk can never leak into an offline run; without
it, a test that merely forgot to stub a lookup would reach the live API.
"""

import os
import tomllib
from pathlib import Path
from typing import List, Optional


def secret_files() -> List[Path]:
    """Return the places a key may live, most specific first."""
    override = os.environ.get("LO_SCOUT_SECRETS_DIR")
    if override:
        return [Path(override) / "secrets.toml"]

    app_dir = Path(__file__).resolve().parent
    candidates = []
    home = os.environ.get("LO_SCOUT_HOME")
    if home:
        candidates.append(Path(home) / "secrets.toml")
    candidates.extend(
        [
            Path.cwd() / ".streamlit" / "secrets.toml",
            app_dir / ".streamlit" / "secrets.toml",
            app_dir.parent / ".streamlit" / "secrets.toml",
            Path.home() / ".streamlit" / "secrets.toml",
        ]
    )
    return candidates


def _value(mapping: dict, key: str) -> Optional[str]:
    value = mapping.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _from_toml(path: Path, name: str) -> Optional[str]:
    """Return ``name`` from one TOML file, accepting both flat and sectioned keys.

    ``PORNDB_API_KEY`` may be spelled ``PORNDB_API_KEY``, ``porndb_api_key`` or
    ``[porndb] api_key``; people write all three and none is wrong.
    """
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None

    for key in (name, name.lower()):
        value = _value(data, key)
        if value:
            return value

    section_name, _, leaf = name.partition("_")
    section = data.get(section_name.lower())
    if isinstance(section, dict):
        for key in (leaf.lower(), "api_key"):
            value = _value(section, key)
            if value:
                return value
    return None


def read(name: str) -> Optional[str]:
    """Return the key called ``name`` (e.g. ``PORNDB_API_KEY``), or ``None``."""
    from_env = (os.environ.get(name) or "").strip()
    if from_env:
        return from_env
    for path in secret_files():
        value = _from_toml(path, name)
        if value:
            return value
    return None


def is_set(name: str) -> bool:
    """Return whether a key called ``name`` is configured anywhere."""
    return read(name) is not None
