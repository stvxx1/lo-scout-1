"""Find performers built like the one you are looking at.

There is no similarity score here, because there is nothing honest to score:
a Freeones listing card carries a name and a portrait, so ranking by, say,
"lifestyle overlap" would be invention. Freeones does the work instead -- the
window below becomes a server-side filter (``r[appearance.metric.height]``), so
every result genuinely falls inside it and the caption can say exactly what was
asked for.

The window is derived from the profile the user opened, which is why this needs
ThePornDB: with no height or weight there is nothing to be similar *to*, and
returning "some other performers" would be a lie dressed as a feature.
"""

from typing import Any, Dict, List, Optional, Tuple

from config import SCRAPER_MAX_RETRIES, SCRAPER_RETRY_DELAY, SCRAPER_TIMEOUT
from models.filters import RANGE_FACETS, FilterConfig
from models.performer import Performer
from scraper.base import ScraperError
from scraper.freeones import FreeonesScraper
from scraper.porndb import centimetres

HEIGHT_SPREAD = 6  # cm either side of the anchor
WEIGHT_SPREAD = 8  # kg either side of the anchor
DEFAULT_LIMIT = 12

# Floor/ceiling come from the facet definition rather than being retyped here:
# a window that starts below the facet floor also matches profiles with no value
# recorded at all, which floods the dialog with strangers.
_HEIGHT_FACET = RANGE_FACETS["appearance.metric.height"]
_WEIGHT_FACET = RANGE_FACETS["appearance.metric.weight"]


def _window(
    value: Optional[int], spread: int, floor: int, ceiling: int
) -> Optional[Tuple[int, int]]:
    """Return the inclusive ``(low, high)`` window around ``value``, clamped."""
    if value is None:
        return None
    low = max(floor, value - spread)
    high = min(ceiling, value + spread)
    if low > high:
        return None
    return low, high


def filters_for(profile: Optional[Dict[str, Any]], gender: str = "babes") -> FilterConfig:
    """Return the Freeones filters that describe "more like this profile"."""
    extras = (profile or {}).get("extras") or {}
    height = _window(centimetres(extras.get("height")), HEIGHT_SPREAD, _HEIGHT_FACET[2], _HEIGHT_FACET[3])
    weight = _window(centimetres(extras.get("weight")), WEIGHT_SPREAD, _WEIGHT_FACET[2], _WEIGHT_FACET[3])

    return FilterConfig(
        gender=gender,
        min_height=height[0] if height else None,
        max_height=height[1] if height else None,
        min_weight=weight[0] if weight else None,
        max_weight=weight[1] if weight else None,
    )


def describe(filters: FilterConfig) -> str:
    """Return the human explanation of the window, e.g. ``157-169 cm``."""
    parts = []
    if filters.min_height is not None:
        parts.append(f"{filters.min_height}-{filters.max_height} cm")
    if filters.min_weight is not None:
        parts.append(f"{filters.min_weight}-{filters.max_weight} kg")
    return ", ".join(parts) if parts else "same gender only"


def find_similar(
    profile: Optional[Dict[str, Any]],
    exclude_slug: str = "",
    gender: str = "babes",
    limit: int = DEFAULT_LIMIT,
    scraper: Optional[FreeonesScraper] = None,
) -> Tuple[List[Performer], FilterConfig]:
    """Return ``(performers, filters)`` for a profile's window.

    One page only: this is a "show me alternatives" action, not a scan, and the
    results are already narrowed by the site itself. The clicked performer is
    dropped by slug -- she is inside her own window and listing her first would
    make the feature look like it does nothing.
    """
    filters = filters_for(profile, gender)
    if not filters.has_filters():
        return [], filters

    scraper = scraper or FreeonesScraper(
        timeout=SCRAPER_TIMEOUT,
        max_retries=SCRAPER_MAX_RETRIES,
        retry_delay=SCRAPER_RETRY_DELAY,
    )
    try:
        found = scraper.fetch_performers(page=1, filters=filters)
    except ScraperError:
        return [], filters

    results = [performer for performer in found if performer.slug != exclude_slug]
    return results[:limit], filters
