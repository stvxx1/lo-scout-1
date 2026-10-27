"""StashDB lookups: key handling, matching, GraphQL errors, caching.

    pytest -q            offline, replays a recorded response
    pytest -q -m live    also queries the real API (needs STASHDB_API_KEY)

The fixture is a real response, recorded on 2026-10-28 and trimmed to the two
largest images per record. Recording it earned its keep: the hand-written
version had ``aliases`` as one comma-separated string, while the live schema
returns a list, so every alias rendered as ``"['Sarah Jay']"``. The same call
showed that "Sara Jay" returns "Sara Jaymes" *first* -- stash-box name search is
fuzzy, and only the exact-name pass in :func:`best_match` saves the lookup.
"""

import json
import sys
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "lo-scout"
sys.path.insert(0, str(APP_DIR))

from scraper import stashdb                                       # noqa: E402
from ui.profile_panel import profile_html, profile_rows            # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
PAYLOAD = json.loads((FIXTURES / "stashdb_performer.json").read_text(encoding="utf-8"))
PROFILES = stashdb.parse_search(PAYLOAD)


def profile_named(name):
    """Return the parsed fixture profile called ``name``."""
    return next(profile for profile in PROFILES if profile["name"] == name)


# Order matters here: StashDB really does answer "Sara Jay" with Sara Jaymes
# first, so every matching test runs against that ranking, not a tidy one.
SARA = profile_named("Sara Jay")
JAYMES = profile_named("Sara Jaymes")


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} for {stashdb.ENDPOINT}")

    def json(self):
        return self.payload


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("STASHDB_API_KEY", "test-key")
    return "test-key"


@pytest.fixture
def calls(monkeypatch, configured):
    """Record every outbound request and answer with the fixture."""
    recorded = []

    def fake_post(url, json=None, headers=None, timeout=None, **kwargs):
        recorded.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return FakeResponse(PAYLOAD)

    monkeypatch.setattr(stashdb.requests, "post", fake_post)
    return recorded


# --- credentials ----------------------------------------------------------

def test_key_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("STASHDB_API_KEY", "abc123")
    assert stashdb.api_key() == "abc123"
    assert stashdb.is_configured()


def test_key_comes_from_a_section_in_secrets_toml(tmp_path):
    (tmp_path / "secrets.toml").write_text(
        '[stashdb]\napi_key = "from-toml"\n', encoding="utf-8"
    )
    assert stashdb.api_key() == "from-toml"


def test_no_key_means_no_metadata_and_no_request(monkeypatch):
    def explode(*args, **kwargs):
        raise AssertionError("stashdb must not be called without a key")

    monkeypatch.setattr(stashdb.requests, "post", explode)
    assert not stashdb.is_configured()
    assert stashdb.search("Sara Jay") == []
    assert stashdb.lookup("Sara Jay") is None


# --- parsing --------------------------------------------------------------

def test_parse_maps_a_record_onto_the_profile_shape():
    assert SARA["name"] == "Sara Jay"
    assert SARA["source"] == "StashDB"
    extras = SARA["extras"]
    # Formatting follows ThePornDB's, because both sources share one stat grid.
    assert extras["height"] == "163cm"
    assert extras["measurements"] == "36-25-41"
    assert extras["cupsize"] == "36E"
    assert extras["hair_colour"] == "Blonde"
    assert extras["eye_colour"] == "Hazel"
    assert extras["ethnicity"] == "Caucasian"
    assert extras["nationality"] == "American"
    assert extras["birthday"] == "1977-11-14"
    assert extras["career_start_year"] == 2001
    assert extras["scenes"] == 570


def test_parse_keeps_the_alias_list_whole():
    """The live field is a list; ``str()`` on it produced ``"['Sarah Jay']"``."""
    assert SARA["aliases"] == ["Sarah Jay"]
    assert JAYMES["aliases"][:3] == ["Ara", "Jessica", "Jessica X"]
    assert not any(alias.startswith(("[", "'", '"')) for alias in JAYMES["aliases"])


def test_comma_separated_aliases_still_parse():
    """Older stash-box builds answered with one string; do not regress on them."""
    assert stashdb._aliases({"aliases": "Sarah Jay, Piera Gambetta"}) == [
        "Sarah Jay",
        "Piera Gambetta",
    ]
    assert stashdb._aliases({"aliases": None}) == []
    assert stashdb._aliases({}) == []


def test_portrait_is_the_largest_image():
    largest = max(
        PAYLOAD["data"]["queryPerformers"]["performers"][1]["images"],
        key=lambda image: image["width"],
    )
    assert SARA["image"] == largest["url"]
    assert SARA["image"].startswith("https://stashdb.org/images/")
    assert stashdb.to_profile({"name": "No Pictures", "images": []})["image"] == ""


def test_unknown_enums_and_partial_measurements_are_dropped():
    extras = stashdb.to_profile(
        {
            "name": "Half A Record",
            "ethnicity": "UNKNOWN",   # not a fact
            "eye_color": None,
            "band_size": None,        # no band, so the cup stays bare
            "waist_size": None,       # no waist, so no measurements triple
            "hip_size": 36,
            "cup_size": "C",
            "hair_color": "BROWN",
            "country": None,
        }
    )["extras"]
    assert "ethnicity" not in extras
    assert "eye_colour" not in extras
    assert "measurements" not in extras
    assert "nationality" not in extras
    assert extras["cupsize"] == "C"
    assert extras["hair_colour"] == "Brown"


def test_country_codes_read_as_nationalities():
    """The tabs share a grid, so "US" beside ThePornDB's "American" looks broken."""
    assert stashdb._nationality({"country": "US"}) == "American"
    assert stashdb._nationality({"country": "gb"}) == "British"
    assert stashdb._nationality({"country": "ZZ"}) == "ZZ", "unmapped codes pass through"
    assert stashdb._nationality({"country": ""}) is None
    assert stashdb._nationality({}) is None


def test_multi_word_enums_read_as_words():
    assert stashdb._pretty("MIDDLE_EASTERN") == "Middle Eastern"
    assert stashdb._pretty("UNKNOWN") is None
    assert stashdb._pretty(None) is None


def test_parse_survives_junk():
    assert stashdb.parse_search(None) == []
    assert stashdb.parse_search({"data": None}) == []
    assert stashdb.parse_search({"data": {"queryPerformers": None}}) == []
    assert stashdb.parse_search({"data": {"queryPerformers": {"performers": []}}}) == []


def test_link_points_at_the_stashdb_profile():
    assert SARA["links"]["StashDB"].endswith(
        "/performers/b99a587a-1e63-409b-8c10-730088389364"
    )
    assert SARA["links"]["StashDB"].startswith(stashdb.SITE)


# --- matching -------------------------------------------------------------

def test_exact_name_wins_over_the_fuzzy_first_hit():
    # StashDB really does answer "Sara Jay" with "Sara Jaymes" first.
    assert PROFILES[0]["name"] == "Sara Jaymes", "the fixture keeps the real ranking"
    assert stashdb.best_match(PROFILES, "Sara Jay")["name"] == "Sara Jay"
    assert stashdb.best_match(PROFILES, "sara jay")["name"] == "Sara Jay"
    assert stashdb.best_match(list(reversed(PROFILES)), "Sara Jay")["name"] == "Sara Jay"


def test_aliases_are_matched_too():
    assert stashdb.best_match(PROFILES, "Sarah Jay")["name"] == "Sara Jay"
    assert stashdb.best_match(PROFILES, "Sarah Jaymes")["name"] == "Sara Jaymes"


def test_ambiguous_leftovers_are_rejected():
    # Two candidates and neither matches: showing either would be a guess.
    assert stashdb.best_match(PROFILES, "Someone Else") is None
    assert stashdb.best_match(PROFILES[:1], "Someone Else")["name"] == "Sara Jaymes"


def test_best_match_ignores_empty_names():
    assert stashdb.best_match(PROFILES, "") is None
    assert stashdb.best_match([], "Sara Jay") is None


# --- transport ------------------------------------------------------------

def test_search_sends_the_key_and_a_parameterised_query(calls):
    profiles = stashdb.search("Sara Jay")

    assert len(calls) == 1
    call = calls[0]
    assert call["url"] == stashdb.ENDPOINT
    assert call["headers"]["ApiKey"] == "test-key"
    assert "queryPerformers" in call["json"]["query"]
    assert "$names" in call["json"]["query"]
    # The name travels as a variable, never spliced into the query text.
    assert call["json"]["variables"] == {"names": "Sara Jay", "perPage": stashdb.PAGE_SIZE}
    assert [profile["name"] for profile in profiles] == ["Sara Jaymes", "Sara Jay"]


def test_search_is_cached_for_the_day(calls):
    first = stashdb.search("Sara Jay")
    second = stashdb.search("Sara Jay")

    assert len(calls) == 1, "the second call must come from the cache"
    assert first == second


def test_cache_can_be_bypassed(calls):
    stashdb.search("Sara Jay")
    stashdb.search("Sara Jay", use_cache=False)
    assert len(calls) == 2


def test_graphql_errors_are_empty_and_not_cached(monkeypatch, configured):
    """A 200 with ``errors`` is how StashDB says "not authorized"."""
    posts = []

    def fake_post(url, json=None, headers=None, timeout=None, **kwargs):
        posts.append(json)
        return FakeResponse({"errors": [{"message": "not authorized"}], "data": None})

    monkeypatch.setattr(stashdb.requests, "post", fake_post)

    assert stashdb.search("Sara Jay") == []
    assert stashdb.search("Sara Jay") == []
    assert len(posts) == 2, "an auth failure must not be cached as 'no such person'"


def test_http_errors_are_swallowed(monkeypatch, configured):
    monkeypatch.setattr(
        stashdb.requests, "post", lambda *a, **k: FakeResponse({}, status_code=503)
    )
    assert stashdb.search("Sara Jay") == []


def test_offline_is_not_an_exception(monkeypatch, configured):
    def boom(*args, **kwargs):
        raise requests.ConnectionError("no network")

    monkeypatch.setattr(stashdb.requests, "post", boom)
    assert stashdb.lookup("Sara Jay") is None


def test_lookup_returns_the_matching_profile(calls):
    assert stashdb.lookup("Sara Jay")["name"] == "Sara Jay"
    assert stashdb.lookup("Nobody At All") is None


def test_blank_names_never_reach_the_network(calls):
    assert stashdb.search("   ") == []
    assert calls == []


# --- rendering ------------------------------------------------------------

def test_stashdb_profile_renders_through_the_shared_renderer():
    markup = profile_html(SARA)
    assert "StashDB" in markup, "the source label comes from the profile"
    assert "36-25-41" in markup
    assert "163cm" in markup
    assert "American" in markup
    assert "alias-chip" in markup
    assert "Sarah Jay" in markup


def test_rendered_stashdb_profile_escapes_values():
    markup = profile_html(
        {
            "name": "<script>alert(1)</script>",
            "image": '"><img src=x onerror=alert(1)>',
            "extras": {"height": "<b>163</b>"},
            "aliases": ["<i>x</i>"],
            "source": "<StashDB>",
        }
    )
    assert "<script>" not in markup
    assert "<b>163</b>" not in markup
    assert "<i>x</i>" not in markup
    assert "&lt;StashDB&gt;" in markup


def test_scene_count_shows_up_in_the_stat_grid():
    assert dict(profile_rows(SARA))["Scenes"] == "570"
    assert dict(profile_rows(SARA))["Active since"] == "2001"


def test_profile_dialog_tabs_both_sources(monkeypatch):
    """With two keys, the dialog shows one tab per source; each keeps its label."""
    from streamlit.testing.v1 import AppTest
    from models.performer import Performer
    from scraper import porndb

    porndb_profile = {
        "name": "Sara Jay",
        "image": "",
        "extras": {"height": "163cm", "measurements": "36E-25-41"},
        "aliases": [],
        "links": {},
        "source": "ThePornDB",
    }

    monkeypatch.setenv("PORNDB_API_KEY", "test-key")
    monkeypatch.setenv("STASHDB_API_KEY", "test-key")
    monkeypatch.setattr(porndb, "lookup", lambda name, use_cache=True: porndb_profile)
    monkeypatch.setattr(stashdb, "lookup", lambda name, use_cache=True: SARA)

    at = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=90)
    at.session_state["performers"] = [
        Performer(name="Sara Jay", slug="sara-jay", source="freeones")
    ]
    at.run()
    next(button for button in at.button if button.key == "profile_sara-jay").click().run()

    assert not at.exception, [f"{e.type}: {e.value}" for e in at.exception]
    assert [tab.label for tab in at.tabs] == ["ThePornDB", "StashDB"]

    markup = " ".join(block.value for block in at.markdown)
    assert "36E-25-41" in markup, "the ThePornDB panel"
    assert "36-25-41" in markup, "the StashDB panel"


# --- live -----------------------------------------------------------------

@pytest.mark.live
def test_live_lookup_returns_a_real_profile():
    if not stashdb.is_configured():
        pytest.skip("STASHDB_API_KEY is not configured")

    profile = stashdb.lookup("Sara Jay", use_cache=False)

    assert profile is not None
    assert profile["name"].lower() == "sara jay", "not the 'Sara Jaymes' ranked first"
    assert profile["links"]["StashDB"].startswith(stashdb.SITE)

    extras = profile["extras"]
    assert extras["height"].endswith("cm")
    assert extras["measurements"].count("-") == 2
    assert extras["nationality"]
    assert profile["aliases"], "the alias list survives the round trip"
    assert not any(alias.startswith("[") for alias in profile["aliases"])


@pytest.mark.live
def test_live_portrait_needs_no_key_to_view():
    """The dialog shows the image in the user's browser, which has no ApiKey."""
    if not stashdb.is_configured():
        pytest.skip("STASHDB_API_KEY is not configured")

    profile = stashdb.lookup("Sara Jay", use_cache=False)
    response = requests.get(profile["image"], timeout=30, stream=True)
    try:
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("image/")
    finally:
        response.close()


@pytest.mark.live
def test_live_profile_dialog_shows_both_sources():
    """End to end: the real APIs through the real dialog."""
    from streamlit.testing.v1 import AppTest
    from models.performer import Performer
    from scraper import porndb

    if not porndb.is_configured() or not stashdb.is_configured():
        pytest.skip("needs both PORNDB_API_KEY and STASHDB_API_KEY")

    at = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=120)
    at.session_state["performers"] = [
        Performer(name="Sara Jay", slug="sara-jay", source="freeones")
    ]
    at.run()
    next(button for button in at.button if button.key == "profile_sara-jay").click().run()

    assert not at.exception, [f"{e.type}: {e.value}" for e in at.exception]
    assert [tab.label for tab in at.tabs] == ["ThePornDB", "StashDB"]

    markup = " ".join(block.value for block in at.markdown)
    assert "stashdb.org/images/" in markup, "the StashDB portrait"
    assert "36E-25-41" in markup, "ThePornDB's measurements"
    assert "36-25-41" in markup, "StashDB's band-waist-hip"
    assert "['" not in markup, "aliases render as text, not as a repr of a list"
