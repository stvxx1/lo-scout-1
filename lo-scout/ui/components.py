"""
UI components module for lo-scout application.
Provides reusable UI components for the Streamlit interface.
"""

from typing import List, Dict, Any, Optional
import html
import json

import streamlit as st

import storage
from config import (
    ETHNICITY_OPTIONS,
    MAX_AGE_DEFAULT,
    MIN_AGE_DEFAULT,
    PIERCING_OPTIONS,
    TATTOO_OPTIONS,
)
from models.performer import Performer
from models.filters import FilterConfig
from thumbnails import portrait_html


# Sentinel for the "no preference" entry of a single-choice facet widget. A
# widget value has to be hashable and serialisable, and a string keeps None free
# to mean "this filter is off" everywhere downstream.
ANY_OPTION = "any"


def _ordered_range(low: Optional[int], high: Optional[int]) -> tuple:
    """Return (low, high, was_swapped) with the pair sorted ascending."""
    if low is not None and high is not None and low > high:
        return high, low, True
    return low, high, False


def _clear_filters() -> None:
    """Reset every filter widget.

    Runs as a widget callback, i.e. before the rerun starts, so Streamlit can
    rebuild the widgets with their defaults instead of re-instantiating widgets
    that were already created during the current run.
    """
    for key in list(st.session_state.keys()):
        if key.startswith("filter_"):
            del st.session_state[key]


def render_filter_sidebar() -> FilterConfig:
    """
    Render the filter sidebar with all filter controls.
    
    Returns:
        FilterConfig object with selected filter values
    """
    with st.sidebar:
        st.title("🔮 LO-SCOUT")
        st.markdown("---")
        
        # Gender filter
        gender_options = {
            "babes": "👩 Babes",
            "males": "👨 Males"
        }
        gender_label = st.selectbox(
            "Gender",
            options=list(gender_options.keys()),
            format_func=lambda x: gender_options[x],
            index=0,
            key="filter_gender"
        )
        
        st.markdown("---")
        
        # Age filter. A slider only: the full extent is what "no filter" means, so
        # typing 18 and 99 by hand would be noise. Freeones' own floor is 18.
        st.subheader("🎂 Age (years)")
        age_range = st.slider(
            "Age Range (years)",
            min_value=MIN_AGE_DEFAULT,
            max_value=MAX_AGE_DEFAULT,
            value=(MIN_AGE_DEFAULT, MAX_AGE_DEFAULT),
            key="filter_age_range"
        )
        min_age = age_range[0] if age_range[0] > MIN_AGE_DEFAULT else None
        max_age = age_range[1] if age_range[1] < MAX_AGE_DEFAULT else None

        st.markdown("---")

        # Height filter
        st.subheader("📏 Height (cm)")
        col1, col2 = st.columns(2)
        with col1:
            min_height = st.number_input(
                "Min",
                min_value=0,
                max_value=300,
                value=None,
                placeholder="Min",
                key="filter_min_height"
            )
        with col2:
            max_height = st.number_input(
                "Max",
                min_value=0,
                max_value=300,
                value=None,
                placeholder="Max",
                key="filter_max_height"
            )
        
        # Height range slider
        if st.checkbox("Use height range slider", value=False, key="filter_height_slider_toggle"):
            height_range = st.slider(
                "Height Range (cm)",
                min_value=0,
                max_value=300,
                value=(0, 300),
                key="filter_height_range"
            )
            min_height = height_range[0] if height_range[0] > 0 else None
            max_height = height_range[1] if height_range[1] < 300 else None

        st.caption(
            "ℹ️ Height and weight are filtered by Freeones itself. The cards show "
            "age, height and weight when ThePornDB has them."
        )
        
        st.markdown("---")
        
        # Weight filter
        st.subheader("⚖️ Weight (kg)")
        col3, col4 = st.columns(2)
        with col3:
            min_weight = st.number_input(
                "Min",
                min_value=0,
                max_value=500,
                value=None,
                placeholder="Min",
                key="filter_min_weight"
            )
        with col4:
            max_weight = st.number_input(
                "Max",
                min_value=0,
                max_value=500,
                value=None,
                placeholder="Max",
                key="filter_max_weight"
            )
        
        # Weight range slider
        if st.checkbox("Use weight range slider", value=False, key="filter_weight_slider_toggle"):
            weight_range = st.slider(
                "Weight Range (kg)",
                min_value=0,
                max_value=500,
                value=(0, 500),
                key="filter_weight_range"
            )
            min_weight = weight_range[0] if weight_range[0] > 0 else None
            max_weight = weight_range[1] if weight_range[1] < 500 else None
        
        st.markdown("---")
        
        # Dick length filter (males only)
        if gender_label == "males":
            st.subheader("📐 Length (cm)")
            col5, col6 = st.columns(2)
            with col5:
                min_dick = st.number_input(
                    "Min",
                    min_value=0,
                    max_value=50,
                    value=None,
                    placeholder="Min",
                    key="filter_min_dick_length"
                )
            with col6:
                max_dick = st.number_input(
                    "Max",
                    min_value=0,
                    max_value=50,
                    value=None,
                    placeholder="Max",
                    key="filter_max_dick_length"
                )
            
            # Length range slider
            if st.checkbox("Use length range slider", value=False, key="filter_dick_slider_toggle"):
                dick_range = st.slider(
                    "Length Range (cm)",
                    min_value=0,
                    max_value=50,
                    value=(0, 50),
                    key="filter_dick_range"
                )
                min_dick = dick_range[0] if dick_range[0] > 0 else None
                max_dick = dick_range[1] if dick_range[1] < 50 else None
        else:
            min_dick = None
            max_dick = None
        
        st.markdown("---")
        
        # Look filters. Single-choice on purpose: freeones reads a comma list as
        # one unknown value (empty page) and keeps only the last of a repeated
        # key, so a multiselect would promise more than the URL can carry -- see
        # SELECT_FACETS in models/filters.py.
        st.subheader("🌍 Ethnicity")
        ethnicity_choice = st.selectbox(
            "Ethnicity",
            options=[ANY_OPTION] + list(ETHNICITY_OPTIONS),
            format_func=lambda value: "Any" if value == ANY_OPTION else ETHNICITY_OPTIONS[value],
            index=0,
            key="filter_ethnicity"
        )

        st.subheader("🎨 Body art")
        tattoos_choice = st.selectbox(
            "Tattoos",
            options=[ANY_OPTION] + list(TATTOO_OPTIONS),
            format_func=lambda value: "Any" if value == ANY_OPTION else TATTOO_OPTIONS[value],
            index=0,
            key="filter_tattoos"
        )
        piercings_choice = st.selectbox(
            "Piercings",
            options=[ANY_OPTION] + list(PIERCING_OPTIONS),
            format_func=lambda value: "Any" if value == ANY_OPTION else PIERCING_OPTIONS[value],
            index=0,
            key="filter_piercings"
        )

        ethnicity = None if ethnicity_choice == ANY_OPTION else ethnicity_choice
        tattoos = None if tattoos_choice == ANY_OPTION else tattoos_choice
        piercings = None if piercings_choice == ANY_OPTION else piercings_choice

        st.markdown("---")

        # Clear filters button
        st.button(
            "🗑️ Clear Filters",
            use_container_width=True,
            key="clear_filters",
            on_click=_clear_filters
        )

        # ===== FAVOURITES =====
        st.markdown("---")
        st.checkbox("⭐ Favourites only", value=False, key="filter_favorites_only")

        favourites = storage.list_favorites()
        if favourites:
            st.download_button(
                f"⬇️ Export {len(favourites)} favourite{'s' if len(favourites) != 1 else ''}",
                data=json.dumps(storage.export_favorites(), indent=2),
                file_name="lo-scout-favourites.json",
                mime="application/json",
                use_container_width=True,
                key="export_favorites",
            )

        uploaded = st.file_uploader(
            "Import favourites (.json)", type=["json"], key="import_favorites_file"
        )
        if uploaded is not None:
            # A re-run keeps the file in the widget, so import once per upload
            # instead of on every interaction.
            marker = f"{uploaded.name}:{uploaded.size}"
            if st.session_state.get("import_favorites_marker") != marker:
                st.session_state["import_favorites_marker"] = marker
                try:
                    payload = json.loads(uploaded.getvalue().decode("utf-8"))
                    if not isinstance(payload, list):
                        raise ValueError("expected a list of performers")
                    added = storage.import_favorites(payload)
                    st.success(f"Imported {added} new favourite{'s' if added != 1 else ''}.")
                except (ValueError, UnicodeDecodeError):
                    st.error("That file is not a LO-SCOUT favourites export.")
        
        # Freeones rejects inverted ranges and FilterConfig raises on them, which
        # would kill the whole app, so swap them and tell the user instead.
        min_height, max_height, swapped_height = _ordered_range(min_height, max_height)
        min_weight, max_weight, swapped_weight = _ordered_range(min_weight, max_weight)
        min_dick, max_dick, swapped_length = _ordered_range(min_dick, max_dick)
        if swapped_height or swapped_weight or swapped_length:
            st.warning("Minimum was greater than maximum — the range was swapped.")

        # Build FilterConfig
        filter_config = FilterConfig(
            gender=gender_label,
            min_height=min_height,
            max_height=max_height,
            min_weight=min_weight,
            max_weight=max_weight,
            min_dick_length=min_dick,
            max_dick_length=max_dick,
            min_age=min_age,
            max_age=max_age,
            ethnicity=ethnicity,
            tattoos=tattoos,
            piercings=piercings
        )
        
        return filter_config


def render_performer_card(performer: Performer, external_sites: List[Dict[str, Any]]) -> str:
    """
    Render a single performer card with external site links and info overlay.
    
    Args:
        performer: Performer object
        external_sites: List of external site configurations
    
    Returns:
        HTML string for the performer card
    """
    # Generate external search URLs
    search_urls = performer.get_external_search_urls(external_sites)
    
    # Image: escaped, with an initials tile behind it, so a failed load
    # degrades instead of showing a broken-image icon.
    img_html = portrait_html(performer.name, performer.image_url)
    
    # Build Info Overlay. Values come from the scraped page, so they are
    # escaped: an unescaped quote or ampersand breaks the surrounding markup.
    info_items = []
    if performer.age:
        info_items.append(f'<div class="info-item"><span class="info-label">Age:</span> <span>{performer.age}</span></div>')
    for label, value, suffix in (
        ("Ethnicity", performer.ethnicity, ""),
        ("Stats", performer.measurements, ""),
        ("Height", performer.height, "cm"),
        ("Weight", performer.weight, "kg"),
        ("Hair", performer.hair_color, ""),
    ):
        if value:
            info_items.append(
                f'<div class="info-item"><span class="info-label">{label}:</span> '
                f'<span>{html.escape(str(value))}{suffix}</span></div>'
            )
    
    info_overlay = f'<div class="info-overlay">{"".join(info_items)}</div>' if info_items else ""
    
    # At-a-glance stats. Freeones' listing carries none of this, so the values
    # are whatever ThePornDB filled in -- any subset, and often nothing at all
    # when no key is configured. Ints only, so nothing here needs escaping.
    stats = []
    if performer.age:
        stats.append(f"{performer.age}")
    if performer.height:
        stats.append(f"{performer.height} cm")
    if performer.weight:
        stats.append(f"{performer.weight} kg")
    stats_text = " · ".join(stats)
    stats_html = f'<p class="performer-stats">{stats_text}</p>' if stats_text else ""
    
    # Build external link buttons
    site_class_map = {
        "XVideos": "xvideos",
        "Eporner": "eporner",
        "Sxyprn": "sxyprn",
        "Xmoviesforyou": "xmovies"
    }
    
    links_html = ""
    for site in external_sites:
        site_name = site["name"]
        site_icon = site["icon"]
        site_class = site_class_map.get(site_name, "")
        url = search_urls.get(site_name, "#")
        
        safe_url = html.escape(url, quote=True)
        safe_site = html.escape(site_name, quote=True)
        links_html += (
            f'<a class="tube-link {site_class}" href="{safe_url}" target="_blank" '
            f'rel="noopener noreferrer" title="Search {safe_site}">{site_icon}</a>'
        )
    
    # Build card HTML. The name lands in both an attribute and a text node,
    # so it is escaped for each; unescaped quotes silently kill the <img>.
    #
    # One line on purpose, like links_html above: st.markdown parses this as
    # CommonMark, and a raw-HTML block ends at the first blank line. An
    # indented multi-line template used to leave whitespace-only lines behind
    # (an empty info_overlay, the gaps between link icons), which silently cut
    # everything after the portrait -- the name and every link vanished while
    # the card still rendered. Keep this string free of blank lines and of
    # lines indented four or more spaces, or the same truncation comes back.
    safe_name = html.escape(performer.name, quote=True)
    card_html = (
        f'<div class="performer-card">'
        f'<div class="img-box">{img_html}{info_overlay}</div>'
        f'<p class="performer-name" title="{safe_name}">{safe_name}</p>'
        f'{stats_html}'
        f'<div class="external-links" style="margin-top: auto;">{links_html}</div>'
        f"</div>"
    )
    
    return card_html


def render_search_sort_bar():
    """
    Render search and sort controls in the main content area.
    
    Returns:
        Tuple of (search_query, sort_option)
    """
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input(
            "🔍 Search performers...",
            placeholder="Type a name to filter results...",
            label_visibility="collapsed",
            key="search_input"
        )
    with col2:
        sort_option = st.selectbox(
            "Sort by",
            options=["Default", "Name (A-Z)", "Name (Z-A)", "Height (Tallest)", "Height (Shortest)"],
            label_visibility="collapsed",
            key="sort_selectbox"
        )
    return search_query, sort_option


def render_loading_spinner(message: str = "Scanning performers...") -> str:
    """
    Render a loading spinner with message.
    
    Args:
        message: Loading message to display
    
    Returns:
        HTML string for loading spinner
    """
    return f'''
    <div class="loading-container">
        <div class="loading-spinner"></div>
        <div class="loading-text">
            <span>{message}</span>
        </div>
    </div>
    '''


def render_status_message(message: str, status_type: str = "info") -> str:
    """
    Render a status message.
    
    Args:
        message: Message to display
        status_type: Type of status (success, error, info)
    
    Returns:
        HTML string for status message
    """
    return f'<div class="status-message status-{status_type}">{message}</div>'


def render_filter_summary(filters: FilterConfig) -> str:
    """
    Render a summary of active filters.
    
    Args:
        filters: Active FilterConfig
    
    Returns:
        HTML string for filter summary
    """
    if not filters.has_filters():
        return ""
    
    badges = []
    
    # Gender badge
    gender_label = "👩 Babes" if filters.gender == "babes" else "👨 Males"
    badges.append(f'<span class="filter-badge"><span class="badge-label">Gender:</span> {gender_label}</span>')
    
    # Height badge
    if filters.min_height is not None or filters.max_height is not None:
        height_str = ""
        if filters.min_height is not None:
            height_str += f">={filters.min_height}cm"
        if filters.max_height is not None:
            if height_str:
                height_str += " "
            height_str += f"<={filters.max_height}cm"
        badges.append(f'<span class="filter-badge"><span class="badge-label">Height:</span> {height_str}</span>')
    
    # Weight badge
    if filters.min_weight is not None or filters.max_weight is not None:
        weight_str = ""
        if filters.min_weight is not None:
            weight_str += f">={filters.min_weight}kg"
        if filters.max_weight is not None:
            if weight_str:
                weight_str += " "
            weight_str += f"<={filters.max_weight}kg"
        badges.append(f'<span class="filter-badge"><span class="badge-label">Weight:</span> {weight_str}</span>')
    
    # Dick length badge (males only)
    if filters.gender == "males" and (filters.min_dick_length is not None or filters.max_dick_length is not None):
        length_str = ""
        if filters.min_dick_length is not None:
            length_str += f">={filters.min_dick_length}cm"
        if filters.max_dick_length is not None:
            if length_str:
                length_str += " "
            length_str += f"<={filters.max_dick_length}cm"
        badges.append(f'<span class="filter-badge"><span class="badge-label">Length:</span> {length_str}</span>')

    # Age badge
    if filters.min_age is not None or filters.max_age is not None:
        age_str = ""
        if filters.min_age is not None:
            age_str += f">={filters.min_age}y"
        if filters.max_age is not None:
            if age_str:
                age_str += " "
            age_str += f"<={filters.max_age}y"
        badges.append(f'<span class="filter-badge"><span class="badge-label">Age:</span> {age_str}</span>')

    # Single-choice badges. FilterConfig has already validated the slug, so the
    # label lookup cannot miss.
    for label, value, options in (
        ("Ethnicity", filters.ethnicity, ETHNICITY_OPTIONS),
        ("Tattoos", filters.tattoos, TATTOO_OPTIONS),
        ("Piercings", filters.piercings, PIERCING_OPTIONS),
    ):
        if value is not None:
            badges.append(
                f'<span class="filter-badge"><span class="badge-label">{label}:</span> {options[value]}</span>'
            )
    
    return f'<div style="margin-bottom: 16px;">{"".join(badges)}</div>'