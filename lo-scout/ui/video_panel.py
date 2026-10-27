"""
Clip panel: a modal listing Eporner and RedTube results for one performer.

The player is a plain iframe around each source's own embed URL, so no video
bytes pass through this app and no player library is bundled.
"""

import html

import streamlit as st
import streamlit.components.v1 as components

from scraper.videos import Video, format_views, search_all


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


@st.dialog("Clips", width="large")
def show_clips(name: str, limit: int = 8) -> None:
    """Open the clip panel for ``name``. Call only from a button click."""
    videos = search_all(name, limit=limit)

    if not videos:
        st.info(
            f"No clips found for {name}. The tube APIs may be rate-limiting; "
            "try again in a minute."
        )
        return

    selected_key = f"clip_index::{name}"
    index = st.session_state.get(selected_key, 0)
    if not isinstance(index, int) or not 0 <= index < len(videos):
        index = 0
    selected = videos[index]

    player = render_player(selected)
    if player:
        components.html(player, height=370)
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

    cols = st.columns(4)
    for position, video in enumerate(videos):
        with cols[position % 4]:
            thumb = render_thumb_link(video)
            if thumb:
                st.markdown(thumb, unsafe_allow_html=True)
            st.caption(f"{video.source} · {video.duration or '—'}")
            if st.button(
                "Playing" if position == index else "▶ Play",
                key=f"clip_play::{name}::{video.id}",
                use_container_width=True,
                disabled=position == index,
            ):
                st.session_state[selected_key] = position
                st.rerun()
