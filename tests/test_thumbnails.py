"""Portrait thumbnails: URL handling, escaping, and fallbacks.

The failure this guards against is silent: an unescaped name breaks the
``<img>`` tag and the card renders with no image and no error anywhere.

    pytest -q            offline
    pytest -q -m live    also fetches the real CDNs
"""
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "lo-scout"
sys.path.insert(0, str(APP_DIR))

from config import EXTERNAL_SITES                             # noqa: E402
from models.performer import Performer                        # noqa: E402
from scraper.freeones import FreeonesScraper, best_image_url   # noqa: E402
from thumbnails import (                                      # noqa: E402
    MAX_INLINE_BYTES,
    cached_portrait,
    initials,
    normalize_image_url,
    pick_largest_srcset,
    portrait_html,
    to_data_uri,
)
from ui.components import render_performer_card               # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "fo_asc48.html"

# A real signed Freeones URL: imgproxy rejects any size rewrite with 403,
# so this string must survive untouched.
SIGNED = (
    "https://thumbs.freeones.com/photo/-gDpXcPTVaxYcR3NS0Ht/"
    "102x82:1280x1650/fit-in/350x466/center/top/filters:upscale():quality(85)/"
    "tx/rZ/tyxXcnkFmUpdJJugEK/Melody-Marks-nude.jpg"
)

QUOTED_NAME = 'Nikki "The Boss" & Zo\u00eb'


# --- URL normalisation ----------------------------------------------------

def test_signed_url_is_used_verbatim():
    assert normalize_image_url(SIGNED) == SIGNED
    # Guard the exact failure mode: asking imgproxy for a bigger render is 403.
    assert "350x466" in normalize_image_url(SIGNED)


def test_protocol_relative_url_gets_https():
    assert normalize_image_url("//thumbs.freeones.com/a.jpg") == "https://thumbs.freeones.com/a.jpg"


@pytest.mark.parametrize(
    "bad", ["", "   ", "data:image/gif;base64,R0lGOD", "javascript:alert(1)", "/relative/a.jpg"]
)
def test_unusable_urls_are_rejected(bad):
    assert normalize_image_url(bad) == ""


def test_srcset_picks_the_widest_candidate():
    srcset = "https://cdn/a-350.jpg 350w, https://cdn/a-700.jpg 700w, https://cdn/a-466.jpg 466w"
    assert pick_largest_srcset(srcset) == "https://cdn/a-700.jpg"


def test_srcset_understands_density_descriptors():
    assert pick_largest_srcset("https://cdn/a.jpg 1x, https://cdn/b.jpg 2x") == "https://cdn/b.jpg"


def test_initials_ignore_punctuation():
    assert initials("Sara Jay") == "SJ"
    assert initials(QUOTED_NAME) == "NT"
    assert initials("") == "?"


# --- image extraction -----------------------------------------------------

def test_best_image_url_prefers_src():
    soup = BeautifulSoup('<img class="image-content" src="https://cdn/a.jpg">', "html.parser")
    assert best_image_url(soup.find("img")) == "https://cdn/a.jpg"


def test_best_image_url_skips_lazy_placeholder():
    html = '<img src="data:image/gif;base64,R0lGOD" data-src="https://cdn/real.jpg">'
    soup = BeautifulSoup(html, "html.parser")
    assert best_image_url(soup.find("img")) == "https://cdn/real.jpg"


def test_best_image_url_falls_back_to_srcset():
    soup = BeautifulSoup(
        '<img srcset="https://cdn/s.jpg 350w, https://cdn/l.jpg 900w">', "html.parser"
    )
    assert best_image_url(soup.find("img")) == "https://cdn/l.jpg"




# --- rendering ------------------------------------------------------------

def test_portrait_marks_up_the_warm_path():
    markup = portrait_html("Sara Jay", SIGNED)
    assert SIGNED in markup
    assert 'loading="lazy"' in markup
    assert 'decoding="async"' in markup
    assert 'referrerpolicy="no-referrer"' in markup
    assert 'width="350"' in markup and 'height="466"' in markup
    assert 'alt="Sara Jay"' in markup


def test_portrait_renders_placeholder_without_a_url():
    markup = portrait_html("Sara Jay")
    assert "img-fallback" in markup
    assert "<img" not in markup
    assert "SJ" in markup


def test_quoted_name_does_not_break_the_img_tag():
    soup = BeautifulSoup(portrait_html(QUOTED_NAME, SIGNED), "html.parser")
    img = soup.find("img")
    assert img is not None, "unescaped name destroyed the tag"
    assert img["alt"] == QUOTED_NAME
    assert img["src"] == SIGNED


def test_card_stays_parseable_with_quoted_name():
    performer = Performer(name=QUOTED_NAME, slug="nikki", image_url=SIGNED, source="freeones")
    soup = BeautifulSoup(render_performer_card(performer, EXTERNAL_SITES), "html.parser")

    assert soup.find("img")["alt"] == QUOTED_NAME
    assert soup.find("p", class_="performer-name").get_text() == QUOTED_NAME
    assert soup.find("p", class_="performer-name")["title"] == QUOTED_NAME


def test_card_links_are_encoded_for_every_site():
    performer = Performer(name=QUOTED_NAME, slug="nikki", image_url=SIGNED, source="freeones")
    soup = BeautifulSoup(render_performer_card(performer, EXTERNAL_SITES), "html.parser")
    hrefs = [a["href"] for a in soup.find_all("a", class_="tube-link")]

    assert len(hrefs) == len(EXTERNAL_SITES)
    for href in hrefs:
        assert " " not in href and "&" not in href, href
    assert any(href.endswith(".html") for href in hrefs)


def test_card_uses_the_portrait_of_each_performer():
    performers = FreeonesScraper().parse_performers(FIXTURE.read_text(encoding="utf-8"))
    for performer in performers[:3]:
        soup = BeautifulSoup(render_performer_card(performer, EXTERNAL_SITES), "html.parser")
        assert soup.find("img")["src"] == performer.image_url


# --- inlining -------------------------------------------------------------

def test_data_uri_refuses_oversized_payloads():
    assert to_data_uri(b"x" * (MAX_INLINE_BYTES + 1)) == ""
    assert to_data_uri(b"abc").startswith("data:image/jpeg;base64,")


# --- live -----------------------------------------------------------------

@pytest.mark.live
def test_live_freeones_portrait_is_served():
    requests = pytest.importorskip("requests")
    performers = FreeonesScraper().parse_performers(FIXTURE.read_text(encoding="utf-8"))
    url = normalize_image_url(performers[0].image_url)
    response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")
    assert len(response.content) > 5_000


@pytest.mark.live
def test_live_stashdb_portrait_downscales_small(tmp_path, monkeypatch):
    monkeypatch.setenv("LO_SCOUT_HOME", str(tmp_path))
    url = "https://stashdb.org/images/d36b9412-0ff9-4849-b2ca-251d9b10049c"
    data = cached_portrait(url)
    assert data, "stashdb portrait download failed"
    assert len(data) < MAX_INLINE_BYTES
    assert data[:2] == b"\xff\xd8"  # JPEG SOI

def test_fixture_exposes_one_portrait_per_performer():
    performers = FreeonesScraper().parse_performers(FIXTURE.read_text(encoding="utf-8"))
    assert len(performers) == 48
    assert sum(1 for p in performers if normalize_image_url(p.image_url)) == 48
