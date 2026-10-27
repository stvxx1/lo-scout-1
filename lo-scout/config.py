"""
Configuration module for lo-scout application.
Centralized configuration for external sites, constants, and settings.
"""

from typing import List, Dict, Any

# ===== EXTERNAL SITE CONFIGURATIONS =====
# These sites will be used for performer search links

# Each pattern was checked against the live site; `encoding` selects how the
# performer name is escaped before it is dropped into the template
# (see links.encode_query). Getting either half wrong silently lands the user
# on an age wall, a 404, or a search page that ignores the query.
EXTERNAL_SITES: List[Dict[str, Any]] = [
    {
        "name": "XVideos",
        "pattern": "https://www.xvideos.com/?k={query}",
        "encoding": "quote_plus",
        "icon": "XV",
        "description": "Popular adult video site"
    },
    {
        "name": "Eporner",
        # 302s to the canonical /tag/<name>/ page; %20 keeps multi-word names intact.
        "pattern": "https://www.eporner.com/search/{query}/",
        "encoding": "quote",
        "icon": "EP",
        "description": "High-quality adult videos"
    },
    {
        "name": "Sxyprn",
        # The trailing .html is required: /search/<name>/ returns a hard 404.
        "pattern": "https://www.sxyprn.com/search/{query}.html",
        "encoding": "slug",
        "icon": "SX",
        "description": "Adult video search engine"
    },
    {
        "name": "Xmoviesforyou",
        # Taken from the site's own JSON-LD SearchAction; /search/<name>/ drops the query.
        "pattern": "https://xmoviesforyou.com/search?q={query}",
        "encoding": "quote_plus",
        "icon": "XM",
        "description": "Adult movie database"
    }
]

# ===== PAGINATION SETTINGS =====
# Freeones' own default page size (robots.txt disallows overriding it with l=).
# app.py compares a page's row count against this to detect the end of the list.
ITEMS_PER_PAGE: int = 24

# ===== FREEONES CONFIGURATION =====
FREEONES_BASE_URL: str = "https://www.freeones.com"
FREEONES_PERFORMERS_PATH: str = "/performers"

# ===== SCRAPING SETTINGS =====
SCRAPER_TIMEOUT: int = 30  # Request timeout in seconds
SCRAPER_MAX_RETRIES: int = 3  # Maximum retry attempts
SCRAPER_RETRY_DELAY: float = 2.0  # Delay between retries in seconds

# ===== UI CONSTANTS =====
DEFAULT_GENDER: str = "babes"  # Default gender filter

# Height range (cm)
MIN_HEIGHT_DEFAULT: int = 0
MAX_HEIGHT_DEFAULT: int = 300

# Weight range (kg)
MIN_WEIGHT_DEFAULT: int = 0
MAX_WEIGHT_DEFAULT: int = 500

# Dick length range (cm) - males only
MIN_DICK_LENGTH_DEFAULT: int = 0
MAX_DICK_LENGTH_DEFAULT: int = 50

# ===== THEME COLORS =====
THEME_COLORS: Dict[str, str] = {
    "bg_primary": "#0F0A1A",
    "bg_secondary": "#1A1025",
    "bg_tertiary": "#251535",
    "bg_card": "#1E1230",
    "accent_purple": "#8B5CF6",
    "accent_purple_light": "#A78BFA",
    "accent_magenta": "#EC4899",
    "accent_magenta_light": "#F472B6",
    "text_primary": "#F5F3FF",
    "text_secondary": "#C4B5FD",
    "text-muted": "#8B7EC8",
    "border_primary": "#3D2C5E",
    "border_hover": "#8B5CF6"
}

# ===== APP METADATA =====
APP_TITLE: str = "LO-SCOUT TITAN V22"
APP_ICON: str = "🔮"
APP_DESCRIPTION: str = "Professional performer discovery tool with advanced filtering"

# ===== FEATURE FLAGS =====
ENABLE_MANUAL_PASTE_MODE: bool = True  # Allow users to paste HTML manually
ENABLE_CACHE: bool = True  # Enable page caching for faster subsequent loads