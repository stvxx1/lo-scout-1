"""ThePornDB performer metadata (needs an API key).

The only source here that requires a key, and the only one that carries real
metadata: ThePornDB has portraits, stats, aliases, measurements and a bio for
each performer, which is exactly what the Freeones *listing* pages leave blank
(they return a name and a portrait, nothing more).

The key is never written into this repository. It is read, in order, from the
``PORNDB_API_KEY`` environment variable, ``$LO_SCOUT_HOME/secrets.toml``, and
``.streamlit/secrets.toml`` beside the working directory, the app, or the user's
home. Without a key every function here degrades to "no metadata" rather than
raising, so the grid keeps working for people who never configure one.
"""

import os
import re
import tomllib
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote

import requests

import storage

API_ROOT = "https://api.theporndb.net"
TIMEOUT = 15
CACHE_TTL = 24 * 3600

_KEY_ENV = "PORNDB_API_KEY"


# --- credentials ----------------------------------------------------------

def _secret_files() -> List[Path]:
    """Return the places a key may live, most specific first.

    ``LO_SCOUT_SECRETS_DIR`` pins the search to a single directory; the tests use
    it so a developer's real key on disk can never leak into an offline run.
    """
    override = os.environ.get("LO_SCOUT_SECRETS_DIR")
    if override:
        return [Path(override) / "secrets.toml"]

    app_dir = Path(__file__).resolve().parents[1]
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


def _key_from_toml(path: Path) -> Optional[str]:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None

    for key in (_KEY_ENV, "porndb_api_key"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    section = data.get("porndb")
    if isinstance(section, dict):
        value = section.get("api_key")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def api_key() -> Optional[str]:
    """Return the configured key, or ``None`` when there isn't one."""
    from_env = (os.environ.get(_KEY_ENV) or "").strip()
    if from_env:
        return from_env
    for path in _secret_files():
        key = _key_from_toml(path)
        if key:
            return key
    return None


def is_configured() -> bool:
    return api_key() is not None


# --- transport ------------------------------------------------------------

def _get_json(url: str, key: str) -> Any:
    response = requests.get(
        url, headers={"Authorization": f"Bearer {key}", "Accept": "application/json"}, timeout=TIMEOUT
    )
    response.raise_for_status()
    return response.json()


# --- parsing --------------------------------------------------------------

def normalise_name(name: str) -> str:
    """Fold a stage name to a comparable form ("Sara-Jay " == "sara jay")."""
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def _profile(entry: Any) -> Optional[Dict[str, Any]]:
    """Flatten one API record into the handful of fields the UI shows."""
    if not isinstance(entry, dict):
        return None
    name = (entry.get("name") or entry.get("full_name") or "").strip()
    if not name:
        return None

    extras = entry.get("extras") if isinstance(entry.get("extras"), dict) else {}
    raw_links = extras.get("links") if isinstance(extras.get("links"), dict) else {}

    aliases = [a.strip() for a in (entry.get("aliases") or []) if isinstance(a, str) and a.strip()]

    return {
        "id": str(entry.get("id") or ""),
        "slug": entry.get("slug") or "",
        "name": name,
        "bio": (entry.get("bio") or "").strip(),
        "rating": entry.get("rating"),
        "aliases": aliases,
        "image": entry.get("image") or "",
        "face": entry.get("face") or "",
        "thumb": entry.get("thumbnail") or "",
        "extras": extras,
        "links": {
            str(label): str(url)
            for label, url in raw_links.items()
            if isinstance(url, str) and url.startswith("http")
        },
    }


def parse_search(payload: Any, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Map a /performers response to profiles (never raises)."""
    entries = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        return []

    profiles = []
    for entry in entries:
        profile = _profile(entry)
        if profile:
            profiles.append(profile)
        if limit is not None and len(profiles) >= limit:
            break
    return profiles


def best_match(profiles: Iterable[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    """Pick the profile that really is ``name``.

    The endpoint is a fuzzy text search: asking for "Sara Jay" also returns
    "Sara Fay", so an exact name match wins, then an exact alias (performer
    pages list every name she has worked under), then a containment match.
    """
    profiles = list(profiles or [])
    needle = normalise_name(name)
    if not needle:
        return profiles[0] if profiles else None

    for profile in profiles:
        if normalise_name(profile.get("name", "")) == needle:
            return profile
    for profile in profiles:
        if any(normalise_name(alias) == needle for alias in profile.get("aliases", [])):
            return profile
    for profile in profiles:
        candidate = normalise_name(profile.get("name", ""))
        if candidate and (needle in candidate or candidate in needle):
            return profile
    return None


# --- lookup ---------------------------------------------------------------

def search(name: str, limit: int = 4, use_cache: bool = True) -> List[Dict[str, Any]]:
    """Return candidate profiles for ``name`` (empty when unconfigured/offline)."""
    key = api_key()
    if not key:
        return []

    cache_key = f"porndb:{normalise_name(name)}"
    if use_cache:
        cached = storage.cache_get(cache_key)
        if cached is not None:
            return cached

    url = f"{API_ROOT}/performers?q={quote(name)}&per_page={limit}"
    try:
        payload = _get_json(url, key)
    except (requests.RequestException, ValueError):
        return []  # offline, rate-limited or a bad key: no metadata, no crash

    profiles = parse_search(payload, limit)
    storage.cache_set(cache_key, profiles, CACHE_TTL)
    return profiles


def lookup(name: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """Return the single best profile for ``name``, or ``None``."""
    return best_match(search(name, use_cache=use_cache), name)


# --- enrichment -----------------------------------------------------------

def _centimetres(value: Any) -> Optional[int]:
    """Parse "163cm" / "68kg" / 163 into a plain integer."""
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return int(float(match.group())) if match else None


def age_from(birthday: Any) -> Optional[int]:
    """Return a performer's current age from an ISO birthday, or ``None``."""
    try:
        born = date.fromisoformat(str(birthday)[:10])
    except (TypeError, ValueError):
        return None
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def portrait(profile: Dict[str, Any]) -> str:
    """Return the best available portrait URL from a profile."""
    return profile.get("image") or profile.get("face") or profile.get("thumb") or ""


def enrich(performer, profile: Optional[Dict[str, Any]] = None):
    """Fill a performer's blank fields from ThePornDB, in place.

    Freeones always wins: the listing is what the user is looking at, and it
    stays consistent with the page the card links back to. This only supplies
    values Freeones left empty.
    """
    if profile is None:
        profile = lookup(performer.name)
    if not profile:
        return performer

    extras = profile.get("extras", {})

    if not performer.image_url:
        performer.image_url = portrait(profile)
    if performer.height is None:
        performer.height = _centimetres(extras.get("height"))
    if performer.weight is None:
        performer.weight = _centimetres(extras.get("weight"))
    if performer.age is None:
        performer.age = age_from(extras.get("birthday"))
    if not performer.gender:
        performer.gender = (extras.get("gender") or "").strip().lower()
    if not performer.ethnicity:
        performer.ethnicity = extras.get("ethnicity") or None
    if not performer.measurements:
        performer.measurements = extras.get("measurements") or None
    if not performer.hair_color:
        performer.hair_color = extras.get("hair_colour") or None
    if not performer.eye_color:
        performer.eye_color = extras.get("eye_colour") or None
    return performer


def enrich_portraits(performers: Iterable[Any], limit: int = 6) -> int:
    """Give portraits to cards whose own image is missing.

    Deliberately bounded: the grid shows ~24 performers and spending a request
    on each at first paint is unacceptable, but the portrait is the one field a
    broken source actually loses. Returns how many were filled.
    """
    if not is_configured():
        return 0

    filled = 0
    for performer in performers:
        if filled >= limit:
            break
        if getattr(performer, "image_url", ""):
            continue
        try:
            enrich(performer)
            if performer.image_url:
                filled += 1
        except Exception:
            continue
    return filled
