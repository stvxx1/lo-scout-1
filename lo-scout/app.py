"""
LO-SCOUT TITAN V22 - Main Application
Professional performer discovery tool with advanced filtering.
"""

import streamlit as st
import sys
import os

# Add the lo-scout directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import storage
from config import (
    EXTERNAL_SITES,
    ITEMS_PER_PAGE,
    SCRAPER_TIMEOUT,
    SCRAPER_MAX_RETRIES,
    SCRAPER_RETRY_DELAY,
    ENABLE_MANUAL_PASTE_MODE,
    APP_TITLE,
    APP_ICON,
    APP_DESCRIPTION
)
from scraper.freeones import FreeonesScraper
from scraper.base import ScraperError
from scraper import porndb
from models.filters import FilterConfig
from ui.theme import get_css
from ui.profile_panel import is_configured as profiles_configured
from ui.profile_panel import show_profile
from ui.similar_panel import show_similar
from ui.video_panel import show_clips
from ui.components import (
    render_filter_sidebar,
    render_performer_card,
    render_loading_spinner,
    render_status_message,
    render_filter_summary,
    render_search_sort_bar
)

# ===== CACHED DATA FETCHING =====
@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_performers(page, gender, min_height, max_height, min_weight, max_weight, min_dick, max_dick,
                          min_age, max_age, ethnicity, tattoos, piercings):
    """Cached wrapper for fetching performers."""
    scraper = FreeonesScraper(
        timeout=SCRAPER_TIMEOUT,
        max_retries=SCRAPER_MAX_RETRIES,
        retry_delay=SCRAPER_RETRY_DELAY
    )
    
    filters = FilterConfig(
        gender=gender,
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
    
    return scraper.fetch_performers(page=page, filters=filters)


# ===== PAGE CONFIGURATION =====
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== APPLY THEME =====
st.markdown(get_css(), unsafe_allow_html=True)

# ===== INITIALIZE SESSION STATE =====
if 'performers' not in st.session_state:
    st.session_state.performers = []
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'all_performers_loaded' not in st.session_state:
    st.session_state.all_performers_loaded = False
if 'is_loading' not in st.session_state:
    st.session_state.is_loading = False
if 'last_filters' not in st.session_state:
    st.session_state.last_filters = None
if 'error_message' not in st.session_state:
    st.session_state.error_message = None


def load_more_performers(filters: FilterConfig) -> bool:
    """
    Load the next page of performers.
    
    Args:
        filters: Current filter configuration
    
    Returns:
        True if performers were loaded successfully
    """
    if st.session_state.all_performers_loaded:
        return False
    
    st.session_state.is_loading = True
    st.session_state.error_message = None
    
    try:
        # Do not advance the counter yet: a failed page must stay retryable and a
        # page that yields nothing new must end the list instead of looping forever.
        page = st.session_state.current_page + 1

        # Call cached fetcher
        new_performers = get_cached_performers(
            page,
            filters.gender, filters.min_height, filters.max_height,
            filters.min_weight, filters.max_weight,
            filters.min_dick_length, filters.max_dick_length,
            filters.min_age, filters.max_age,
            filters.ethnicity, filters.tattoos, filters.piercings
        )

        # The listing carries a name and a portrait and nothing else -- no age,
        # height or weight at all. ThePornDB has all three, so every card gets
        # one lookup: eight in flight at a time, cached 24h per name (misses
        # included), so only a cold page waits on the network.
        porndb.enrich_stats(new_performers)

        # Add new performers to the list (avoid duplicates)
        existing_slugs = {p.slug for p in st.session_state.performers}
        added = [p for p in new_performers if p.slug not in existing_slugs]

        if not added:
            # Empty page, or a page we have already seen (e.g. the API ignored the
            # page parameter again): there is nothing more to load.
            st.session_state.all_performers_loaded = True
            st.session_state.is_loading = False
            return False

        st.session_state.performers.extend(added)
        st.session_state.current_page = page

        # Check if we got a full page (if not, we're at the end)
        if len(new_performers) < ITEMS_PER_PAGE:
            st.session_state.all_performers_loaded = True

        st.session_state.last_filters = filters
        st.session_state.is_loading = False

        return True
        
    except ScraperError as e:
        st.session_state.error_message = f"Failed to fetch performers: {str(e)}"
        st.session_state.is_loading = False
        return False
    except Exception as e:
        st.session_state.error_message = f"Unexpected error: {str(e)}"
        st.session_state.is_loading = False
        return False


def reset_and_load(filters: FilterConfig):
    """
    Reset state and load fresh results with new filters.
    
    Args:
        filters: New filter configuration
    """
    st.session_state.performers = []
    st.session_state.current_page = 0
    st.session_state.all_performers_loaded = False
    st.session_state.last_filters = filters
    st.session_state.error_message = None
    
    load_more_performers(filters)


def parse_manual_html(html_content: str, filters: FilterConfig) -> bool:
    """
    Parse manually pasted HTML content.
    
    Args:
        html_content: Raw HTML content pasted by user
        filters: Current filter configuration
    
    Returns:
        True if parsing was successful
    """
    st.session_state.is_loading = True
    st.session_state.error_message = None
    
    try:
        scraper = FreeonesScraper(
            timeout=SCRAPER_TIMEOUT,
            max_retries=SCRAPER_MAX_RETRIES,
            retry_delay=SCRAPER_RETRY_DELAY
        )
        
        performers = scraper.parse_performers(html_content)
        
        if not performers:
            st.session_state.error_message = "No performers found in the pasted content."
            st.session_state.is_loading = False
            return False
        
        st.session_state.performers = performers
        st.session_state.current_page = 1
        st.session_state.all_performers_loaded = True  # Can't paginate manual paste
        st.session_state.last_filters = filters
        st.session_state.is_loading = False
        
        return True
        
    except Exception as e:
        st.session_state.error_message = f"Failed to parse HTML: {str(e)}"
        st.session_state.is_loading = False
        return False


# ===== MAIN APPLICATION =====
def main():
    """Main application entry point."""
    
    # Render title
    st.markdown(f'<h1 class="main-title">{APP_ICON} {APP_TITLE}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="subtitle">{APP_DESCRIPTION}</p>', unsafe_allow_html=True)
    
    # Render filter sidebar
    filters = render_filter_sidebar()

    # Favourites live in sqlite rather than in the scrape results, so they can be
    # browsed before the first scan and survive filter changes.
    favourites_only = st.session_state.get("filter_favorites_only", False)
    favourites = storage.list_favorites() if favourites_only else []
    
    # Render manual paste mode in sidebar
    if ENABLE_MANUAL_PASTE_MODE:
        with st.sidebar:
            st.markdown("---")
            with st.expander("📋 Manual Paste Mode"):
                st.info("Right-click the site → View Page Source → Ctrl+A → Ctrl+C. Paste below.")
                raw_html = st.text_area(
                    "Paste HTML Source Code",
                    height=150,
                    placeholder="Paste HTML here...",
                    key="manual_html"
                )
                
                if st.button("🏗️ Extract from Paste", use_container_width=True, key="parse_manual"):
                    if raw_html:
                        parse_manual_html(raw_html, filters)
                    else:
                        st.warning("Please paste some HTML content first.")
    
    # ===== MAIN CONTENT AREA =====
    
    # Display error message if any
    if st.session_state.error_message:
        st.markdown(render_status_message(st.session_state.error_message, "error"), unsafe_allow_html=True)
    
    # Display filter summary if filters are active
    if st.session_state.last_filters and st.session_state.last_filters.has_filters():
        st.markdown(render_filter_summary(st.session_state.last_filters), unsafe_allow_html=True)

    # The sidebar is live: without this, a changed filter has no effect until the
    # results are reset, and Load More would append a page fetched with the new
    # filters onto a list built with the old ones.
    if st.session_state.last_filters is not None and st.session_state.last_filters != filters:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔄 APPLY FILTERS", use_container_width=True, type="primary", key="apply_filters"):
                reset_and_load(filters)
                st.rerun()
    
    # Loading state
    if st.session_state.is_loading:
        st.markdown(render_loading_spinner("Scanning performers and their stats..."), unsafe_allow_html=True)
        st.stop()
    
    # No results yet - either nothing was scanned yet, or the scan came back empty
    if not st.session_state.performers and not favourites:
        if favourites_only:
            st.markdown(
                render_status_message(
                    "No favourites saved yet — tap ☆ Save under any performer.", "info"
                ),
                unsafe_allow_html=True,
            )
            st.stop()

        scanned = st.session_state.last_filters is not None
        if scanned and st.session_state.error_message is None:
            st.markdown(
                render_status_message(
                    "No performers match these filters. Try widening the ranges.", "error"
                ),
                unsafe_allow_html=True,
            )

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            label = "🔁 SCAN AGAIN" if scanned else "🚀 RUN AUTO-SCAN"
            if st.button(label, use_container_width=True, type="primary"):
                reset_and_load(filters)
                st.rerun()

        st.markdown("""
        <div style="text-align: center; margin-top: 40px; color: var(--text-muted);">
            <p>Click the button above to start scanning performers from Freeones.com</p>
            <p style="font-size: 0.85rem; margin-top: 10px;">
                Use the sidebar filters to narrow your search by gender, height, weight, and more.
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.stop()
    
    # Search and Sort Bar
    search_query, sort_option = render_search_sort_bar()
    
    # Filter and Sort Logic. In favourites mode the list comes from the store, so
    # it can be searched and sorted without a scan.
    display_performers = list(favourites if favourites_only else st.session_state.performers)
    
    # Apply search filter
    if search_query:
        display_performers = [p for p in display_performers if search_query.lower() in p.name.lower()]
    
    # Apply sorting
    if sort_option == "Name (A-Z)":
        display_performers.sort(key=lambda x: x.name)
    elif sort_option == "Name (Z-A)":
        display_performers.sort(key=lambda x: x.name, reverse=True)
    elif sort_option == "Height (Tallest)":
        display_performers.sort(key=lambda x: x.height or 0, reverse=True)
    elif sort_option == "Height (Shortest)":
        display_performers.sort(key=lambda x: x.height or 999)
    
    # Display results count
    total_found = len(display_performers)
    st.markdown(
        render_status_message(f"✨ Found <b>{total_found}</b> performers matching your search", "success"),
        unsafe_allow_html=True
    )
    
    # Render performer grid
    if display_performers:
        # One query for the whole grid instead of one per card.
        saved_slugs = storage.favorite_slugs()

        # Use Streamlit columns for the grid layout
        grid_cols = st.columns(4)
        
        for idx, performer in enumerate(display_performers):
            with grid_cols[idx % 4]:
                # Render each performer card
                card_html = render_performer_card(performer, EXTERNAL_SITES)
                st.markdown(card_html, unsafe_allow_html=True)

                is_saved = performer.slug in saved_slugs
                # Two actions per card: keep her, or go looking for clips.
                save_col, clips_col = st.columns(2)
                with save_col:
                    if st.button(
                        "⭐ Saved" if is_saved else "☆ Save",
                        key=f"fav_{performer.slug}",
                        use_container_width=True,
                        help="Add or remove this performer from your favourites",
                    ):
                        storage.toggle_favorite(performer)
                        st.rerun()
                with clips_col:
                    if st.button(
                        "🎬 Clips",
                        key=f"clips_{performer.slug}",
                        use_container_width=True,
                        help=f"Find clips of {performer.name} on Eporner, RedTube and XVideos",
                    ):
                        show_clips(performer.name)

                # Profile needs any keyed source; Similar needs ThePornDB, which
                # supplies the anchor height. Freeones alone has nothing to match
                # on, so that button is absent rather than useless.
                if profiles_configured():
                    if porndb.is_configured():
                        profile_col, similar_col = st.columns(2)
                    else:
                        profile_col, similar_col = st.container(), None

                    with profile_col:
                        if st.button(
                            "ℹ️ Profile",
                            key=f"profile_{performer.slug}",
                            use_container_width=True,
                            help=f"Bio, measurements and links for {performer.name}",
                        ):
                            show_profile(performer.name)

                    if similar_col is not None:
                        with similar_col:
                            if st.button(
                                "🔎 Similar",
                                key=f"similar_{performer.slug}",
                                use_container_width=True,
                                help=f"Find performers in {performer.name}'s height range",
                            ):
                                show_similar(performer.name, performer.slug)
    
    # Render pagination
    if favourites_only:
        st.markdown(
            '<div style="text-align: center; color: var(--text-muted); margin: 24px 0;">'
            '⭐ Showing your saved performers. Uncheck "Favourites only" to browse the full list.'
            '</div>',
            unsafe_allow_html=True
        )
    elif not st.session_state.all_performers_loaded and not search_query:
        # Create a container for the Load More button
        load_more_col = st.columns([1, 2, 1])
        with load_more_col[1]:
            if st.button("⚡ LOAD MORE", use_container_width=True, key="load_more_btn"):
                load_more_performers(filters)
                st.rerun()
        
        # Page info
        st.markdown(
            f'<div style="text-align: center; color: var(--text-secondary); margin: 16px 0;">'
            f'Page <span style="color: var(--accent-purple-light);">{st.session_state.current_page}</span> '
            f'- Showing <span style="color: var(--accent-purple-light);">{len(st.session_state.performers)}</span> total'
            f'</div>',
            unsafe_allow_html=True
        )
    elif search_query:
        st.markdown(
            '<div style="text-align: center; color: var(--text-muted); margin: 24px 0;">'
            '<i>Search filters are applied to loaded results. Clear search to load more.</i>'
            '</div>',
            unsafe_allow_html=True
        )
    else:
        if len(st.session_state.performers) > 0:
            st.markdown(
                '<div style="text-align: center; color: var(--text-muted); margin: 24px 0;">'
                '🎉 You\'ve reached the end of available performers!'
                '</div>',
                unsafe_allow_html=True
            )


if __name__ == "__main__":
    main()