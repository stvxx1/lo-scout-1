"""Clip search on Eporner and RedTube.

Both sites publish public JSON endpoints that need no key and no HTML scraping,
so they are far sturdier than the Freeones listing. A failure here must never
take the grid down: every search returns an empty list on error and the caller
renders "no clips found".
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import requests

import storage

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
TIMEOUT = 20.0
CACHE_TTL = 6 * 60 * 60  # a stale clip list is harmless; a refetch is cheap

EPORNER_SEARCH = (
    "https://www.eporner.com/api/v2/video/search/"
    "?query={query}&per_page={limit}&thumbsize=big&order=top-weekly&format=json"
)
REDTUBE_SEARCH = (
    "https://api.redtube.com/?data=redtube.Videos.searchVideos"
    "&search={query}&output=json&thumbsize=big"
)


@dataclass
class Video:
    source: str
    id: str
    title: str
    page_url: str
    embed_url: str
    thumb_url: str = ""
    duration: str = ""
    views: Optional[int] = None


def format_views(views: Optional[int]) -> str:
    if not views:
        return ""
    if views >= 1_000_000:
        return f"{views / 1_000_000:.1f}M views"
    if views >= 1_000:
        return f"{views / 1_000:.0f}K views"
    return f"{views} views"


def _get_json(url: str, timeout: float = TIMEOUT) -> Any:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    return response.json()


# --- Eporner --------------------------------------------------------------

def _eporner_thumb(entry: Dict[str, Any]) -> str:
    default = entry.get("default_thumb") or {}
    if isinstance(default, dict) and default.get("src"):
        return default["src"]
    for thumb in entry.get("thumbs") or []:
        if isinstance(thumb, dict) and thumb.get("src"):
            if thumb.get("size") in ("big", "medium"):
                return thumb["src"]
    return ""


def parse_eporner(payload: Any, limit: int = 12) -> List[Video]:
    """Map an Eporner search response to Videos (never raises)."""
    videos = []
    for entry in (payload or {}).get("videos", []) or []:
        if not isinstance(entry, dict):
            continue
        try:
            videos.append(
                Video(
                    source="Eporner",
                    id=str(entry["id"]),
                    title=(entry.get("title") or "").strip(),
                    page_url=entry.get("url") or "",
                    embed_url=entry.get("embed") or "",
                    thumb_url=_eporner_thumb(entry),
                    duration=entry.get("length_min") or "",
                    views=_as_int(entry.get("views")),
                )
            )
        except (KeyError, TypeError):
            continue
        if len(videos) >= limit:
            break
    return videos


# --- RedTube --------------------------------------------------------------

def parse_redtube(payload: Any, limit: int = 12) -> List[Video]:
    """Map a RedTube search response to Videos (never raises)."""
    videos = []
    for wrapper in (payload or {}).get("videos", []) or []:
        if not isinstance(wrapper, dict):
            continue
        entry = wrapper.get("video") or {}
        if not isinstance(entry, dict):
            continue
        try:
            videos.append(
                Video(
                    source="RedTube",
                    id=str(entry["video_id"]),
                    title=(entry.get("title") or "").strip(),
                    page_url=entry.get("url") or "",
                    embed_url=entry.get("embed_url") or "",
                    thumb_url=entry.get("thumb") or entry.get("default_thumb") or "",
                    duration=entry.get("duration") or "",
                    views=_as_int(entry.get("views")),
                )
            )
        except (KeyError, TypeError):
            continue
        if len(videos) >= limit:
            break
    return videos


def _as_int(value: Any) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


# --- relevance and fetching ----------------------------------------------

def rank_by_name(videos: List[Video], name: str) -> List[Video]:
    """Put clips whose title names the performer first.

    Both APIs match on keywords, so a search for "Sara Jay" also returns videos
    that merely tag her. The title is the best signal available, and the API
    order is preserved inside each group.
    """
    needle = name.strip().lower()
    if not needle:
        return videos
    named = [v for v in videos if needle in v.title.lower()]
    rest = [v for v in videos if needle not in v.title.lower()]
    return named + rest


def search_eporner(name: str, limit: int = 12, timeout: float = TIMEOUT) -> List[Video]:
    url = EPORNER_SEARCH.format(query=quote_plus(name), limit=limit)
    try:
        return parse_eporner(_get_json(url, timeout), limit)
    except (requests.RequestException, ValueError):
        return []


def search_redtube(name: str, limit: int = 12, timeout: float = TIMEOUT) -> List[Video]:
    url = REDTUBE_SEARCH.format(query=quote_plus(name))
    try:
        # The RedTube endpoint has no page-size parameter, so trim afterwards.
        return parse_redtube(_get_json(url, timeout), limit)
    except (requests.RequestException, ValueError):
        return []


def search_all(name: str, limit: int = 8, use_cache: bool = True) -> List[Video]:
    """Search both sources, interleaved by relevance, and cache the result."""
    key = f"videos:{name.strip().lower()}"
    if use_cache:
        cached = storage.cache_get(key)
        if cached is not None:
            return [Video(**row) for row in cached]

    videos = rank_by_name(
        search_eporner(name, limit) + search_redtube(name, limit), name
    )[:limit]

    if use_cache and videos:
        storage.cache_set(key, [video.__dict__ for video in videos], CACHE_TTL)
    return videos

    return videos
