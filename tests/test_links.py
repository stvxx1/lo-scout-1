"""External search links.

Every pattern here was verified against the live site once (see the `live`
test); the offline tests pin the shape so a refactor cannot quietly restore
the old broken URLs.

    pytest -q            offline
    pytest -q -m live    also fetches each search page
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "lo-scout"
sys.path.insert(0, str(APP_DIR))

from config import EXTERNAL_SITES                                  # noqa: E402
from links import build_search_url, build_search_urls, encode_query  # noqa: E402
from models.performer import Performer                             # noqa: E402

AWKWARD = "Nikki & Zo\u00eb O'Neil"   # ampersand, non-ASCII, apostrophe


def site(name: str) -> dict:
    return next(s for s in EXTERNAL_SITES if s["name"] == name)


# --- encoding -------------------------------------------------------------

def test_quote_plus_style():
    assert encode_query(AWKWARD, "quote_plus") == "Nikki+%26+Zo%C3%AB+O%27Neil"


def test_quote_style_keeps_spaces_as_percent20():
    assert encode_query("Sara Jay", "quote") == "Sara%20Jay"


def test_slug_style_for_sxyprn():
    assert encode_query("Sara Jay", "slug") == "sara-jay"
    assert encode_query(AWKWARD, "slug") == "nikki-zo-o-neil"


def test_unknown_style_falls_back_to_quote_plus():
    assert encode_query("Sara Jay", "nonsense") == "Sara+Jay"


# --- per-site patterns ----------------------------------------------------

def test_xvideos_uses_k_parameter():
    url = build_search_url(site("XVideos"), "Sara Jay")
    assert url == "https://www.xvideos.com/?k=Sara+Jay"


def test_eporner_uses_search_path_and_percent20():
    url = build_search_url(site("Eporner"), "Sara Jay")
    assert url == "https://www.eporner.com/search/Sara%20Jay/"


def test_sxyprn_requires_html_suffix():
    # /search/<name>/ 404s; only /search/<slug>.html resolves.
    url = build_search_url(site("Sxyprn"), "Sara Jay")
    assert url == "https://www.sxyprn.com/search/sara-jay.html"


def test_xmoviesforyou_uses_q_parameter():
    # /search/<name>/ redirects to /new-search and drops the query entirely.
    url = build_search_url(site("Xmoviesforyou"), "Sara Jay")
    assert url == "https://xmoviesforyou.com/search?q=Sara+Jay"


def test_every_site_template_and_encoding_is_configured():
    for entry in EXTERNAL_SITES:
        assert "{query}" in entry["pattern"], entry["name"]
        assert entry["encoding"] in {"quote", "quote_plus", "slug"}, entry["name"]


# --- whatever the name, the URL stays valid -------------------------------

@pytest.mark.parametrize("name", [AWKWARD, "100% Real", "A#B?C", "  spaced  "])
def test_urls_never_contain_raw_spaces_or_ampersands(name):
    urls = build_search_urls(EXTERNAL_SITES, name)
    assert len(urls) == len(EXTERNAL_SITES)
    for url in urls.values():
        assert " " not in url, url
        # A name's "&" must arrive percent-encoded, and no template adds its own.
        assert "&" not in url, url
        assert url.startswith("https://"), url


def test_performer_uses_the_same_builder():
    performer = Performer(name="Sara Jay", slug="sara-jay", source="freeones")
    urls = performer.get_external_search_urls(EXTERNAL_SITES)
    assert urls["Sxyprn"].endswith("/sara-jay.html")
    assert urls["Xmoviesforyou"].endswith("?q=Sara+Jay")


# --- live -----------------------------------------------------------------

@pytest.mark.live
@pytest.mark.parametrize("site_name", ["XVideos", "Eporner", "Sxyprn", "Xmoviesforyou"])
def test_live_search_url_resolves(site_name):
    requests = pytest.importorskip("requests")
    url = build_search_url(site(site_name), "Sara Jay")
    response = requests.get(
        url,
        timeout=30,
        allow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/131.0.0.0 Safari/537.36"},
    )
    assert response.status_code < 400, f"{site_name} -> {response.status_code}"
