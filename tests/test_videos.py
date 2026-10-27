"""Eporner and RedTube clip search.

    pytest -q            offline, replays the captured JSON fixtures
    pytest -q -m live    also queries both APIs
"""
import json
import sys
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "lo-scout"
sys.path.insert(0, str(APP_DIR))

import storage                                               # noqa: E402
from models.performer import Performer                       # noqa: E402
from scraper import videos as vids                           # noqa: E402
from ui.video_panel import render_player, render_thumb_link   # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
EPORNER = json.loads((FIXTURES / "eporner_search.json").read_text(encoding="utf-8"))
REDTUBE = json.loads((FIXTURES / "redtube_search.json").read_text(encoding="utf-8"))


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


# --- rendering ------------------------------------------------------------

def test_player_iframe_is_escaped():
    video = vids.Video("Eporner", "abc", "t", "p", "https://x/embed/?a=1&b=2")
    markup = render_player(video)
    assert "&amp;" in markup and "b=2" in markup
    assert "allowfullscreen" in markup


def test_player_without_embed_renders_nothing():
    assert render_player(vids.Video("Eporner", "abc", "t", "p", "")) == ""


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
def test_live_both_sources_return_clips():
    videos = vids.search_all("Sara Jay", limit=4, use_cache=False)

    assert videos, "no clips from either source"
    assert {v.source for v in videos} == {"Eporner", "RedTube"}
    for video in videos:
        assert video.title and video.page_url.startswith("https://")


def test_grid_offers_a_clips_button():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=90)
    at.session_state["performers"] = [
        Performer(name="Sara Jay", slug="sara-jay", source="freeones")
    ]
    at.run()

    assert not at.exception, [f"{e.type}: {e.value}" for e in at.exception]
    assert any("Clips" in b.label for b in at.button)
