# Implementation Plan

## Overview
Transform the lo-scout-1 Streamlit application into a fully functional, professional-grade performer discovery tool with reliable freeones.com scraping, advanced filtering (height, weight, gender, dick length), proper pagination, multi-site search links (XVideos, Eporner, Sxyprn, Xmoviesforyou), and a seductive dark theme.

## Context & Scope

The current application has several critical issues that prevent it from being production-ready:

1. **Unreliable Data Fetching**: The scraper uses two strategies - Next.js JSON extraction and regex fallback. The JSON extraction may fail due to website structure changes or anti-bot measures, while the regex fallback only captures names without images or slugs.

2. **Broken Thumbnail Pairing**: When the regex fallback is used, performer entries are created with empty image URLs, resulting in broken image displays. Even with JSON extraction, there's no validation that images actually exist or are accessible.

3. **No Pagination**: All results are displayed at once in a 4-column grid with no way to navigate through large datasets, making the UI cluttered and unusable for substantial result sets.

4. **Missing Advanced Filtering**: The original application had sidebar filters for gender (babes/males), height, weight, and dick length (for males) that modified the freeones search URL. This functionality is currently missing and needs to be restored.

5. **Limited External Site Links**: Currently only links to XVideos and Eporner. User requires links to 4 sites: XVideos, Eporner, Sxyprn, and Xmoviesforyou.

6. **Amateur UI/UX**: The current interface uses basic styling with minimal visual hierarchy, no loading states, and lacks the professional, seductive aesthetic appropriate for an adult content discovery tool.

The solution will address all these issues while maintaining a modular architecture that allows for future expansion to additional sites without breaking the core functionality. The focus is on making freeones.com scraping work reliably first with full filtering capabilities (gender, height, weight, dick length), then displaying results with pagination (48 per page, Load More button) and links to 4 external adult sites for video searches.

## Types

Single sentence: Define robust data structures for performer information, filtering configuration, and pagination state.

```python
# Performer data model
class Performer:
    name: str                    # Performer name (required)
    slug: str                    # URL-friendly identifier (required)
    image_url: str              # Thumbnail image URL (can be empty string)
    height: Optional[int]       # Height in cm (for filtering)
    weight: Optional[int]       # Weight in kg (for filtering)
    gender: str                 # "female" or "male" (for filtering and UI)
    source: str                 # Source website identifier (e.g., "freeones")

# Filter configuration for freeones search
class FilterConfig:
    gender: str                 # "babes" or "males" - determines freeones URL
    min_height: Optional[int]   # Minimum height in cm
    max_height: Optional[int]   # Maximum height in cm
    min_weight: Optional[int]   # Minimum weight in kg
    max_weight: Optional[int]   # Maximum weight in kg
    min_dick_length: Optional[int]  # Minimum dick length in cm (males only)
    max_dick_length: Optional[int]  # Maximum dick length in cm (males only)
    
# Pagination state
class PaginationState:
    current_page: int           # Current page number (1-indexed)
    items_per_page: int         # Items per page (48)
    total_items: int            # Total number of items available (if known)
    current_items: List[Performer]  # Items on current page
    all_results: List[Performer]    # All fetched results (for client-side pagination)

# External site search URL configuration
class ExternalSite:
    name: str                   # Display name (e.g., "XVideos")
    search_url_pattern: str     # URL pattern with {query} placeholder
    icon: str                   # Short label for button (e.g., "XV")
```

## Files

Single sentence: Restructure the application into modular components with clear separation of concerns for scraping, filtering, and display.

### New Files to Create:

1. **`lo-scout-1/lo-scout/config.py`**
   - Centralized configuration for the application
   - Freeones API endpoints and URL patterns
   - External site search URL patterns for XVideos, Eporner, Sxyprn, Xmoviesforyou
   - UI constants: items per page (48), color scheme, styling constants
   - Example external site configs:
     ```python
     EXTERNAL_SITES = [
         {"name": "XVideos", "pattern": "https://www.xvideos.com/?k={query}", "icon": "XV"},
         {"name": "Eporner", "pattern": "https://www.eporner.com/search/{query}/", "icon": "EP"},
         {"name": "Sxyprn", "pattern": "https://www.sxyprn.com/search/{query}/", "icon": "SX"},
         {"name": "Xmoviesforyou", "pattern": "https://www.xmoviesforyou.com/search/{query}/", "icon": "XM"},
     ]
     ```

2. **`lo-scout-1/lo-scout/scraper/__init__.py`**
   - Package initialization for scraper modules
   - Exports base scraper and site-specific scrapers

3. **`lo-scout-1/lo-scout/scraper/base.py`**
   - Abstract base class for all scrapers
   - Common functionality: HTTP requests with cloudscraper, caching, error handling
   - Abstract methods: `fetch_performers()`, `parse_performer_data()`
   - Properties: `site_name`, `base_url`, `timeout`

4. **`lo-scout-1/lo-scout/scraper/freeones.py`**
   - Freeones-specific scraper implementation
   - Enhanced JSON extraction from `__NEXT_DATA__` with better error handling
   - Multiple parsing strategies with fallbacks
   - Image URL validation
   - Filter URL building: constructs URLs like `https://www.freeones.com/performers?s=rank.currentRank&o=desc&gender=babes&height_min=160&height_max=170&weight_min=50&weight_max=60`
   - Gender-specific handling (dick length filters for males)

5. **`lo-scout-1/lo-scout/ui/__init__.py`**
   - Package initialization for UI components

6. **`lo-scout-1/lo-scout/ui/components.py`**
   - Reusable UI components:
     - `render_filter_sidebar()`: Creates sidebar with gender dropdown, height/weight sliders, dick length sliders (conditional)
     - `render_performer_card()`: Generates performer card with 4 external site links
     - `render_pagination()`: Creates "Load More" button with page indicator
     - `render_loading_spinner()`: Shows loading state
   - All components return HTML strings for Streamlit rendering

7. **`lo-scout-1/lo-scout/ui/theme.py`**
   - CSS styling with dark, seductive theme
   - Color palette: deep purples (#8B5CF6), magentas (#EC4899), dark backgrounds (#0F0A1A)
   - Professional typography and spacing
   - Responsive grid layout for performer cards
   - Styled filter controls (sliders, dropdowns)
   - External site link buttons with hover effects

8. **`lo-scout-1/lo-scout/models/__init__.py`**
   - Package initialization for data models

9. **`lo-scout-1/lo-scout/models/performer.py`**
   - Performer data class with validation
   - Methods: `to_dict()`, `from_dict()`, `get_external_search_urls()`
   - Validation for required fields (name, slug)

10. **`lo-scout-1/lo-scout/models/filters.py`**
    - FilterConfig data class
    - Methods: `to_url_params()`, `from_streamlit_state()`
    - Validation for filter ranges (min < max)

### Files to Modify:

1. **`lo-scout-1/lo-scout/app.py`**
   - Complete rewrite to use modular architecture
   - Sidebar with filter controls (gender, height, weight, dick length)
   - Main content area with performer grid (4 columns)
   - "Load More" pagination (48 items per page)
   - Each performer card shows 4 external site links
   - Loading states and error handling
   - Use new UI components and theme

### Files to Delete:

None - all existing functionality will be preserved and enhanced.

## Functions

Single sentence: Implement robust scraping with filters, pagination, and UI rendering functions with proper error handling.

### New Functions:

1. **`scraper/base.py:BaseScraper.fetch_page(url: str) -> str`**
   - Makes HTTP request with cloudscraper
   - Handles retries (3 attempts) and timeouts (30 seconds)
   - Returns raw HTML content
   - Raises `ScraperError` on failure

2. **`scraper/freeones.py:FreeonesScraper.parse_performers(html: str) -> List[Performer]`**
   - Enhanced JSON extraction with multiple fallback strategies
   - Validates image URLs before including them
   - Extracts gender from performer data
   - Returns list of Performer objects with validated data

3. **`scraper/freeones.py:FreeonesScraper.fetch_performers(page: int, filters: FilterConfig) -> List[Performer]`**
   - Constructs proper URL with pagination and filter parameters
   - Fetches and parses a single page of results
   - Handles freeones.com URL parameter structure
   - Returns list of Performer objects for the requested page

4. **`scraper/freeones.py:FreeonesScraper.build_search_url(filters: FilterConfig, page: int) -> str`**
   - Builds freeones.com search URL with filter parameters
   - Handles gender-specific parameters (dick length for males only)
   - Example output: `https://www.freeones.com/performers?s=rank.currentRank&o=desc&gender=babes&height_min=160&height_max=170&weight_min=50&weight_max=60&page=1`
   - Returns properly formatted URL string

5. **`ui/components.py:render_filter_sidebar() -> FilterConfig`**
   - Creates sidebar UI with:
     - Gender dropdown: "Babes" or "Males"
     - Height range sliders (min/max in cm)
     - Weight range sliders (min/max in kg)
     - Dick length range sliders (min/max in cm, only shown when gender="Males")
   - Returns FilterConfig object with selected values

6. **`ui/components.py:render_performer_card(performer: Performer) -> str`**
   - Generates HTML for a single performer card
   - Handles missing images with placeholder (dark gradient background)
   - Creates 4 search links: XVideos, Eporner, Sxyprn, Xmoviesforyou
   - Each link opens in new tab with performer name as search query
   - Returns HTML string for Streamlit rendering

7. **`ui/components.py:render_pagination(current_page: int, has_more: bool) -> str`**
   - Creates "Load More" button
   - Shows current page indicator (e.g., "Page 1 - 48 performers")
   - Disables button when no more results available
   - Returns HTML string for Streamlit rendering

8. **`ui/components.py:render_loading_spinner() -> str`**
   - Shows animated loading indicator
   - Displays "Scanning performers..." message
   - Returns HTML string for Streamlit rendering

9. **`ui/theme.py:get_css() -> str`**
   - Returns complete CSS with dark seductive theme
   - Includes responsive grid layout (4 columns on desktop, 2 on tablet, 1 on mobile)
   - Professional typography (system fonts, proper sizing)
   - Styled performer cards with hover effects
   - Styled external site buttons with site-specific colors
   - Styled filter controls (sliders, dropdowns)

### Modified Functions:

1. **`app.py:parse_html_content()` → REMOVED**
   - Functionality moved to scraper modules
   - No longer needed in main app file

### Removed Functions:

1. **`app.py:parse_html_content()`**
   - Reason: Functionality moved to modular scraper architecture
   - Migration: Use `FreeonesScraper.fetch_performers(page, filters)` instead

## Classes

Single sentence: Create a modular scraper architecture with base and site-specific implementations, plus data models for performers and filters.

### New Classes:

1. **`scraper/base.py:BaseScraper`**
   - Abstract base class for all site scrapers
   - Methods: `fetch_page(url)`, `get_headers()`, `handle_error()`
   - Properties: `site_name`, `base_url`, `timeout`
   - Provides common HTTP client setup with cloudscraper
   - Template method pattern for scrape workflow

2. **`scraper/freeones.py:FreeonesScraper(BaseScraper)`**
   - Inherits from BaseScraper
   - Implements freeones-specific parsing logic
   - Methods: `fetch_performers(page, filters)`, `build_search_url(filters, page)`, `parse_performers(html)`, `extract_from_json(html)`, `extract_from_regex(html)`
   - Handles freeones.com pagination and filter parameters (gender, height, weight, dick length)
   - Constructs URLs with proper query parameters for freeones search API

3. **`models/performer.py:Performer`**
   - Data class for performer information
   - Properties: name (str), slug (str), image_url (str), height (Optional[int]), weight (Optional[int]), gender (str), source (str)
   - Methods: `to_dict()`, `from_dict()`, `get_external_search_urls()` returns dict of site_name -> URL
   - Validation: name and slug are required, image_url can be empty

4. **`models/filters.py:FilterConfig`**
   - Data class for filter configuration
   - Properties: gender (str), min_height (Optional[int]), max_height (Optional[int]), min_weight (Optional[int]), max_weight (Optional[int]), min_dick_length (Optional[int]), max_dick_length (Optional[int])
   - Methods: `to_url_params()` returns dict for URL query string, `from_streamlit_state()` creates from session state
   - Validation: min values must be less than max values, dick_length only valid for males

5. **`ui/components.py:PerformerCard`**
   - Static class for rendering performer cards
   - Methods: `render(performer)` returns HTML string
   - Handles missing data gracefully (placeholder image, no broken links)
   - Generates 4 external site search links per performer

### Modified Classes:

None - no existing classes to modify.

### Removed Classes:

None - no existing classes to remove.

## Dependencies

Single sentence: Add fake-useragent for better request headers and maintain existing reliable dependencies.

### Current Dependencies:
- streamlit
- cloudscraper
- beautifulsoup4

### New Dependencies:
- **fake-useragent** (for more realistic rotating request headers to avoid blocking)

### Updated requirements.txt:
```
streamlit
cloudscraper
beautifulsoup4
fake-useragent
```

### Integration Notes:
- cloudscraper remains primary HTTP client for bypassing Cloudflare
- fake-useragent provides rotating user agents for better success rates
- beautifulsoup4 for HTML parsing
- No breaking changes to existing functionality

## Testing

Single sentence: Implement manual testing procedures to verify scraping functionality, filter application, pagination, and data integrity.

### Test Scenarios:

1. **Basic Scraping Test**
   - Run app with no filters
   - Verify performers are fetched and displayed with images
   - Check that all performers have names and valid image URLs

2. **Filter Testing**
   - Test gender filter: select "Babes" only, verify only female performers shown
   - Test gender filter: select "Males" only, verify only male performers shown
   - Test height filter: set range 160-170cm, verify results match
   - Test weight filter: set range 50-60kg, verify results match
   - Test dick length filter: only visible when gender="Males", verify filtering works

3. **Pagination Testing**
   - Verify "Load More" button appears after first 48 results
   - Click "Load More" and verify next 48 results load
   - Verify page indicator updates correctly
   - Verify button disables when no more results

4. **External Links Testing**
   - Verify each performer card shows 4 links (XV, EP, SX, XM)
   - Click each link and verify it opens correct site with performer name in search
   - Verify links open in new tabs

5. **Error Handling Testing**
   - Test behavior when freeones.com is down
   - Test behavior when parsing fails
   - Verify user-friendly error messages display

### Validation Strategies:
- Manual testing: Run app and interact with all features
- Data validation: Check that all performers have names and valid image URLs
- Filter validation: Verify URL parameters match selected filters
- Link validation: Verify external site URLs are correctly formatted

### Existing Test Modifications:
None - no existing tests to modify.

## Implementation Order

Single sentence: Implement in order of dependency, starting with core models and ending with UI integration.

1. **Create project structure**: Set up directories for scraper/, ui/, and models/ packages with __init__.py files

2. **Implement data models**: Create Performer class (models/performer.py) and FilterConfig class (models/filters.py) with validation methods

3. **Build base scraper**: Implement BaseScraper abstract class (scraper/base.py) with HTTP client using cloudscraper and fake-useragent

4. **Implement FreeonesScraper**: Create freeones-specific scraper (scraper/freeones.py) with enhanced JSON parsing, filter URL building, and gender-specific handling

5. **Create UI theme**: Define CSS (ui/theme.py) with dark seductive theme using deep purples (#8B5CF6), magentas (#EC4899), and dark backgrounds (#0F0A1A)

6. **Build UI components**: Create filter sidebar with gender/height/weight/dick-length controls, performer card with 4 external site links, and "Load More" pagination (ui/components.py)

7. **Create configuration**: Create config.py with freeones URL patterns, external site search URLs (XVideos, Eporner, Sxyprn, Xmoviesforyou), and UI constants

8. **Rewrite main app**: Integrate all components in app.py with sidebar filters, performer grid (4 columns), pagination (48 per page), loading states, and error handling

9. **Test integration**: Manually test scraping with various filter combinations, verify pagination loads correctly, test all 4 external links generate proper search URLs

10. **Final polish**: Add loading spinners, improve error messages, ensure gender-specific filters show/hide correctly, test responsive design on different screen sizes