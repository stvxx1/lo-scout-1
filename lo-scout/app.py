import sys, os; sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import sys, os; sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import sys, os; sys.path.append(os.getcwd())
"""
LO-SCOUT TITAN V22 - Main Application
Professional performer discovery tool with advanced filtering.
"""

import streamlit as st
import sys
import os

# Add the lo-scout directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    EXTERNAL_SITES,
    ITEMS_PER_PAGE,
    SCRAPER_TIMEOUT,
    SCRAPER_MAX_RETRIES,
    SCRAPER_RETRY_DELAY,
    ENABLE_MANUAL_PASTE_MODE,
    ENABLE_CACHE,
    APP_TITLE,
    APP_ICON,
    APP_DESCRIPTION
)
from scraper.freeones import FreeonesScraper
from scraper.base import ScraperError
from models.performer import Performer
from models.filters import FilterConfig
from ui.theme import get_css
from ui.components import (
    render_filter_sidebar,
    render_performer_card,
    render_performer_grid,
    render_pagination,
    render_loading_spinner,
    render_status_message,
    render_filter_summary
)

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
        # Create scraper with configured settings
        scraper = FreeonesScraper(
            timeout=SCRAPER_TIMEOUT,
            max_retries=SCRAPER_MAX_RETRIES,
            retry_delay=SCRAPER_RETRY_DELAY
        )
        
        # Increment page and fetch performers
        st.session_state.current_page += 1
        page = st.session_state.current_page
        
        new_performers = scraper.fetch_performers(page=page, filters=filters)
        
        if not new_performers:
            st.session_state.all_performers_loaded = True
            st.session_state.is_loading = False
            return False
        
        # Add new performers to the list
        st.session_state.performers.extend(new_performers)
        
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
    
    # Loading state
    if st.session_state.is_loading:
        st.markdown(render_loading_spinner("Scanning performers..."), unsafe_allow_html=True)
        st.stop()
    
    # No results yet - show scan button
    if not st.session_state.performers:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 RUN AUTO-SCAN", use_container_width=True, type="primary"):
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
    
    # Display results count
    total_performers = len(st.session_state.performers)
    st.markdown(
        render_status_message(f"✨ Found <b>{total_performers}</b> performers", "success"),
        unsafe_allow_html=True
    )
    
    # Render performer grid
    if st.session_state.performers:
        # Use Streamlit columns for the grid layout
        cols = st.columns(4)
        
        for idx, performer in enumerate(st.session_state.performers):
            with cols[idx % 4]:
                # Render each performer card
                card_html = render_performer_card(performer, EXTERNAL_SITES)
                st.markdown(card_html, unsafe_allow_html=True)
    
    # Render pagination
    if not st.session_state.all_performers_loaded:
        pagination_html = render_pagination(
            current_page=st.session_state.current_page,
            total_performers=total_performers,
            items_per_page=ITEMS_PER_PAGE
        )
        
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
            f'- Showing <span style="color: var(--accent-purple-light);">{total_performers}</span> performers'
            f'</div>',
            unsafe_allow_html=True
        )
    else:
        if total_performers > 0:
            st.markdown(
                '<div style="text-align: center; color: var(--text-muted); margin: 24px 0;">'
                '🎉 You\'ve reached the end of available performers!'
                '</div>',
                unsafe_allow_html=True
            )


if __name__ == "__main__":
    main()