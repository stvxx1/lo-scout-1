"""
UI components module for lo-scout application.
Provides reusable UI components for the Streamlit interface.
"""

from typing import List, Dict, Any, Optional
import streamlit as st

from ..models.performer import Performer
from ..models.filters import FilterConfig


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
        
        # Clear filters button
        if st.button("🗑️ Clear Filters", use_container_width=True, key="clear_filters"):
            # Reset all filter values
            for key in st.session_state.keys():
                if key.startswith("filter_"):
                    st.session_state[key] = None
            
            # Reset gender to default
            st.session_state.filter_gender = "babes"
            gender_label = "babes"
            min_height = max_height = min_weight = max_weight = None
            min_dick = max_dick = None
        
        # Build FilterConfig
        filter_config = FilterConfig(
            gender=gender_label,
            min_height=min_height,
            max_height=max_height,
            min_weight=min_weight,
            max_weight=max_weight,
            min_dick_length=min_dick,
            max_dick_length=max_dick
        )
        
        return filter_config


def render_performer_card(performer: Performer, external_sites: List[Dict[str, Any]]) -> str:
    """
    Render a single performer card with external site links.
    
    Args:
        performer: Performer object
        external_sites: List of external site configurations
    
    Returns:
        HTML string for the performer card
    """
    # Generate external search URLs
    search_urls = performer.get_external_search_urls(external_sites)
    
    # Build image HTML
    if performer.has_image:
        img_html = f'<img src="{performer.image_url}" alt="{performer.name}" loading="lazy">'
    else:
        img_html = '<div class="img-placeholder">👤</div>'
    
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
        
        links_html += f'''
        <a class="tube-link {site_class}" href="{url}" target="_blank" rel="noopener noreferrer" title="Search {site_name}">
            {site_icon}
        </a>
        '''
    
    # Build card HTML
    card_html = f'''
    <div class="performer-card">
        <div class="img-box">
            {img_html}
        </div>
        <p class="performer-name" title="{performer.name}">{performer.name}</p>
        <div class="external-links">
            {links_html}
        </div>
    </div>
    '''
    
    return card_html


def render_performer_grid(performers: List[Performer], external_sites: List[Dict[str, Any]]) -> str:
    """
    Render a grid of performer cards.
    
    Args:
        performers: List of Performer objects
        external_sites: List of external site configurations
    
    Returns:
        HTML string for the performer grid
    """
    if not performers:
        return '<div class="status-message status-info">No performers found.</div>'
    
    cards_html = ""
    for performer in performers:
        cards_html += render_performer_card(performer, external_sites)
    
    return f'<div class="performer-grid">{cards_html}</div>'


def render_pagination(current_page: int, total_performers: int, items_per_page: int = 48) -> str:
    """
    Render pagination controls with "Load More" button.
    
    Args:
        current_page: Current page number (1-indexed)
        total_performers: Total number of performers loaded so far
        items_per_page: Number of items per page
    
    Returns:
        HTML string for pagination controls
    """
    total_loaded_pages = current_page
    total_items_shown = total_performers
    
    page_info = f'<div class="page-info">Page <span>{current_page}</span> - Showing <span>{total_items_shown}</span> performers</div>'
    
    # Load More button (always enabled - we don't know if there are more results until we try)
    button_html = '''
    <button class="load-more-btn" id="load-more-btn">
        ⚡ Load More
    </button>
    '''
    
    pagination_html = f'''
    <div class="pagination-container">
        {page_info}
        {button_html}
    </div>
    '''
    
    return pagination_html


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
    
    return f'<div style="margin-bottom: 16px;">{"".join(badges)}</div>'