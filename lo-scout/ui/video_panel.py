"""
Clip panel: one tab per tube site, played in each site's own embed iframe.

The player is a plain iframe around each source's embed URL, so no video bytes
pass through this app and no player library is bundled. Every source is fetched
before the tabs are built (Streamlit renders all tabs eagerly), which is why
``search_by_source`` runs the requests in parallel and caches them.
"""

import html

import streamlit as st
import streamlit.components.v1 as components

from scraper.videos import Video, format_views, search_by_source


def render_player(video: Video) -> str:
    """Return the iframe markup for a clip (empty when it has no embed URL)."""
    if not video.embed_url:
        return ""
    return (
        f'<iframe src="{html.escape(video.embed_url, quote=True)}" width="100%" height="360" '
        'frameborder="0" scrolling="no" allowfullscreen '
        'referrerpolicy="no-referrer" style="border-radius: var(--radius-md);"></iframe>'
    )


def render_thumb_link(video: Video) -> str:
    """Return a clickable thumbnail that opens the clip page in a new tab."""
    if not video.thumb_url:
        return ""
    return (
        f'<a class="clip-thumb" href="{html.escape(video.page_url, quote=True)}" '
        f'target="_blank" rel="noopener noreferrer" '
        f'title="{html.escape(video.title, quote=True)}">'
        f'<img src="{html.escape(video.thumb_url, quote=True)}" alt="" loading="lazy" '
        f'decoding="async" referrerpolicy="no-referrer">'
        f"</a>"
    )


def render_watch_link(video: Video) -> str:
    """Return an outbound link, for sources that refuse to be embedded."""
    if not video.page_url:
        return ""
    return (
        f'<a class="clip-watch" href="{html.escape(video.page_url, quote=True)}" '
        f'target="_blank" rel="noopener noreferrer">'
        f"Watch on {html.escape(video.source)}</a>"
    )


def selected_clip(
    name: str, grouped: dict
) -> Video:
    """Return the clip the user last pressed play on, else the first one.

    One selection is shared by every tab and rendered above them: pressing play
    reruns the script, and Streamlit resets the open tab on every rerun, so a
    player that lived inside a tab would disappear from view.
    """
    choice = st.session_state.get(f"selected_clip::{name}") or {}
    for clips in grouped.values():
        for video in clips:
            if video.source == choice.get("source") and video.id == choice.get("id"):
                return video
    for clips in grouped.values():
        if clips:
            return clips[0]
    return None


def _render_source_tab(name: str, source: str, clips: list, selected: Video) -> None:
    if not clips:
        st.info(f"No clips found on {source}.")
        return

    cols = st.columns(4)
    for position, video in enumerate(clips):
        with cols[position % 4]:
            thumb = render_thumb_link(video)
            if thumb:
                st.markdown(thumb, unsafe_allow_html=True)
            st.caption(video.duration or "—")
            playing = selected is not None and video.id == selected.id and video.source == source
            if st.button(
                "Playing" if playing else "▶ Play",
                key=f"clip_play::{name}::{source}::{video.id}",
                use_container_width=True,
                disabled=playing,
            ):
                st.session_state[f"selected_clip::{name}"] = {
                    "source": source,
                    "id": video.id,
                }
                st.rerun()


@st.dialog("Clips", width="large")
def show_clips(name: str, limit: int = 8) -> None:
    """Open the clip panel for ``name``. Call only from a button click."""
    grouped = search_by_source(name, limit=limit)

    if not any(grouped.values()):
        st.info(
            f"No clips found for {name}. The tube APIs may be rate-limiting; "
            "try again in a minute."
        )
        return

    selected = selected_clip(name, grouped)
    player = render_player(selected)
    watch_link = "" if player else render_watch_link(selected)
    if player:
        components.html(player, height=370)
    elif watch_link:
        st.markdown(watch_link, unsafe_allow_html=True)
    st.markdown(f"**{html.escape(selected.title)}**")
    st.caption(
        " · ".join(
            part
            for part in (
                selected.source,
                selected.duration,
                format_views(selected.views),
            )
            if part
        )
    )

    st.markdown("---")

    tabs = st.tabs(list(grouped))
    for tab, source in zip(tabs, grouped):
        with tab:
            _render_source_tab(name, source, grouped[source], selected)

