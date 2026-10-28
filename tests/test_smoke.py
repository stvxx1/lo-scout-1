"""Offline tests for the Freeones scraper and the Streamlit UI.

    pytest -q            offline, uses the saved listing fixture
    pytest -q -m live    hits freeones.com, ~30s
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "lo-scout"
sys.path.insert(0, str(APP_DIR))

from models.filters import FilterConfig        # noqa: E402
from models.performer import Performer         # noqa: E402
from scraper.freeones import FreeonesScraper   # noqa: E402
from ui.components import ANY_OPTION, render_filter_summary  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "fo_asc48.html"


# --- URL building ---------------------------------------------------------

def test_pagination_respects_robots_txt():
    first = FreeonesScraper().build_search_url(FilterConfig(), 1)
    deeper = FreeonesScraper().build_search_url(FilterConfig(), 3)

    # robots.txt: Disallow /*p=1$ -- page one must not carry a page param at all.
    assert "p=" not in first
    assert "p=3" in deeper

    # robots.txt: Disallow /*s=, /*o=, /*l= -- the default order already is
    # rank ascending and the default page size already matches ITEMS_PER_PAGE.
    for forbidden in ("s=", "o=", "l="):
        assert forbidden not in first, first
        assert forbidden not in deeper, deeper


def test_no_range_params_by_default():
    assert not any(key.startswith("r[") for key in FilterConfig().to_url_params())


def test_range_facets_use_site_syntax():
    params = FilterConfig(min_height=195, max_height=215).to_url_params()
    assert params["r[appearance.metric.height]"] == "195,215"


def test_open_ended_range_uses_domain_bounds():
    assert FilterConfig(max_height=155).to_url_params()["r[appearance.metric.height]"] == "100,155"
    assert FilterConfig(min_weight=80).to_url_params()["r[appearance.metric.weight]"] == "80,500"


def test_penis_length_only_for_males():
    assert "r[appearance.metric.penisLength]" not in FilterConfig(min_dick_length=18).to_url_params()
    males = FilterConfig(gender="males", min_dick_length=18).to_url_params()
    assert males["r[appearance.metric.penisLength]"] == "18,50"


def test_age_is_a_range_facet():
    assert FilterConfig(min_age=25, max_age=32).to_url_params()["r[age]"] == "25,32"


def test_open_ended_age_uses_facet_bounds():
    # 18 is freeones' own floor, so a max-only age filter must not start at 0 --
    # that would also match profiles with no age recorded.
    assert FilterConfig(max_age=30).to_url_params()["r[age]"] == "18,30"


def test_select_facets_use_slug_params():
    params = FilterConfig(ethnicity="latin", tattoos="no", piercings="yes").to_url_params()
    assert params["f[ethnicity]"] == "latin"
    assert params["f[tattoos]"] == "no"
    assert params["f[piercings]"] == "yes"


def test_select_facets_are_absent_when_unset():
    params = FilterConfig().to_url_params()
    for facet in ("ethnicity", "tattoos", "piercings"):
        assert f"f[{facet}]" not in params


def test_unknown_slug_is_rejected_before_the_site_sees_it():
    # freeones answers an unknown slug with an empty page rather than an error,
    # which would surface as "no performers match" and look like a bug.
    with pytest.raises(ValueError):
        FilterConfig(ethnicity="klingon")
    with pytest.raises(ValueError):
        FilterConfig(tattoos="a-few")


def test_select_filter_alone_counts_as_active():
    assert FilterConfig(ethnicity="caucasian").has_filters()
    assert FilterConfig(min_age=30).has_filters()


def test_inverted_age_range_is_rejected():
    with pytest.raises(ValueError):
        FilterConfig(min_age=40, max_age=30)


# --- parsing --------------------------------------------------------------

def test_parser_reads_listing_fixture():
    performers = FreeonesScraper().parse_performers(FIXTURE.read_text(encoding="utf-8"))
    assert len(performers) == 48
    assert sum(1 for p in performers if p.image_url) == 48
    assert performers[0].name == "Sara Jay"
    assert all(p.slug for p in performers)


def test_parser_survives_garbage():
    assert FreeonesScraper().parse_performers("<html><body>nothing</body></html>") == []


# --- UI crash paths -------------------------------------------------------

def _app():
    from streamlit.testing.v1 import AppTest

    return AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=90)


def test_inverted_range_is_swapped_not_fatal():
    at = _app()
    at.session_state["filter_min_height"] = 180
    at.session_state["filter_max_height"] = 150
    at.run()
    assert not at.exception, [f"{e.type}: {e.value}" for e in at.exception]
    assert any("swapped" in w.value.lower() for w in at.warning)


def test_clear_filters_does_not_crash():
    at = _app()
    at.session_state["filter_min_height"] = 180
    at.run()
    buttons = [b for b in at.button if "Clear Filters" in b.label]
    assert buttons, "clear filters button missing"
    buttons[0].click()
    at.run()
    assert not at.exception, [f"{e.type}: {e.value}" for e in at.exception]
    assert at.session_state["filter_min_height"] is None


def test_changed_filters_offer_a_rescan():
    at = _app()
    at.session_state["last_filters"] = FilterConfig()
    at.session_state["performers"] = [Performer(name="Test", slug="test", source="freeones")]
    at.session_state["filter_min_height"] = 195
    at.run()
    assert not at.exception, [f"{e.type}: {e.value}" for e in at.exception]
    assert any("APPLY FILTERS" in b.label for b in at.button)


def test_age_and_look_filters_reach_the_config():
    """A new widget only matters if it lands in the FilterConfig the app compares.

    Comparing against an empty config is what raises APPLY FILTERS, so the button
    appearing proves the widget value survived the sidebar round trip.
    """
    at = _app()
    at.session_state["last_filters"] = FilterConfig()
    at.session_state["performers"] = [Performer(name="Test", slug="test", source="freeones")]
    at.session_state["filter_age_range"] = (25, 32)
    at.session_state["filter_ethnicity"] = "latin"
    at.session_state["filter_tattoos"] = "no"
    at.session_state["filter_piercings"] = "yes"
    at.run()
    assert not at.exception, [f"{e.type}: {e.value}" for e in at.exception]
    assert any("APPLY FILTERS" in b.label for b in at.button)


def test_clear_filters_resets_look_filters():
    at = _app()
    at.session_state["filter_ethnicity"] = "latin"
    at.run()
    [b for b in at.button if "Clear Filters" in b.label][0].click()
    at.run()
    assert not at.exception, [f"{e.type}: {e.value}" for e in at.exception]
    assert at.session_state["filter_ethnicity"] == ANY_OPTION


def test_filter_summary_lists_new_filters():
    summary = render_filter_summary(
        FilterConfig(min_age=25, max_age=32, ethnicity="latin", tattoos="no", piercings="yes")
    )
    assert ">=25y" in summary and "<=32y" in summary
    assert "Ethnicity:" in summary and "Latin" in summary
    assert "Tattoos:" in summary and "Piercings:" in summary


# --- live -----------------------------------------------------------------

@pytest.mark.live
def test_live_first_page_is_top_ranked_with_images():
    performers = FreeonesScraper().fetch_performers(1, FilterConfig())
    # Freeones' default page size is 24; only assert it is a real page.
    assert len(performers) >= 20
    assert sum(1 for p in performers if p.image_url) >= len(performers) - 2


@pytest.mark.live
def test_live_height_filter_narrows_results():
    performers = FreeonesScraper().fetch_performers(1, FilterConfig(min_height=195, max_height=215))
    assert 0 < len(performers) < 48


@pytest.mark.live
def test_live_load_more_advances_pages():
    at = _app()
    at.run()
    [b for b in at.button if "AUTO-SCAN" in b.label][0].click()
    at.run()
    first_page = len(at.session_state["performers"])
    assert first_page >= 20

    more = [b for b in at.button if "LOAD MORE" in b.label]
    assert more, "LOAD MORE not shown"
    more[0].click()
    at.run()
    assert len(at.session_state["performers"]) > first_page
    assert at.session_state["current_page"] == 2
