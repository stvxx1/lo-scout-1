"""Favourites, settings, reply cache and external-id mappings.

    pytest -q    fully offline (sqlite in a temp dir)
"""
import json
import sqlite3
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "lo-scout"
sys.path.insert(0, str(APP_DIR))

import storage                                        # noqa: E402
from models.performer import Performer                # noqa: E402
from paths import db_path                             # noqa: E402

SARA = Performer(
    name="Sara Jay",
    slug="sara-jay",
    image_url="https://thumbs.freeones.com/photo/x/350x466/y/sara-jay.jpg",
    source="freeones",
    height=165,
    measurements="34DD",
)


# --- favourites -----------------------------------------------------------

def test_add_and_list_round_trips_every_field():
    storage.add_favorite(SARA)
    [restored] = storage.list_favorites()

    assert restored == SARA
    assert restored.measurements == "34DD"


def test_list_favorites_is_newest_first():
    storage.add_favorite(SARA)
    time.sleep(0.01)
    storage.add_favorite(Performer(name="Zazie Skymm", slug="zazie-skymm", source="freeones"))

    assert [p.slug for p in storage.list_favorites()] == ["zazie-skymm", "sara-jay"]
    assert [p.slug for p in storage.list_favorites(limit=1)] == ["zazie-skymm"]


def test_toggle_flips_state():
    assert storage.toggle_favorite(SARA) is True
    assert storage.is_favorite("sara-jay")
    assert storage.toggle_favorite(SARA) is False
    assert not storage.is_favorite("sara-jay")


def test_adding_twice_does_not_duplicate():
    storage.add_favorite(SARA)
    storage.add_favorite(SARA)
    assert len(storage.list_favorites()) == 1


def test_remove_is_idempotent():
    storage.remove_favorite("never-saved")
    assert storage.favorite_slugs() == set()


def test_export_import_merges_and_is_idempotent():
    storage.add_favorite(SARA)
    exported = storage.export_favorites()
    assert json.dumps(exported)  # JSON-serialisable for download_button

    storage.add_favorite(Performer(name="Zazie Skymm", slug="zazie-skymm", source="freeones"))
    assert storage.import_favorites(exported) == 0, "re-import must not duplicate"
    assert len(storage.list_favorites()) == 2


def test_import_skips_rows_it_cannot_use():
    rows = [{"name": "Good One", "slug": "good-one"}, {"nope": 1}, "not a dict"]
    assert storage.import_favorites(rows) == 1


def test_corrupt_payload_does_not_break_the_grid():
    storage.add_favorite(SARA)
    connection = sqlite3.connect(db_path())
    with connection:
        connection.execute("UPDATE favorites SET payload = ? WHERE slug = ?", ("{broken", "sara-jay"))
    connection.close()

    assert storage.list_favorites() == []



# --- settings -------------------------------------------------------------

def test_settings_keep_json_types():
    assert storage.get_setting("missing", "fallback") == "fallback"

    storage.set_setting("last_sort", "Height (Tallest)")
    storage.set_setting("min_height", 195)
    storage.set_setting("flags", {"a": [1, 2]})

    assert storage.get_setting("last_sort") == "Height (Tallest)"
    assert storage.get_setting("min_height") == 195
    assert storage.get_setting("flags") == {"a": [1, 2]}


def test_setting_overwrites_in_place():
    storage.set_setting("k", 1)
    storage.set_setting("k", 2)
    assert storage.get_setting("k") == 2


# --- reply cache ----------------------------------------------------------

def test_cache_hits_until_it_expires():
    storage.cache_set("eporner:search:zazie", {"hits": 12}, ttl_seconds=60)
    assert storage.cache_get("eporner:search:zazie") == {"hits": 12}

    storage.cache_set("eporner:search:old", {"hits": 1}, ttl_seconds=-1)
    assert storage.cache_get("eporner:search:old") is None


def test_cache_miss_returns_none():
    assert storage.cache_get("never-fetched") is None


def test_cache_clear_by_prefix():
    storage.cache_set("stashdb:a", 1, ttl_seconds=60)
    storage.cache_set("stashdb:b", 2, ttl_seconds=60)
    storage.cache_set("eporner:c", 3, ttl_seconds=60)

    storage.cache_clear("stashdb:")
    assert storage.cache_get("stashdb:a") is None
    assert storage.cache_get("eporner:c") == 3


# --- external ids ---------------------------------------------------------

def test_external_ids_are_keyed_by_source():
    storage.set_external_id("zazie-skymm", "stashdb", "0e2a...", {"name": "Zazie Skymm"})
    storage.set_external_id("zazie-skymm", "eporner", "zazie-skymm")

    assert storage.get_external_id("zazie-skymm", "stashdb") == "0e2a..."
    assert storage.get_external_record("zazie-skymm", "stashdb")["payload"] == {"name": "Zazie Skymm"}
    assert storage.get_external_id("zazie-skymm", "unknown") is None
    assert storage.get_external_record("nobody", "stashdb") is None



# --- UI -------------------------------------------------------------------

def _app():
    from streamlit.testing.v1 import AppTest

    return AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=90)


def test_save_button_persists_a_favourite():
    at = _app()
    at.session_state["performers"] = [SARA]
    at.run()
    assert not at.exception, [f"{e.type}: {e.value}" for e in at.exception]

    save = [b for b in at.button if "Save" in b.label]
    assert save, "no save button on the card"
    save[0].click()
    at.run()

    assert storage.is_favorite("sara-jay")
    assert any("Saved" in b.label for b in at.button)


def test_favourites_only_shows_saved_performers_without_a_scan():
    storage.add_favorite(SARA)

    at = _app()
    at.session_state["filter_favorites_only"] = True
    at.run()

    assert not at.exception, [f"{e.type}: {e.value}" for e in at.exception]
    rendered = " ".join(str(m.value) for m in at.markdown)
    assert "Sara Jay" in rendered
    assert not any("AUTO-SCAN" in b.label for b in at.button), "should not ask for a scan"


def test_favourites_only_with_nothing_saved_says_so():
    at = _app()
    at.session_state["filter_favorites_only"] = True
    at.run()

    assert not at.exception, [f"{e.type}: {e.value}" for e in at.exception]
    rendered = " ".join(str(m.value) for m in at.markdown)
    assert "No favourites" in rendered
