"""
Profile dialog: the metadata Freeones' listing pages don't carry.

Everything shown here comes from ThePornDB, so the dialog is also where the
"no API key" case has to be explained -- there is no other source for a bio or
measurements.
"""

import html
from typing import Any, Dict, List, Tuple

import streamlit as st

from scraper import porndb

SEARCH_URL = "https://theporndb.net/performers?q="


def profile_rows(profile: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Return the ``(label, value)`` pairs for a profile's stat grid.

    Blank attributes are dropped rather than rendered as "—": a grid of empty
    labels is worse than no grid.
    """
    extras = profile.get("extras") or {}
    rows: List[Tuple[str, str]] = []

    age = porndb.age_from(extras.get("birthday"))
    birthday = extras.get("birthday")
    if birthday:
        rows.append(("Born", f"{birthday}{f' ({age})' if age else ''}"))
    elif age:
        rows.append(("Age", str(age)))

    for label, key, suffix in (
        ("Height", "height", ""),
        ("Weight", "weight", ""),
        ("Measurements", "measurements", ""),
        ("Cup", "cupsize", ""),
        ("Hair", "hair_colour", ""),
        ("Eyes", "eye_colour", ""),
        ("Ethnicity", "ethnicity", ""),
        ("Nationality", "nationality", ""),
        ("Birthplace", "birthplace", ""),
        ("Star sign", "astrology", ""),
    ):
        value = extras.get(key)
        if value:
            rows.append((label, f"{value}{suffix}"))

    career = extras.get("career_start_year")
    if career:
        rows.append(("Active since", str(career)))

    rating = profile.get("rating")
    if rating:
        rows.append(("Rating", f"{float(rating):.2f} / 5"))

    return rows


def profile_html(profile: Dict[str, Any]) -> str:
    """Return the header, stat grid, bio and aliases as one escaped HTML block."""
    name = html.escape(profile.get("name", ""))
    portrait = profile.get("image") or profile.get("face") or ""
    rows = profile_rows(profile)

    image = ""
    if portrait:
        image = (
            f'<img class="profile-portrait" src="{html.escape(portrait, quote=True)}" '
            f'alt="{name}" loading="lazy" decoding="async" referrerpolicy="no-referrer">'
        )

    stats = "".join(
        f'<div class="profile-stat"><span class="profile-stat-label">{html.escape(label)}</span>'
        f'<span class="profile-stat-value">{html.escape(value)}</span></div>'
        for label, value in rows
    )
    stats_block = f'<div class="profile-stats">{stats}</div>' if stats else ""

    bio = profile.get("bio") or ""
    bio_block = f'<p class="profile-bio">{html.escape(bio)}</p>' if bio else ""

    aliases = profile.get("aliases") or []
    alias_block = ""
    if aliases:
        chips = "".join(
            f'<span class="alias-chip">{html.escape(alias)}</span>' for alias in aliases
        )
        alias_block = f'<div class="profile-aliases">{chips}</div>'

    return (
        f'<div class="profile-head">{image}'
        f'<div class="profile-identity"><h2 class="profile-name">{name}</h2>'
        f'<div class="profile-source">ThePornDB</div></div></div>'
        f"{stats_block}{bio_block}{alias_block}"
    )


@st.dialog("Profile", width="large")
def show_profile(name: str) -> None:
    """Open the profile dialog for ``name``. Call only from a button click."""
    if not porndb.is_configured():
        st.warning(
            "No ThePornDB API key configured. Set **PORNDB_API_KEY** (environment "
            "variable or `.streamlit/secrets.toml`) and reload to see bios, "
            "measurements and links here."
        )
        return

    profile = porndb.lookup(name)
    if not profile:
        st.info(f"ThePornDB has no profile for **{html.escape(name)}**.")
        return

    st.markdown(profile_html(profile), unsafe_allow_html=True)

    links = profile.get("links") or {}
    if links:
        st.markdown("---")
        columns = st.columns(min(len(links), 4))
        for position, (label, url) in enumerate(sorted(links.items())):
            with columns[position % len(columns)]:
                st.link_button(label, url, use_container_width=True)
