"""StashDB performer metadata (optional API key).

StashDB runs stash-box, so everything goes through one GraphQL endpoint;
introspection is public but the data queries answer "not authorized" without a
key from your StashDB account settings, sent as an ``ApiKey`` header.

This is a second opinion, not a duplicate of ThePornDB: stash-box records carry
the numeric details StashDB users curate (band/waist/hip as separate integers,
career start year, scene count) and a scene-linked portrait. The dialog shows it
beside the ThePornDB profile, and any disagreement is information.

Scope is deliberately the dialog only: the grid's portrait backfill stays
ThePornDB's job, so a page load never fans out to two keyed services.
"""

import re
from typing import Any, Dict, List, Optional

import requests

import credentials
import storage

ENDPOINT = "https://stashdb.org/graphql"
SITE = "https://stashdb.org/performers"
TIMEOUT = 20
CACHE_TTL = 24 * 3600
PAGE_SIZE = 10

_KEY_ENV = "STASHDB_API_KEY"

_FIELDS = """
  id
  name
  aliases
  birth_date
  ethnicity
  country
  eye_color
  hair_color
  height
  cup_size
  band_size
  waist_size
  hip_size
  career_start_year
  scene_count
  images { url width height }
"""

QUERY = (
    "query($names: String!, $perPage: Int!) {"
    " queryPerformers(input: {names: $names, per_page: $perPage}) {"
    " count performers {" + _FIELDS + "} } }"
)

# stash-box has no free-text "close enough" mode to hide behind: the enum is the
# whole vocabulary, so an unknown value is dropped rather than guessed.
_SKIP_ENUMS = {"", "UNKNOWN"}


# --- credentials ----------------------------------------------------------

def api_key() -> Optional[str]:
    return credentials.read(_KEY_ENV)


def is_configured() -> bool:
    return credentials.is_set(_KEY_ENV)


# --- transport ------------------------------------------------------------

def _post(query: str, variables: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
    """Run one GraphQL query and return its ``data`` block, or ``None``.

    stash-box reports unauthorised queries as HTTP 200 with an ``errors`` array,
    so ``raise_for_status`` alone would happily cache an empty result forever.
    """
    response = requests.post(
        ENDPOINT,
        json={"query": query, "variables": variables},
        headers={
            "ApiKey": key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("errors"):
        return None
    data = payload.get("data")
    return data if isinstance(data, dict) else None


# --- parsing --------------------------------------------------------------

def _pretty(value: Any) -> Optional[str]:
    """Turn ``MIDDLE_EASTERN`` into ``Middle Eastern``; drop empty/unknown."""
    text = str(value or "").strip()
    if text.upper() in _SKIP_ENUMS:
        return None
    return text.replace("_", " ").title()


def _aliases(record: Dict[str, Any]) -> List[str]:
    """Return the record's aliases as a list.

    The live schema returns a list (``["Sarah Jay"]``); older stash-box builds
    returned one comma-separated string, and a fixture or a fork may still. Both
    are accepted, because ``str(list)`` would produce ``"['Sarah Jay']"`` -- a
    bracket-quoted alias chip, which is how this was found.
    """
    raw = record.get("aliases")
    if isinstance(raw, list):
        return [str(alias).strip() for alias in raw if str(alias).strip()]
    return [alias.strip() for alias in str(raw or "").split(",") if alias.strip()]


# stash-box stores ``country`` as an ISO code, ThePornDB as a demonym; the two
# tabs sit side by side, so "American" next to "US" reads as a bug. The codes
# that actually show up are mapped and anything else is shown as-is rather than
# run through a table that pretends to be complete.
_DEMONYMS = {
    "AR": "Argentine", "AT": "Austrian", "AU": "Australian", "BR": "Brazilian",
    "CA": "Canadian", "CH": "Swiss", "CL": "Chilean", "CO": "Colombian",
    "CU": "Cuban", "CZ": "Czech", "DE": "German", "DK": "Danish",
    "ES": "Spanish", "FI": "Finnish", "FR": "French", "GB": "British",
    "GR": "Greek", "HU": "Hungarian", "IE": "Irish", "IL": "Israeli",
    "IN": "Indian", "IT": "Italian", "JP": "Japanese", "KR": "Korean",
    "MX": "Mexican", "NL": "Dutch", "NO": "Norwegian", "NZ": "New Zealander",
    "PH": "Filipino", "PL": "Polish", "PR": "Puerto Rican", "PT": "Portuguese",
    "RO": "Romanian", "RS": "Serbian", "RU": "Russian", "SE": "Swedish",
    "SK": "Slovak", "TH": "Thai", "TR": "Turkish", "UA": "Ukrainian",
    "UK": "British", "US": "American", "VE": "Venezuelan", "ZA": "South African",
}


def _nationality(record: Dict[str, Any]) -> Optional[str]:
    code = str(record.get("country") or "").strip().upper()
    if not code:
        return None
    return _DEMONYMS.get(code, code)



def _measurements(record: Dict[str, Any]) -> Optional[str]:
    parts = [record.get("band_size"), record.get("waist_size"), record.get("hip_size")]
    if all(isinstance(part, int) and part > 0 for part in parts):
        return "-".join(str(part) for part in parts)
    return None


def portrait(record: Dict[str, Any]) -> str:
    """Return the largest image URL on a record, or ``""``."""
    images = [image for image in (record.get("images") or []) if image.get("url")]
    if not images:
        return ""
    return max(images, key=lambda image: image.get("width") or 0)["url"]


def to_profile(record: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a stash-box performer into the shape :func:`profile_html` renders.

    Reusing ThePornDB's profile shape keeps one renderer: both sources carry the
    same facts under different names, and a second HTML builder would drift.
    """
    extras: Dict[str, Any] = {}
    height = record.get("height")
    if isinstance(height, int) and height > 0:
        extras["height"] = f"{height}cm"  # ThePornDB's format, since the tabs share a grid
    cup = str(record.get("cup_size") or "").strip()
    band = record.get("band_size")
    if cup and isinstance(band, int) and band > 0:
        extras["cupsize"] = f"{band}{cup}"  # "36E", as ThePornDB writes it
    elif cup:
        extras["cupsize"] = cup
    measurements = _measurements(record)
    if measurements:
        extras["measurements"] = measurements
    for source_key, extra_key in (
        ("ethnicity", "ethnicity"),
        ("hair_color", "hair_colour"),
        ("eye_color", "eye_colour"),
    ):
        pretty = _pretty(record.get(source_key))
        if pretty:
            extras[extra_key] = pretty
    if record.get("birth_date"):
        extras["birthday"] = str(record["birth_date"])[:10]
    nationality = _nationality(record)
    if nationality:
        extras["nationality"] = nationality
    if record.get("career_start_year"):
        extras["career_start_year"] = record["career_start_year"]
    if record.get("scene_count"):
        extras["scenes"] = record["scene_count"]

    profile: Dict[str, Any] = {
        "name": record.get("name") or "",
        "image": portrait(record),
        "extras": extras,
        "aliases": _aliases(record),
        "links": {},
        "source": "StashDB",
    }
    if record.get("id"):
        profile["links"]["StashDB"] = f"{SITE}/{record['id']}"
    return profile


def parse_search(payload: Any, limit: int = PAGE_SIZE) -> List[Dict[str, Any]]:
    """Return normalised profiles from a raw ``queryPerformers`` response."""
    if not isinstance(payload, dict):
        return []
    data = payload.get("data") if "data" in payload else payload
    if not isinstance(data, dict):
        return []
    connection = data.get("queryPerformers")
    if not isinstance(connection, dict):
        return []
    records = connection.get("performers") or []
    return [to_profile(record) for record in records[:limit] if isinstance(record, dict)]


def _normalise(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def best_match(profiles: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    """Return the record that really is ``name``, or ``None``.

    Deliberately stricter than :mod:`porndb`: stash-box name search is fuzzy --
    asking for "Sara Jay" returns "Sara Jaymes" first -- and unlike ThePornDB
    there is no containment pass to fall back on, because a leftover result is
    more likely a different person than a spelling variant. An exact name wins,
    then an exact alias, then a lone result; anything else is no match rather
    than a stranger's stats under this name.
    """
    wanted = _normalise(name)
    if not wanted:
        return None

    for profile in profiles:
        if _normalise(profile.get("name", "")) == wanted:
            return profile
    for profile in profiles:
        if any(_normalise(alias) == wanted for alias in profile.get("aliases") or []):
            return profile
    return profiles[0] if len(profiles) == 1 else None


# --- lookup ---------------------------------------------------------------

def search(name: str, limit: int = PAGE_SIZE, use_cache: bool = True) -> List[Dict[str, Any]]:
    """Return candidate profiles for ``name``, or ``[]`` when unavailable."""
    if not name or not name.strip():
        return []
    key = api_key()
    if not key:
        return []

    cache_key = f"stashdb:search:{_normalise(name)}:{limit}"
    if use_cache:
        cached = storage.cache_get(cache_key)
        if isinstance(cached, list):
            return cached

    try:
        data = _post(QUERY, {"names": name, "perPage": limit}, key)
    except (requests.RequestException, ValueError):
        return []  # offline, rate-limited or a bad key: no metadata, no crash
    if data is None:
        return []  # GraphQL-level error, usually "not authorized"

    profiles = parse_search({"data": data}, limit)
    storage.cache_set(cache_key, profiles, CACHE_TTL)
    return profiles


def lookup(name: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """Return the single best profile for ``name``, or ``None``."""
    return best_match(search(name, use_cache=use_cache), name)
