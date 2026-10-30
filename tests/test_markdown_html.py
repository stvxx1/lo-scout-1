"""HTML handed to ``st.markdown`` has to survive CommonMark parsing.

Streamlit renders *markdown*, and markdown only tolerates raw HTML in blocks it
does not otherwise interpret. A raw-HTML block ends at the first blank line, so
a multi-line, indented card template that left a whitespace-only line behind
(an empty info overlay, the gaps between link icons) lost everything after the
portrait: the performer's name and all four site links vanished, silently, with
no exception anywhere. The card still rendered, which is what made it hard to
see.

These tests fail on the string, not on a browser, because the string is what
actually diverged. The one-line card is deliberate; see
``render_performer_card``.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lo-scout"))

from config import EXTERNAL_SITES                              # noqa: E402
from models.filters import FilterConfig                        # noqa: E402
from models.performer import Performer                         # noqa: E402
from ui.components import (                                    # noqa: E402
    render_filter_summary,
    render_loading_spinner,
    render_performer_card,
    render_status_message,
)
from ui.profile_panel import profile_html                      # noqa: E402
from ui.similar_panel import result_html                       # noqa: E402
from ui.video_panel import (                                   # noqa: E402
    Video,
    render_player,
    render_thumb_link,
    render_watch_link,
)

VIDEO = Video(
    source="Eporner",
    id="abc123",
    title="A title",
    page_url="https://www.eporner.com/video-abc123/a-title/",
    embed_url="https://www.eporner.com/embed/abc123",
    thumb_url="https://cdn.example/thumb.jpg",
    duration="12:34",
    views=1500,
)

PROFILE = {
    "name": "Sara Jay",
    "source": "Freeones",
    "image_url": "https://cdn.example/sara.jpg",
    "url": "https://www.freeones.com/sara-jay",
    "rating": 4.25,
    "bio": "Bio text.",
    "aliases": ["Sara"],
    "extras": {"height": 163, "birthday": "1977-11-14", "measurements": "34DD"},
}

# Every builder whose output reaches st.markdown(..., unsafe_allow_html=True).
BUILDERS = {
    "card": lambda: render_performer_card(
        Performer(name="Sara Jay", slug="sara-jay", image_url=""), EXTERNAL_SITES
    ),
    "card with image and stats": lambda: render_performer_card(
        Performer(
            name="Sara Jay",
            slug="sara-jay",
            image_url="https://cdn.example/sara.jpg",
            age=48,
        ),
        EXTERNAL_SITES,
    ),
    "status message": lambda: render_status_message("Done", "success"),
    "filter summary": lambda: render_filter_summary(
        FilterConfig(gender="babes", min_height=150, max_height=180)
    ),
    "loading spinner": lambda: render_loading_spinner("Scanning performers..."),
    "profile": lambda: profile_html(PROFILE, "Freeones"),
    "similar performer": lambda: result_html(
        Performer(name="Sara Jay", slug="sara-jay", image_url="https://x/y.jpg")
    ),
    "clip player": lambda: render_player(VIDEO),
    "clip thumbnail": lambda: render_thumb_link(VIDEO),
    "clip watch link": lambda: render_watch_link(VIDEO),
}


def interior_blank_lines(html: str):
    """Return the numbers of blank lines *inside* an HTML block.

    Leading and trailing blank lines are harmless -- the block simply starts
    later or ends earlier. A blank line between the first and last non-blank
    line is the dangerous one: it terminates the HTML block.
    """
    lines = html.split("\n")
    filled = [n for n, line in enumerate(lines, 1) if line.strip()]
    if not filled:
        return []
    return [
        n
        for n in range(filled[0] + 1, filled[-1])
        if not lines[n - 1].strip()
    ]


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_no_blank_line_can_cut_the_html_block(name):
    assert interior_blank_lines(BUILDERS[name]()) == []


def test_the_check_notices_the_template_that_caused_this():
    """Guard the guard: the old multi-line template must be flagged."""
    old = (
        '\n    <div class="performer-card">\n        <div class="img-box">\n'
        '            <img src="x">\n            \n        </div>\n'
        '        <p class="performer-name">Sara Jay</p>\n    </div>\n    '
    )

    assert interior_blank_lines(old) == [5]


def test_card_is_a_single_html_block():
    """The regression itself: one line, no indentation, nothing to cut it."""
    html = render_performer_card(
        Performer(name="Sara Jay", slug="sara-jay", image_url=""), EXTERNAL_SITES
    )

    assert "\n" not in html
    assert html.startswith('<div class="performer-card">')
    assert html.endswith("</div>")


def test_card_keeps_the_name_and_links_after_the_portrait():
    """Both losses were downstream of the image box, so assert the order too."""
    html = render_performer_card(
        Performer(name="Sara Jay", slug="sara-jay", image_url=""), EXTERNAL_SITES
    )

    portrait = html.index('class="img-box"')
    name = html.index('class="performer-name"')
    links = html.index('class="external-links"')

    assert portrait < name < links
    assert ">Sara Jay</p>" in html
    assert html.count('class="tube-link') == len(EXTERNAL_SITES)
