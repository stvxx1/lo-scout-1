"""ThePornDB lookups: key handling, matching, caching, enrichment.

    pytest -q            offline, replays the captured JSON fixture
    pytest -q -m live    also queries the real API (needs PORNDB_API_KEY)
"""
import json
import sys
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "lo-scout"
sys.path.insert(0, str(APP_DIR))

import storage                                                    # noqa: E402
from models.performer import Performer                            # noqa: E402
from scraper import porndb                                        # noqa: E402
from ui.profile_panel import profile_html, profile_rows            # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
PAYLOAD = json.loads((FIXTURES / "porndb_search.json").read_text(encoding="utf-8"))
PROFILES = porndb.parse_search(PAYLOAD)


@pytest.fixture
def configured(monkeypatch):
    """Configure a key through the environment."""
    monkeypatch.setenv("PORNDB_API_KEY", "test-key")
    return "test-key"


# --- credentials ----------------------------------------------------------

def test_key_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("PORNDB_API_KEY", "abc123")
    assert porndb.api_key() == "abc123"
    assert porndb.is_configured()


def test_key_can_come_from_a_secrets_file(tmp_path):
    (tmp_path / "secrets.toml").write_text('PORNDB_API_KEY = "from-file"\n', encoding="utf-8")
    assert porndb.api_key() == "from-file"


def test_key_can_come_from_a_porndb_section(tmp_path):
    (tmp_path / "secrets.toml").write_text('[porndb]\napi_key = "nested"\n', encoding="utf-8")
    assert porndb.api_key() == "nested"


def test_the_environment_wins_over_the_file(monkeypatch, tmp_path):
    (tmp_path / "secrets.toml").write_text('PORNDB_API_KEY = "from-file"\n', encoding="utf-8")
    monkeypatch.setenv("PORNDB_API_KEY", "from-env")
    assert porndb.api_key() == "from-env"


@pytest.mark.parametrize("body", ["", "not toml at all {{", 'PORNDB_API_KEY = ""\n'])
def test_unreadable_secrets_file_is_ignored(tmp_path, body):
    (tmp_path / "secrets.toml").write_text(body, encoding="utf-8")
    assert porndb.api_key() is None


def test_without_a_key_everything_is_silently_empty():
    assert not porndb.is_configured()
    assert porndb.search("Sara Jay") == []
    assert porndb.lookup("Sara Jay") is None
    assert porndb.enrich_portraits([Performer(name="Sara Jay", slug="sara-jay")]) == 0


# --- parsing --------------------------------------------------------------

def test_fixture_parses_into_profiles():
    assert len(PROFILES) == 2
    profile = PROFILES[0]

    assert profile["name"] == "Sara Jay"
    assert profile["slug"] == "sara-jay"
    assert profile["image"].startswith("https://cdn.theporndb.net/")
    assert profile["face"].startswith("https://thumb.theporndb.net/")
    assert profile["bio"]
    assert "Sarah Jay" in profile["aliases"]
    assert profile["extras"]["measurements"] == "36E-25-41"
    assert profile["links"]["IAFD"].startswith("https://www.iafd.com/")


def test_limit_is_respected():
    assert len(porndb.parse_search(PAYLOAD, limit=1)) == 1


@pytest.mark.parametrize(
    "payload", [None, {}, {"data": None}, {"data": [None]}, {"data": [{"slug": "x"}]}, "junk"]
)
def test_parsing_junk_yields_nothing(payload):
    assert porndb.parse_search(payload) == []


def test_non_http_links_are_dropped(monkeypatch):
    payload = {
        "data": [
            {
                "name": "Someone",
                "extras": {"links": {"Site": "https://ok", "Bad": "javascript:alert(1)"}},
            }
        ]
    }
    profile = porndb.parse_search(payload)[0]
    assert profile["links"] == {"Site": "https://ok"}


# --- matching -------------------------------------------------------------

def test_exact_name_beats_the_fuzzy_second_hit():
    assert porndb.best_match(PROFILES, "sara jay")["name"] == "Sara Jay"
    assert porndb.best_match(PROFILES, "Sara-Jay")["name"] == "Sara Jay"


def test_alias_matches_when_the_stage_name_differs():
    assert porndb.best_match(PROFILES, "Piera Gambetta")["name"] == "Sara Jay"


def test_a_stranger_matches_nothing():
    assert porndb.best_match(PROFILES, "Completely Different Person") is None
    assert porndb.best_match([], "Sara Jay") is None

# --- fetching and caching -------------------------------------------------

def test_request_sends_the_key_and_an_encoded_query(configured, monkeypatch):
    seen = {}

    def fake_get(url, key):
        seen["url"] = url
        seen["key"] = key
        return PAYLOAD

    monkeypatch.setattr(porndb, "_get_json", fake_get)
    profiles = porndb.search("Zoë Kravitz", limit=3)

    assert seen["url"] == "https://api.theporndb.net/performers?q=Zo%C3%AB%20Kravitz&per_page=3"
    assert seen["key"] == "test-key"
    assert len(profiles) == 2


def test_results_are_cached_for_a_day(configured, monkeypatch):
    calls = []

    def fake_get(url, key):
        calls.append(url)
        return PAYLOAD

    monkeypatch.setattr(porndb, "_get_json", fake_get)

    first = porndb.lookup("Sara Jay")
    second = porndb.lookup("Sara Jay")

    assert len(calls) == 1, "second lookup should come from sqlite"
    assert first == second
    assert storage.cache_get("porndb:sara jay")


def test_network_failure_is_not_cached(configured, monkeypatch):
    def boom(url, key):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(porndb, "_get_json", boom)

    assert porndb.search("Sara Jay") == []
    assert storage.cache_get("porndb:sara jay") is None, "a transient failure must retry"


def test_http_error_is_swallowed(configured, monkeypatch):
    class Response:
        status_code = 401

        def raise_for_status(self):
            raise requests.HTTPError("401 Unauthorized")

    monkeypatch.setattr(porndb.requests, "get", lambda *a, **k: Response())
    assert porndb.lookup("Sara Jay") is None


# --- enrichment -----------------------------------------------------------

def test_blank_fields_are_filled_from_the_profile():
    performer = Performer(name="Sara Jay", slug="sara-jay")

    porndb.enrich(performer, PROFILES[0])

    assert performer.image_url.startswith("https://cdn.theporndb.net/")
    assert performer.height == 163          # from "163cm"
    assert performer.weight == 68           # from "68kg"
    assert performer.ethnicity == "Caucasian"
    assert performer.measurements == "36E-25-41"
    assert performer.hair_color == "Blonde"
    assert performer.eye_color == "Hazel"
    assert performer.gender == "female"
    assert performer.age and performer.age > 40


def test_freeones_values_are_never_overwritten():
    performer = Performer(
        name="Sara Jay",
        slug="sara-jay",
        image_url="https://www.freeones.com/portrait.jpg",
        height=170,
        ethnicity="Mixed",
    )

    porndb.enrich(performer, PROFILES[0])

    assert performer.image_url == "https://www.freeones.com/portrait.jpg"
    assert performer.height == 170
    assert performer.ethnicity == "Mixed"
    assert performer.measurements == "36E-25-41", "blanks still get filled"


def test_enrich_without_a_profile_changes_nothing(monkeypatch):
    monkeypatch.setattr(porndb, "lookup", lambda name, use_cache=True: None)
    performer = Performer(name="Nobody", slug="nobody")
    assert porndb.enrich(performer).image_url == ""


def test_known_heights_and_weights_parse():
    assert porndb.centimetres("163cm") == 163
    assert porndb.centimetres("68kg") == 68
    assert porndb.centimetres("") is None
    assert porndb.centimetres(None) is None
    assert porndb.age_from("not a date") is None


def test_portrait_gaps_are_filled_within_the_budget(configured, monkeypatch):
    monkeypatch.setattr(porndb, "lookup", lambda name, use_cache=True: PROFILES[0])
    performers = [Performer(name=f"Performer {i}", slug=f"p{i}") for i in range(10)]

    filled = porndb.enrich_portraits(performers, limit=3)

    assert filled == 3
    assert [bool(p.image_url) for p in performers[:3]] == [True, True, True]
    assert not any(p.image_url for p in performers[3:])


def test_portraits_are_not_fetched_for_cards_that_have_one(configured, monkeypatch):
    calls = []
    monkeypatch.setattr(porndb, "lookup", lambda name, use_cache=True: calls.append(name))
    performers = [Performer(name="Has One", slug="has-one", image_url="https://x/y.jpg")]

    assert porndb.enrich_portraits(performers) == 0
    assert calls == []


# --- rendering ------------------------------------------------------------

def test_profile_rows_describe_the_fixture():
    rows = dict(profile_rows(PROFILES[0]))

    assert rows["Height"] == "163cm"
    assert rows["Measurements"] == "36E-25-41"
    assert rows["Born"].startswith("1977-11-14")
    assert rows["Ethnicity"] == "Caucasian"


def test_profile_rows_skip_empty_attributes():
    rows = dict(profile_rows({"name": "Ghost", "extras": {}}))
    assert rows == {}


def test_profile_html_escapes_everything_user_facing():
    profile = {
        "name": 'Eva "The Boss" <script>',
        "bio": "Tom & Jerry <b>",
        "aliases": ['<img src=x onerror=alert(1)>'],
        "image": "https://cdn.example/p.jpg?a=1&b=2",
        "extras": {"height": "160cm"},
    }

    markup = profile_html(profile)

    assert "<script>" not in markup
    assert "&lt;script&gt;" in markup
    assert "Tom &amp; Jerry &lt;b&gt;" in markup
    assert "<img" not in markup.replace('<img class="profile-portrait"', "")
    assert "a=1&amp;b=2" in markup


# --- wiring ---------------------------------------------------------------

def test_profile_button_only_appears_with_a_key(monkeypatch):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=90)
    at.session_state["performers"] = [
        Performer(name="Sara Jay", slug="sara-jay", source="freeones")
    ]
    at.run()

    assert not at.exception, [f"{e.type}: {e.value}" for e in at.exception]
    assert not any("Profile" in button.label for button in at.button)

    monkeypatch.setenv("PORNDB_API_KEY", "test-key")
    at.run()

    assert not at.exception, [f"{e.type}: {e.value}" for e in at.exception]
    assert any("Profile" in button.label for button in at.button)


# --- live -----------------------------------------------------------------

@pytest.mark.live
def test_live_lookup_returns_a_real_profile():
    if not porndb.is_configured():
        pytest.skip("PORNDB_API_KEY is not configured")

    profile = porndb.lookup("Sara Jay", use_cache=False)

    assert profile is not None
    assert profile["name"] == "Sara Jay"
    assert profile["image"].startswith("https://")
    assert profile["extras"].get("measurements")

