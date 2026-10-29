"""Eporner, RedTube and XVideos clip search.

    pytest -q            offline, replays the captured JSON/HTML fixtures
    pytest -q -m live    also queries the three sites
"""
import json
import sys
import time
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "lo-scout"
sys.path.insert(0, str(APP_DIR))

import storage                                               # noqa: E402
from models.performer import Performer                       # noqa: E402
from scraper import tubes                                    # noqa: E402
from scraper import videos as vids                           # noqa: E402
from ui.video_panel import (                                 # noqa: E402
    render_player,
    render_thumb_link,
    render_watch_link,
)

FIXTURES = Path(__file__).parent / "fixtures"
EPORNER = json.loads((FIXTURES / "eporner_search.json").read_text(encoding="utf-8"))
REDTUBE = json.loads((FIXTURES / "redtube_search.json").read_text(encoding="utf-8"))
XVIDEOS = (FIXTURES / "xvideos_search.html").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def offline(request, monkeypatch):
    """Keep the offline suite hermetic: XVideos is the only source that fetches
    HTML, and every test that expects it to return clips monkeypatches
    ``vids.search_xvideos``. Live tests opt out."""
    if request.node.get_closest_marker("live"):
        return

    def boom(*args, **kwargs):
        raise requests.ConnectionError("network disabled in tests")

    monkeypatch.setattr(requests, "get", boom)


# --- parsing --------------------------------------------------------------

def test_eporner_fixture_parses():
    videos = vids.parse_eporner(EPORNER, limit=5)

    assert len(videos) == 5
    first = videos[0]
    assert first.source == "Eporner"
    assert first.id and first.page_url.startswith("https://www.eporner.com/video-")
    assert first.embed_url.startswith("https://www.eporner.com/embed/")
    assert first.thumb_url.startswith("https://")
    assert first.duration  # "60:21"
    assert isinstance(first.views, int)


def test_eporner_limit_is_respected():
    assert len(vids.parse_eporner(EPORNER, limit=2)) == 2


def test_redtube_fixture_parses():
    videos = vids.parse_redtube(REDTUBE, limit=5)

    assert len(videos) == 5
    first = videos[0]
    assert first.source == "RedTube"
    assert first.id and first.page_url.startswith("https://www.redtube.com/")
    assert first.embed_url.startswith("https://embed.redtube.com/")
    assert first.thumb_url.startswith("https://")
    assert first.duration  # "25:18"


@pytest.mark.parametrize(
    "payload", [None, {}, {"videos": None}, {"videos": [{}]}, {"videos": ["junk"]}]
)
def test_parsers_never_raise_on_junk(payload):
    assert vids.parse_eporner(payload) == []
    assert vids.parse_redtube(payload) == []


# --- XVideos (scraped) ----------------------------------------------------

def test_xvideos_fixture_parses():
    videos = tubes.parse_xvideos(XVIDEOS, limit=5)

    assert len(videos) == 5
    first = videos[0]
    assert first.source == "XVideos"
    assert first.id == "okiuoad77be"
    assert first.page_url.startswith("https://www.xvideos.com/video.okiuoad77be/")
    assert first.embed_url == "https://www.xvideos.com/embedframe/okiuoad77be"
    assert first.title  # taken from the anchor's title attribute
    assert first.duration.endswith(("min", "sec"))  # "10 min"
    assert first.thumb_url.startswith("https://") and "xvideos-cdn" in first.thumb_url


def test_xvideos_skips_profile_cards():
    # The fixture holds ten .thumb-block nodes, two of which are model cards
    # linking to /pornstars/. Counting them would add clip-less blocks.
    videos = tubes.parse_xvideos(XVIDEOS, limit=50)

    assert len(videos) == 8
    for video in videos:
        assert "/video." in video.page_url
        assert video.id and video.embed_url


def test_xvideos_ignores_the_lazy_loading_placeholder():
    for video in tubes.parse_xvideos(XVIDEOS, limit=50):
        assert "lightbox-blank" not in video.thumb_url


def test_xvideos_limit_is_respected():
    assert len(tubes.parse_xvideos(XVIDEOS, limit=3)) == 3


@pytest.mark.parametrize("markup", ["", "   ", "<html><body>no results</body></html>"])
def test_xvideos_never_raises_on_junk(markup):
    assert tubes.parse_xvideos(markup) == []


def test_xvideos_embed_falls_back_to_the_slug_when_data_eid_is_missing():
    markup = (
        '<div class="thumb-block">'
        '<div class="thumb"><a href="/video.abc123/some_title_here">'
        '<img src="https://assets-cdn77.xvideos-cdn.com/img/lightbox/lightbox-blank.gif" '
        'data-src="https://cdn.example/real.jpg"></a></div>'
        '<p class="title"><a href="/video.abc123/some_title_here" title="Some Title Here">'
        'Some Title Here<span class="duration">3 min</span></a></p>'
        "</div>"
    )
    video = tubes.parse_xvideos(markup)[0]

    assert video.id == "abc123"
    assert video.embed_url == "https://www.xvideos.com/embedframe/abc123"
    assert video.title == "Some Title Here"
    assert video.thumb_url == "https://cdn.example/real.jpg"
    assert video.duration == "3 min"


# --- grouping -------------------------------------------------------------

def test_group_by_source_keeps_sites_apart():
    grouped = vids.group_by_source(
        [
            vids.Video("Eporner", "1", "a", "p", "e"),
            vids.Video("XVideos", "2", "b", "p", "e"),
            vids.Video("Eporner", "3", "c", "p", "e"),
        ]
    )

    assert list(grouped) == list(vids.SOURCES)  # tab order
    assert [v.id for v in grouped["Eporner"]] == ["1", "3"]
    assert [v.id for v in grouped["XVideos"]] == ["2"]
    assert grouped["RedTube"] == []  # a stable tab even when empty


# --- relevance ------------------------------------------------------------

def test_clips_naming_the_performer_come_first():
    videos = [
        vids.Video("Eporner", "1", "Interracial Compilation", "", "", ""),
        vids.Video("Eporner", "2", "Sara Jay and friends", "", "", ""),
        vids.Video("Eporner", "3", "SARA JAY solo", "", "", ""),
    ]
    ranked = vids.rank_by_name(videos, "Sara Jay")
    assert [v.id for v in ranked] == ["2", "3", "1"]


def test_ranking_keeps_api_order_within_groups():
    videos = [vids.Video("R", str(i), "other", "", "", "") for i in range(3)]
    assert [v.id for v in vids.rank_by_name(videos, "Sara Jay")] == ["0", "1", "2"]


# --- fetching -------------------------------------------------------------

def test_eporner_request_carries_an_encoded_query(monkeypatch):
    seen = {}

    def fake_get(url, timeout=None):
        seen["url"] = url
        return EPORNER

    monkeypatch.setattr(vids, "_get_json", fake_get)
    vids.search_eporner("Nikki & Zo\u00eb", limit=3)

    assert "query=Nikki+%26+Zo%C3%AB" in seen["url"]
    assert "per_page=3" in seen["url"]
    assert "format=json" in seen["url"]


def test_network_failure_yields_no_clips(monkeypatch):
    def boom(url, timeout=None):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(vids, "_get_json", boom)
    assert vids.search_eporner("Sara Jay") == []
    assert vids.search_redtube("Sara Jay") == []
    assert vids.search_all("Sara Jay") == []


def test_bad_json_yields_no_clips(monkeypatch):
    def boom(url, timeout=None):
        raise ValueError("not json")

    monkeypatch.setattr(vids, "_get_json", boom)
    assert vids.search_all("Sara Jay") == []


def test_search_all_merges_both_sources_and_trims(monkeypatch):
    monkeypatch.setattr(
        vids, "search_eporner", lambda name, limit=12: vids.parse_eporner(EPORNER, limit)
    )
    monkeypatch.setattr(
        vids, "search_redtube", lambda name, limit=12: vids.parse_redtube(REDTUBE, limit)
    )

    videos = vids.search_all("Sara Jay", limit=4)

    assert len(videos) == 4
    assert {v.source for v in videos} == {"Eporner", "RedTube"}


def test_search_all_caches_the_result(monkeypatch):
    calls = []

    def fake_eporner(name, limit=12):
        calls.append(name)
        return vids.parse_eporner(EPORNER, 2)

    monkeypatch.setattr(vids, "search_eporner", fake_eporner)
    monkeypatch.setattr(vids, "search_redtube", lambda name, limit=12: [])

    first = vids.search_all("Sara Jay", limit=2)
    second = vids.search_all("Sara Jay", limit=2)

    assert len(calls) == 1, "second call should come from the cache"
    assert [v.id for v in first] == [v.id for v in second]
    assert storage.cache_get("videos:sara jay") is not None


def test_search_by_source_returns_one_bucket_per_site(monkeypatch):
    monkeypatch.setattr(vids, "search_eporner", lambda name, limit=12: vids.parse_eporner(EPORNER, limit))
    monkeypatch.setattr(vids, "search_redtube", lambda name, limit=12: vids.parse_redtube(REDTUBE, limit))
    monkeypatch.setattr(vids, "search_xvideos", lambda name, limit=12: tubes.parse_xvideos(XVIDEOS, limit))

    grouped = vids.search_by_source("Sara Jay", limit=3)

    assert list(grouped) == list(vids.SOURCES)
    assert all(len(clips) == 3 for clips in grouped.values())
    assert {clip.source for clips in grouped.values() for clip in clips} == set(vids.SOURCES)


def test_one_failing_source_does_not_empty_the_others(monkeypatch):
    def boom(name, limit=12):
        raise RuntimeError("scraper bug")

    monkeypatch.setattr(vids, "search_eporner", lambda name, limit=12: vids.parse_eporner(EPORNER, limit))
    monkeypatch.setattr(vids, "search_redtube", boom)
    monkeypatch.setattr(vids, "search_xvideos", boom)

    grouped = vids.search_by_source("Sara Jay", limit=2)

    assert len(grouped["Eporner"]) == 2
    assert grouped["RedTube"] == [] and grouped["XVideos"] == []


def test_sources_are_fetched_in_parallel(monkeypatch):
    def slow(name, limit=12):
        time.sleep(0.2)
        return []

    for attribute in vids.SOURCES.values():
        monkeypatch.setattr(vids, attribute, slow)

    started = time.monotonic()
    vids.search_by_source("Sara Jay", use_cache=False)
    elapsed = time.monotonic() - started

    # Sequential would be 0.6s; the dialog opens on a click, so it must not be.
    assert elapsed < 0.45, f"sources were fetched sequentially ({elapsed:.2f}s)"


def test_search_by_source_is_cached_and_regrouped(monkeypatch):
    monkeypatch.setattr(vids, "search_eporner", lambda name, limit=12: vids.parse_eporner(EPORNER, 2))
    monkeypatch.setattr(vids, "search_redtube", lambda name, limit=12: vids.parse_redtube(REDTUBE, 2))
    monkeypatch.setattr(vids, "search_xvideos", lambda name, limit=12: tubes.parse_xvideos(XVIDEOS, 2))

    first = vids.search_by_source("Sara Jay", limit=2)

    def boom(name, limit=12):
        raise AssertionError("second call should come from the cache")

    for attribute in vids.SOURCES.values():
        monkeypatch.setattr(vids, attribute, boom)

    second = vids.search_by_source("Sara Jay", limit=2)

    assert list(second) == list(vids.SOURCES)
    assert [[v.id for v in clips] for clips in second.values()] == [
        [v.id for v in clips] for clips in first.values()
    ]


def test_search_all_keeps_every_source(monkeypatch):
    monkeypatch.setattr(vids, "search_eporner", lambda name, limit=12: vids.parse_eporner(EPORNER, limit))
    monkeypatch.setattr(vids, "search_redtube", lambda name, limit=12: vids.parse_redtube(REDTUBE, limit))
    monkeypatch.setattr(vids, "search_xvideos", lambda name, limit=12: tubes.parse_xvideos(XVIDEOS, limit))

    # A limit larger than the whole fixture set, so ranking cannot starve a site
    # whose titles do not spell the performer out: the flat view must still be
    # the union of every tab.
    videos = vids.search_all("Sara Jay", limit=100)
    expected = (
        vids.parse_eporner(EPORNER, 100)
        + vids.parse_redtube(REDTUBE, 100)
        + tubes.parse_xvideos(XVIDEOS, 100)
    )

    assert {v.source for v in videos} == set(vids.SOURCES)
    assert len(videos) == len(expected)


# --- rendering ------------------------------------------------------------

def test_player_iframe_is_escaped():
    video = vids.Video("Eporner", "abc", "t", "p", "https://x/embed/?a=1&b=2")
    markup = render_player(video)
    assert "&amp;" in markup and "b=2" in markup
    assert "allowfullscreen" in markup


def test_player_without_embed_renders_nothing():
    assert render_player(vids.Video("Eporner", "abc", "t", "p", "")) == ""


def test_watch_link_is_offered_when_a_clip_cannot_be_embedded():
    video = vids.Video("XVideos", "abc", "t", "https://www.xvideos.com/video.abc/x", "")
    markup = render_watch_link(video)

    assert 'href="https://www.xvideos.com/video.abc/x"' in markup
    assert "Watch on XVideos" in markup
    assert 'target="_blank"' in markup and "noopener" in markup
    assert render_watch_link(vids.Video("XVideos", "abc", "t", "", "")) == ""


def test_thumb_link_escapes_quotes_in_the_title():
    video = vids.Video("Eporner", "abc", 'She said "hi"', "https://x/1", "", "https://x/t.jpg")
    markup = render_thumb_link(video)
    assert "&quot;hi&quot;" in markup
    assert markup.count("<img") == 1


def test_views_are_humanised():
    assert vids.format_views(198_985) == "199K views"
    assert vids.format_views(2_400_000) == "2.4M views"
    assert vids.format_views(42) == "42 views"
    assert vids.format_views(None) == ""


# --- live -----------------------------------------------------------------

@pytest.mark.live
def test_live_every_source_returns_clips():
    grouped = vids.search_by_source("Sara Jay", limit=3, use_cache=False)

    missing = [source for source, clips in grouped.items() if not clips]
    assert not missing, f"no clips from {missing}"
    for clips in grouped.values():
        for video in clips:
            assert video.title and video.page_url.startswith("https://")


@pytest.mark.live
def test_live_xvideos_returns_playable_clips():
    clips = tubes.search_xvideos("Sara Jay", limit=4)

    assert clips, "XVideos returned no clips (layout change or rate limit?)"
    for clip in clips:
        assert clip.source == "XVideos"
        assert clip.id and clip.thumb_url.startswith("https://")
        assert clip.page_url.startswith("https://www.xvideos.com/video.")
        assert clip.embed_url == f"https://www.xvideos.com/embedframe/{clip.id}"


@pytest.mark.live
def test_live_xvideos_embed_frame_is_served():
    requests = pytest.importorskip("requests")
    clip = tubes.search_xvideos("Sara Jay", limit=1)[0]

    response = requests.get(
        clip.embed_url, headers={"User-Agent": vids.USER_AGENT}, timeout=30
    )

    assert response.status_code == 200
    assert "player" in response.text.lower()



def test_grid_offers_a_clips_button():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=90)
    at.session_state["performers"] = [
        Performer(name="Sara Jay", slug="sara-jay", source="freeones")
    ]
    at.run()

    assert not at.exception, [f"{e.type}: {e.value}" for e in at.exception]
    assert any("Clips" in b.label for b in at.button)
