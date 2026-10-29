"""Clip search across Eporner, RedTube and XVideos.

Eporner and RedTube publish public JSON endpoints that need no key and no HTML
scraping, so they are far sturdier than the Freeones listing; XVideos is scraped
in ``scraper.tubes``. A failure here must never take the grid down: every search
returns an empty list on error and the caller renders "no clips found".

Results are fetched per site so the panel can show one tab per source::

    grouped = search_by_source("Sara Jay")   # {"Eporner": [...], "RedTube": [...], ...}
    flat = search_all("Sara Jay")            # the same clips, relevance-ranked
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import requests

import storage

from scraper import tubes

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

# Ordered on purpose: the panel renders one tab per entry, left to right, and
# the flat ``search_all`` listing keeps this order before ranking by relevance.
# Values are attribute names on this module so tests can monkeypatch a single
# source without touching the network.
SOURCES: Dict[str, str] = {
    "Eporner": "search_eporner",
    "RedTube": "search_redtube",
    "XVideos": "search_xvideos",
}


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


def search_xvideos(name: str, limit: int = 12, timeout: float = TIMEOUT) -> List[Video]:
    """Search XVideos via the HTML scraper.

    A thin wrapper on purpose: everything else in this module is looked up by
    name in ``SOURCES``, so the scraped source stays monkeypatchable here.
    """
    return tubes.search_xvideos(name, limit, timeout)


def group_by_source(videos: List[Video]) -> Dict[str, List[Video]]:
    """Split clips into one bucket per configured source, keeping tab order.

    Every source gets a bucket even when it returned nothing, so the panel can
    show a stable set of tabs; unknown sources are appended rather than dropped.
    """
    grouped: Dict[str, List[Video]] = {source: [] for source in SOURCES}
    for video in videos:
        grouped.setdefault(video.source, []).append(video)
    return grouped


def _fetch(source: str, name: str, limit: int) -> List[Video]:
    """Fetch one source, isolated from every other source."""
    fetcher = globals().get(SOURCES[source])
    if fetcher is None:
        return []
    try:
        return fetcher(name, limit)
    except Exception:  # noqa: BLE001 - a parser bug must not empty the other tabs
        return []


def search_by_source(
    name: str, limit: int = 8, use_cache: bool = True
) -> Dict[str, List[Video]]:
    """Search every source in parallel and return the clips grouped by site.

    The cache stores one flat list of clips; the grouping is recomputed on read
    so the layout can change without invalidating saved results.
    """
    key = f"videos:{name.strip().lower()}"
    if use_cache:
        cached = storage.cache_get(key)
        if cached is not None:
            return group_by_source([Video(**row) for row in cached])

    # Parallel, not sequential: a few seconds per site adds up fast in a dialog
    # that opens on a click, and one slow site should not delay the others.
    with ThreadPoolExecutor(max_workers=len(SOURCES)) as pool:
        futures = {
            source: pool.submit(_fetch, source, name, limit) for source in SOURCES
        }
        grouped = {source: future.result() for source, future in futures.items()}

    if use_cache and any(grouped.values()):
        flat = [video for clips in grouped.values() for video in clips]
        storage.cache_set(key, [video.__dict__ for video in flat], CACHE_TTL)
    return grouped


def search_all(name: str, limit: int = 8, use_cache: bool = True) -> List[Video]:
    """Search every source, interleaved by relevance, and cache the result."""
    grouped = search_by_source(name, limit=limit, use_cache=use_cache)
    videos = [video for clips in grouped.values() for video in clips]
    return rank_by_name(videos, name)[:limit]

