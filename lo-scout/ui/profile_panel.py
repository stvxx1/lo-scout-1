"""
Profile dialog: the metadata Freeones' listing pages don't carry.

ThePornDB is the primary source; StashDB is shown beside it when a key for it is
configured, because the two disagree often enough that the disagreement is
useful (curated band/waist/hip integers versus one measurements string). This is
also where the "no API key" case has to be explained -- there is no other source
for a bio or measurements.
"""

import html
from typing import Any, Dict, List, Tuple

import streamlit as st

from scraper import porndb, stashdb

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
        ("Scenes", "scenes", ""),
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


def profile_html(profile: Dict[str, Any], source: str = "") -> str:
    """Return the header, stat grid, bio and aliases as one escaped HTML block."""
    name = html.escape(profile.get("name", ""))
    portrait = profile.get("image") or profile.get("face") or ""
    rows = profile_rows(profile)
    source = source or profile.get("source") or "ThePornDB"

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
        f'<div class="profile-source">{html.escape(source)}</div></div></div>'
        f"{stats_block}{bio_block}{alias_block}"
    )


def _render_profile(profile: Dict[str, Any], source: str) -> None:
    """Render one source's profile plus its outbound links."""
    st.markdown(profile_html(profile, source), unsafe_allow_html=True)

    links = profile.get("links") or {}
    if not links:
        return
    st.markdown("---")
    columns = st.columns(min(len(links), 4))
    for position, (label, url) in enumerate(sorted(links.items())):
        with columns[position % len(columns)]:
            st.link_button(label, url, use_container_width=True)


def is_configured() -> bool:
    """Return whether *any* profile source has a key.

    The grid gates its button on this rather than on ThePornDB alone: StashDB is
    a profile source in its own right, and gating both dialogs on one key left a
    StashDB-only setup with a working dialog and no way to open it.
    """
    return porndb.is_configured() or stashdb.is_configured()


def _panels(name: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Return the profiles available for ``name``, primary source first."""
    panels: List[Tuple[str, Dict[str, Any]]] = []
    if porndb.is_configured():
        profile = porndb.lookup(name)
        if profile:
            panels.append(("ThePornDB", profile))
    if stashdb.is_configured():
        profile = stashdb.lookup(name)
        if profile:
            panels.append(("StashDB", profile))
    return panels


@st.dialog("Profile", width="large")
def show_profile(name: str) -> None:
    """Open the profile dialog for ``name``. Call only from a button click."""
    if not is_configured():
        st.warning(
            "No metadata API key configured. Set **PORNDB_API_KEY** (environment "
            "variable or `.streamlit/secrets.toml`) and reload to see bios, "
            "measurements and links here. **STASHDB_API_KEY** adds a second source."
        )
        return

    panels = _panels(name)
    if not panels:
        sought = " and ".join(
            source
            for source, configured in (
                ("ThePornDB", porndb.is_configured()),
                ("StashDB", stashdb.is_configured()),
            )
            if configured
        )
        st.info(f"{sought} has no profile for **{html.escape(name)}**.")
        return

    if len(panels) == 1:
        # Unpacked explicitly: ``panels`` holds (source, profile) while this
        # renderer takes (profile, source), and ``_render_profile(*panels[0])``
        # handed it the source name as the profile -- a crash on the commonest
        # one-key setup, which the two-source tab tests could never catch.
        source, profile = panels[0]
        _render_profile(profile, source)
        return

    for tab, (source, profile) in zip(st.tabs([source for source, _ in panels]), panels):
        with tab:
            _render_profile(profile, source)
