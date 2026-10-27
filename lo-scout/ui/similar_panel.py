"""Similar-performer dialog: the current profile's window, filled by Freeones.

The caption matters as much as the grid. "Similar" without a stated basis is a
promise the app cannot keep from a listing card; ``same gender, 157-169 cm`` is
both true and checkable by the user.
"""

import html
from typing import Any, Dict, List, Optional

import streamlit as st

from config import FREEONES_BASE_URL
from models.performer import Performer
from scraper import porndb, similar


def profile_url(slug: str) -> str:
    """Return a performer's Freeones profile URL (``/sara-jay``, verified 200)."""
    return f"{FREEONES_BASE_URL}/{slug}" if slug else FREEONES_BASE_URL


def result_html(performer: Performer) -> str:
    """Return the portrait + name block for one similar performer (escaped)."""
    name = html.escape(performer.name)
    portrait = html.escape(performer.image_url, quote=True)
    image = (
        f'<img class="similar-portrait" src="{portrait}" alt="{name}" loading="lazy" '
        f'decoding="async" referrerpolicy="no-referrer">'
        if portrait
        else '<div class="similar-portrait similar-portrait-empty" aria-hidden="true"></div>'
    )
    return f'<div class="similar-head">{image}<div class="similar-name">{name}</div></div>'


def _render(performers: List[Performer], columns: int = 3) -> None:
    if not performers:
        return
    grid = st.columns(columns)
    for position, performer in enumerate(performers):
        with grid[position % columns]:
            st.markdown(result_html(performer), unsafe_allow_html=True)
            st.link_button(
                "Open on Freeones",
                profile_url(performer.slug),
                use_container_width=True,
            )


@st.dialog("Similar performers", width="large")
def show_similar(
    name: str, slug: str = "", profile: Optional[Dict[str, Any]] = None
) -> None:
    """Open the similar dialog for ``name``. Call only from a button click."""
    if profile is None:
        profile = porndb.lookup(name)

    if not profile:
        st.info(
            f"No ThePornDB profile for **{html.escape(name)}**, so there are no "
            "stats to match on. Similar needs a height or weight to work from."
        )
        return

    filters = similar.filters_for(profile)
    if not filters.has_filters():
        st.info(
            f"ThePornDB has no height or weight for **{html.escape(name)}**, and "
            "Freeones can only filter on what it stores per performer. Try the "
            "height range in the sidebar instead."
        )
        return

    with st.spinner("Asking Freeones for the same window..."):
        results, filters = similar.find_similar(profile, exclude_slug=slug)

    st.caption(
        f"Matched on {similar.describe(filters)} -- filtered by Freeones itself, "
        "so every performer below falls inside that range."
    )
    if not results:
        st.warning("Nothing came back for that window. It may simply be a quiet one.")
        return

    _render(results)
