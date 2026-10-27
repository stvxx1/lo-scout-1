"""Find-similar: the window derivation, and what reaches Freeones.

The point of these tests is that the dialog cannot overclaim. Every assertion
here is about the window being real (so the caption is true), clamped to the
facet's own domain (so results aren't flooded by unrecorded values), and absent
when the profile has no stats (so the button explains itself instead of returning
strangers).
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "lo-scout"
sys.path.insert(0, str(APP_DIR))

from models.filters import FilterConfig                             # noqa: E402
from models.performer import Performer                              # noqa: E402
from scraper import similar                                         # noqa: E402
from scraper.base import ScraperError                               # noqa: E402

PROFILE = {
    "name": "Sara Jay",
    "extras": {"height": "163 cm", "weight": "68kg", "measurements": "36-28-44"},
}


class FakeScraper:
    def __init__(self, performers=None, error=None):
        self.performers = performers or []
        self.error = error
        self.calls = []

    def fetch_performers(self, page, filters):
        self.calls.append((page, filters))
        if self.error:
            raise self.error
        return self.performers


def performer(name, slug):
    return Performer(name=name, slug=slug, image_url=f"https://cdn/{slug}.jpg")


# --- the window -----------------------------------------------------------

def test_window_surrounds_the_anchor():
    filters = similar.filters_for(PROFILE)
    assert (filters.min_height, filters.max_height) == (163 - 6, 163 + 6)
    assert (filters.min_weight, filters.max_weight) == (68 - 8, 68 + 8)


def test_window_is_clamped_to_the_facet_domain():
    """Below the facet floor a window also matches unrecorded values."""
    tiny = similar.filters_for({"extras": {"height": "101 cm"}})
    assert (tiny.min_height, tiny.max_height) == (100, 107)

    huge = similar.filters_for({"extras": {"height": "299 cm"}})
    assert (huge.min_height, huge.max_height) == (293, 300)


def test_numeric_and_suffixed_values_both_parse():
    assert similar.filters_for({"extras": {"height": 163}}).min_height == 157
    assert similar.filters_for({"extras": {"height": "163cm"}}).min_height == 157


def test_no_stats_means_no_window():
    for extras in ({}, {"measurements": "36-28-44"}, {"height": "unknown"}):
        filters = similar.filters_for({"extras": extras})
        assert not filters.has_filters()
        assert filters.gender == "babes"


def test_missing_profile_is_not_an_error():
    assert not similar.filters_for(None).has_filters()


def test_gender_is_carried_through():
    assert similar.filters_for({"extras": {"height": "163 cm"}}, "males").gender == "males"


def test_window_lands_on_the_facet_freeones_actually_filters_by():
    params = similar.filters_for(PROFILE).to_url_params()
    assert params["r[appearance.metric.height]"] == "157,169"
    assert params["r[appearance.metric.weight]"] == "60,76"
    assert params["f[performerType]"] == "babe"


def test_describe_states_the_window():
    assert similar.describe(similar.filters_for(PROFILE)) == "157-169 cm, 60-76 kg"
    assert similar.describe(FilterConfig()) == "same gender only"


# --- the results ----------------------------------------------------------

def test_find_similar_excludes_the_clicked_performer():
    scraper = FakeScraper([performer("Sara Jay", "sara-jay"), performer("Rissa May", "rissa-may")])
    results, filters = similar.find_similar(PROFILE, exclude_slug="sara-jay", scraper=scraper)

    assert [p.slug for p in results] == ["rissa-may"]
    assert filters.min_height == 157


def test_find_similar_fetches_one_page_only():
    scraper = FakeScraper([performer("Rissa May", "rissa-may")])
    similar.find_similar(PROFILE, scraper=scraper)
    assert [call[0] for call in scraper.calls] == [1]


def test_find_similar_respects_the_limit():
    scraper = FakeScraper([performer(f"Person {n}", f"person-{n}") for n in range(20)])
    results, _ = similar.find_similar(PROFILE, limit=5, scraper=scraper)
    assert len(results) == 5


def test_no_stats_means_no_request():
    scraper = FakeScraper()
    results, filters = similar.find_similar({"name": "Ghost", "extras": {}}, scraper=scraper)
    assert results == []
    assert not filters.has_filters()
    assert scraper.calls == [], "there is nothing to search for, so nothing is fetched"


def test_a_failed_fetch_is_an_empty_dialog_not_a_traceback():
    scraper = FakeScraper(error=ScraperError("freeones is down"))
    results, filters = similar.find_similar(PROFILE, scraper=scraper)
    assert results == []
    assert filters.min_height == 157, "the window is still worth reporting"


# --- the dialog helpers ---------------------------------------------------

def test_profile_url_points_at_freeones():
    from ui.similar_panel import profile_url

    assert profile_url("sara-jay") == "https://www.freeones.com/sara-jay"
    assert profile_url("") == "https://www.freeones.com"


def test_result_html_escapes_the_name_and_the_image():
    from ui.similar_panel import result_html

    markup = result_html(
        Performer(name="<script>x</script>", slug="x", image_url='"><img src=x>')
    )
    assert "<script>" not in markup
    assert 'src=""><img' not in markup
    assert "similar-portrait" in markup


def test_anchor_text_names_the_stat_the_window_came_from():
    from ui.similar_panel import anchor_text

    assert anchor_text(PROFILE) == "163 cm"
    assert anchor_text({"extras": {"weight": "68kg"}}) == "68 kg"
    assert anchor_text({"extras": {}}) == ""


def test_result_html_survives_a_missing_portrait():
    from ui.similar_panel import result_html

    markup = result_html(Performer(name="Ghost", slug="ghost"))
    assert "similar-portrait-empty" in markup
    assert "Ghost" in markup


@pytest.mark.parametrize("spread", [similar.HEIGHT_SPREAD, similar.WEIGHT_SPREAD])
def test_spreads_stay_small_enough_to_be_similar(spread):
    # A wide net would make "similar" meaningless; keep both windows tight.
    assert 0 < spread <= 10


# --- wiring ---------------------------------------------------------------

def test_similar_button_only_appears_with_a_key(monkeypatch):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=90)
    at.session_state["performers"] = [
        Performer(name="Sara Jay", slug="sara-jay", source="freeones")
    ]
    at.run()

    assert not at.exception, [f"{e.type}: {e.value}" for e in at.exception]
    assert not any("Similar" in button.label for button in at.button)

    monkeypatch.setenv("PORNDB_API_KEY", "test-key")
    at.run()

    assert not at.exception, [f"{e.type}: {e.value}" for e in at.exception]
    assert any("Similar" in button.label for button in at.button)


def test_profile_button_appears_with_only_a_stashdb_key(monkeypatch):
    """StashDB is a profile source in its own right, and the cheaper key to get.

    The grid used to gate its button on ThePornDB, which left a StashDB-only
    setup with a working dialog and no way to open it.
    """
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("STASHDB_API_KEY", "test-key")

    at = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=90)
    at.session_state["performers"] = [
        Performer(name="Sara Jay", slug="sara-jay", source="freeones")
    ]
    at.run()

    assert not at.exception, [f"{e.type}: {e.value}" for e in at.exception]
    assert any("Profile" in button.label for button in at.button)
    assert not any("Similar" in button.label for button in at.button), (
        "Similar needs ThePornDB for the anchor, not merely any key"
    )


def _dialog_after_click(monkeypatch, lookup):
    """Open the grid with one performer and click its Similar button."""
    from streamlit.testing.v1 import AppTest
    from scraper import porndb

    monkeypatch.setenv("PORNDB_API_KEY", "test-key")
    monkeypatch.setattr(porndb, "lookup", lookup)

    at = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=90)
    at.session_state["performers"] = [
        Performer(name="Sara Jay", slug="sara-jay", source="freeones")
    ]
    at.run()
    next(button for button in at.button if button.key == "similar_sara-jay").click().run()
    return at


def test_similar_dialog_explains_missing_stats(monkeypatch):
    at = _dialog_after_click(monkeypatch, lambda name, use_cache=True: None)

    assert not at.exception, [f"{e.type}: {e.value}" for e in at.exception]
    assert any("stats to match on" in info.value for info in at.info)


def test_similar_dialog_renders_the_stated_window(monkeypatch):
    monkeypatch.setattr(
        similar,
        "FreeonesScraper",
        lambda *args, **kwargs: FakeScraper(
            [performer("Sara Jay", "sara-jay"), performer("Rissa May", "rissa-may")]
        ),
    )

    at = _dialog_after_click(monkeypatch, lambda name, use_cache=True: PROFILE)

    assert not at.exception, [f"{e.type}: {e.value}" for e in at.exception]
    captions = " ".join(caption.value for caption in at.caption)
    assert "157-169 cm, 60-76 kg" in captions, "the caption must state the window"
    assert "ThePornDB's 163 cm for Sara Jay" in captions, (
        "the caption must name the anchor, so a wrong match is visible"
    )

    markup = " ".join(block.value for block in at.markdown if "similar-head" in block.value)
    assert "Rissa May" in markup
    assert "Sara Jay" not in markup, "the clicked performer is never her own suggestion"

    links = [button for button in at.link_button if button.label == "Open on Freeones"]
    assert len(links) == 1


# --- live -----------------------------------------------------------------

@pytest.mark.live
def test_live_window_returns_performers_from_freeones():
    """End to end: a real profile, a real filter, real results.

    This is the only check that the height facet still does what the caption
    claims. It needs both a ThePornDB key (for the stats) and the network.
    """
    from scraper import porndb

    if not porndb.is_configured():
        pytest.skip("PORNDB_API_KEY is not configured")

    profile = porndb.lookup("Sara Jay")
    if not profile or not (profile.get("extras") or {}).get("height"):
        pytest.skip("ThePornDB did not return a height to anchor the window")

    results, filters = similar.find_similar(profile, exclude_slug="sara-jay")

    assert filters.min_height is not None
    assert results, "Freeones returned nothing for a window around a known height"
    assert all(p.slug != "sara-jay" for p in results)
    assert all(p.name and p.slug for p in results)
