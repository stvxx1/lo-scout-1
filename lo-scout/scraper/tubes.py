"""Clip search on tube sites that publish no search API.

XVideos is scraped with BeautifulSoup. The selectors mirror the TypeScript
scraper in the sibling project (``server/scrapers/tubes.ts``) with two
corrections found by inspecting the live markup:

* ``.thumb-block`` also matches *profile* cards, so a block only counts as a
  clip when it contains a ``/video.`` link;
* thumbnails are lazy -- ``src`` holds a blank placeholder and the real image
  URL sits in ``data-src``.

robots.txt (checked 2026-10) disallows only ``/video-vote/``, so the bare
search page is allowed. One page per query, no pagination; any failure returns
an empty list, exactly like the JSON sources in ``scraper.videos``.
"""

from typing import TYPE_CHECKING, List
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

if TYPE_CHECKING:  # pragma: no cover - only for the annotations
    from scraper.videos import Video

BASE_URL = "https://www.xvideos.com"
SEARCH_URL = BASE_URL + "/?k={query}"
EMBED_URL = BASE_URL + "/embedframe/{eid}"
PLACEHOLDER = "lightbox-blank"


def _models():
    """Import the shared module lazily: ``scraper.videos`` imports this one."""
    from scraper import videos

    return videos


def _clip_link(block):
    """Return the clip anchor inside a result block, or None for profile cards."""
    return block.find("a", href=lambda href: bool(href) and href.startswith("/video."))


def _title(block, link) -> str:
    anchor = block.select_one("p.title a")
    if anchor is not None and anchor.get("title"):
        return anchor["title"].strip()
    image = block.find("img")
    if image is not None and image.get("alt"):
        return image["alt"].strip()
    slug = link["href"].split("/video.", 1)[-1].split("/", 1)[-1]
    return slug.replace("_", " ").strip().capitalize()


def _thumb(block) -> str:
    """Return the thumbnail URL, skipping the lazy-loading blank GIF."""
    image = block.find("img")
    if image is None:
        return ""
    for attribute in ("data-src", "data-mzl", "src"):
        value = (image.get(attribute) or "").strip()
        if value.startswith("https://") and PLACEHOLDER not in value:
            return value
    return ""


def _duration(block) -> str:
    span = block.select_one("span.duration")
    return span.get_text(strip=True) if span is not None else ""


def _video_id(block, link) -> str:
    """Return the embed id (``okiuoad77be``), which differs from ``data-id``."""
    eid = (block.get("data-eid") or "").strip()
    if eid:
        return eid
    path = link["href"].split("/video.", 1)[-1]
    return path.split("/", 1)[0].split("?", 1)[0]


def parse_xvideos(markup: str, limit: int = 12) -> List["Video"]:
    """Map an XVideos search page to Videos (never raises)."""
    videos: List["Video"] = []
    if not markup:
        return videos

    Video = _models().Video
    soup = BeautifulSoup(markup, "html.parser")

    for block in soup.select(".thumb-block"):
        link = _clip_link(block)
        if link is None:
            continue  # a model/profile card, not a clip
        video_id = _video_id(block, link)
        try:
            videos.append(
                Video(
                    source="XVideos",
                    id=video_id or link["href"],
                    title=_title(block, link),
                    page_url=urljoin(BASE_URL + "/", link["href"]),
                    embed_url=EMBED_URL.format(eid=video_id) if video_id else "",
                    thumb_url=_thumb(block),
                    duration=_duration(block),
                )
            )
        except (KeyError, TypeError):
            continue
        if len(videos) >= limit:
            break
    return videos


def _get_html(url: str, timeout: float) -> str:
    models = _models()
    response = requests.get(
        url, headers={"User-Agent": models.USER_AGENT}, timeout=timeout
    )
    response.raise_for_status()
    return response.text


def search_xvideos(name: str, limit: int = 12, timeout: float = None) -> List["Video"]:
    """Search XVideos and return Videos (empty list on any network problem)."""
    models = _models()
    url = SEARCH_URL.format(query=quote_plus(name))
    try:
        return parse_xvideos(_get_html(url, timeout or models.TIMEOUT), limit)
    except (requests.RequestException, ValueError):
        return []
