"""Build outbound search URLs for the external tube sites.

Every site in :data:`config.EXTERNAL_SITES` carries a ``pattern`` URL template
plus the ``encoding`` its router expects. The encodings are *not*
interchangeable -- each was verified against the live site:

* ``quote_plus``  spaces become ``+``          -- XVideos ``?k=``,
  Xmoviesforyou ``search?q=`` (their own JSON-LD ``SearchAction``)
* ``quote``       spaces become ``%20``        -- Eporner ``/search/<q>/``,
  which 302s to the canonical ``/tag/<q>/`` page
* ``slug``        lowercase, spaces become ``-`` -- Sxyprn ``/search/<slug>.html``
  (``/search/<q>/`` returns a hard 404)

Names routinely contain characters that break URL building when concatenated
naively (``Nikki & Zoë O'Neil``), so every query goes through :func:`encode_query`.
"""

import re
from typing import Any, Dict, Iterable
from urllib.parse import quote, quote_plus

_SLUG_SEPARATORS = re.compile(r"[^a-z0-9]+")


def _slug(name: str) -> str:
    """Lowercase, accent-tolerant-enough slug used by Sxyprn's search router."""
    return _SLUG_SEPARATORS.sub("-", name.lower()).strip("-")


def encode_query(name: str, style: str = "quote_plus") -> str:
    """Percent-encode a performer name for a site's particular query style."""
    name = (name or "").strip()
    if style == "slug":
        return _slug(name)
    if style == "quote":
        return quote(name, safe="")
    return quote_plus(name)


def build_search_url(site: Dict[str, Any], name: str) -> str:
    """Return the search URL for one site config and one performer name."""
    pattern = site.get("pattern") or ""
    template = pattern if "{query}" in pattern else pattern.format(query="")
    query = encode_query(name, site.get("encoding", "quote_plus"))
    return template.format(query=query)


def build_search_urls(sites: Iterable[Dict[str, Any]], name: str) -> Dict[str, str]:
    """Return ``{site_name: search_url}`` for every configured site."""
    return {site["name"]: build_search_url(site, name) for site in sites}
