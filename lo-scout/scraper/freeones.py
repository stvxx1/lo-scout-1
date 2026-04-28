"""
Freeones scraper module for lo-scout application.
Implements scraping logic for freeones.com performer database.
"""

from typing import List, Optional, Dict, Any
import json
import re
import logging
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from scraper.base import BaseScraper, ScraperError
from models.performer import Performer
from models.filters import FilterConfig

logger = logging.getLogger(__name__)


class FreeonesScraper(BaseScraper):
    """Scraper for freeones.com performer database."""
    
    BASE_URL = "https://www.freeones.com"
    PERFORMERS_PATH = "/performers"
    
    def __init__(self, timeout: int = 30, max_retries: int = 3, retry_delay: float = 2.0):
        """
        Initialize Freeones scraper.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        super().__init__(timeout, max_retries, retry_delay)
    
    @property
    def site_name(self) -> str:
        """Return the name of the site being scraped."""
        return "freeones"
    
    @property
    def base_url(self) -> str:
        """Return the base URL for the site."""
        return self.BASE_URL
    
    def build_search_url(self, filters: FilterConfig, page: int = 1) -> str:
        """
        Build freeones.com search URL with filter parameters.
        
        Args:
            filters: Filter configuration
            page: Page number (1-indexed)
        
        Returns:
            Complete URL string
        """
        params = filters.to_url_params()
        
        # Add pagination parameter
        if page > 1:
            params["p"] = str(page) # Site uses 'p' for pagination in the new structure
        
        query_string = urlencode(params)
        url = f"{self.BASE_URL}{self.PERFORMERS_PATH}?{query_string}"
        
        logger.info(f"Built search URL: {url}")
        return url
    
    def fetch_performers(self, page: int = 1, filters: FilterConfig = None) -> List[Performer]:
        """
        Fetch performers from freeones.com.
        
        Args:
            page: Page number to fetch (1-indexed)
            filters: Optional filter configuration
        
        Returns:
            List of Performer objects
        """
        if filters is None:
            filters = FilterConfig()
        
        url = self.build_search_url(filters, page)
        
        try:
            html = self.fetch_page(url, use_cache=True)
            performers = self.parse_performers(html)
            
            logger.info(f"Fetched {len(performers)} performers from page {page}")
            return performers
            
        except ScraperError as e:
            self._handle_error(e, f"page={page}")
            return []
    
    def parse_performers(self, html: str) -> List[Performer]:
        """
        Parse performer data from HTML content using multiple strategies.
        
        Args:
            html: Raw HTML content
        
        Returns:
            List of Performer objects
        """
        performers = []
        
        # Strategy 1: Next.js JSON extraction (most reliable)
        try:
            performers = self._extract_from_json(html)
            if performers:
                logger.info(f"JSON extraction successful: {len(performers)} performers")
                return performers
        except Exception as e:
            logger.warning(f"JSON extraction failed: {e}")
        
        # Strategy 2: Enhanced regex extraction with multiple patterns
        try:
            performers = self._extract_from_regex_enhanced(html)
            if performers:
                logger.info(f"Enhanced regex extraction successful: {len(performers)} performers")
                return performers
        except Exception as e:
            logger.warning(f"Enhanced regex extraction failed: {e}")
        
        # Strategy 3: BeautifulSoup DOM parsing with better selectors
        try:
            performers = self._extract_from_dom(html)
            if performers:
                logger.info(f"DOM extraction successful: {len(performers)} performers")
                return performers
        except Exception as e:
            logger.warning(f"DOM extraction failed: {e}")
        
        # Strategy 4: Simple name extraction as last resort
        try:
            performers = self._extract_names_only(html)
            if performers:
                logger.info(f"Names-only extraction successful: {len(performers)} performers")
                return performers
        except Exception as e:
            logger.warning(f"Names-only extraction failed: {e}")
        
        logger.error("All extraction strategies failed")
        return []
    
    def _extract_from_json(self, html: str) -> List[Performer]:
        """
        Extract performers from embedded JSON data (__INITIAL_STATE__ or __NEXT_DATA__).
        
        Args:
            html: Raw HTML content
        
        Returns:
            List of Performer objects
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        data = None
        
        # Try to find __INITIAL_STATE__ (New Freeones structure)
        scripts = soup.find_all('script')
        for s in scripts:
            if s.string and '__INITIAL_STATE__' in s.string:
                match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', s.string)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        logger.debug("Found __INITIAL_STATE__ JSON")
                        break
                    except json.JSONDecodeError:
                        pass
        
        # Fallback to __NEXT_DATA__ (Old Freeones structure)
        if not data:
            script_tag = soup.find('script', id='__NEXT_DATA__')
            if script_tag and script_tag.string:
                try:
                    data = json.loads(script_tag.string)
                    logger.debug("Found __NEXT_DATA__ JSON")
                except json.JSONDecodeError:
                    pass
        
        if not data:
            logger.debug("No JSON state found in scripts")
            return []
            
        edges = self._find_edges(data)
        
        if not edges:
            logger.debug("No edges found in JSON data")
            return []
        
        performers = []
        for item in edges:
            try:
                node = item.get('node', {}) if isinstance(item, dict) else item
                if not node or not isinstance(node, dict):
                    continue
                
                # In the new structure, node might contain 'performer' object
                if 'performer' in node:
                    node = node['performer']
                
                name = node.get('name')
                if not name:
                    continue
                
                # Skip non-performer names
                if any(x in name.lower() for x in ['loading', 'error', 'null', 'undefined', 'view all', 'credits', 'transactions', 'overview', 'window.', 'https:', 'path']):
                    continue
                
                slug = node.get('slug', '')
                if not slug:
                    # sometimes the slug is nested
                    slug = node.get('uri', '').replace('/profile/', '')
                
                # Extract image URL - try multiple fields
                image_url = ''
                main_image = node.get('mainImage', {}) or node.get('image', {}) or node.get('thumbnail', {}) or node.get('picture', {})
                if main_image:
                    # Try different image URL fields
                    if isinstance(main_image, dict):
                        image_url = (
                            main_image.get('urls', {}).get('large') or
                            main_image.get('urls', {}).get('medium') or
                            main_image.get('urls', {}).get('small') or
                            main_image.get('url') or
                            main_image.get('src') or
                            ''
                        )
                    elif isinstance(main_image, str):
                        image_url = main_image
                
                # Extract gender if available
                gender = node.get('gender', 'female')
                if gender:
                    gender = str(gender).lower()
                    if 'male' == gender or 'males' == gender:
                        gender = 'male'
                    else:
                        gender = 'female'
                else:
                    gender = 'female'
                
                # Validate image URL
                if image_url and not image_url.startswith(('http://', 'https://')):
                    image_url = ''
                
                performer = Performer(
                    name=name,
                    slug=slug,
                    image_url=image_url,
                    gender=gender,
                    source="freeones"
                )
                performers.append(performer)
                
            except Exception as e:
                logger.warning(f"Error parsing performer node: {e}")
                continue
        
        return performers
    
    def _find_edges(self, obj: Any) -> Optional[List]:
        """
        Recursively find 'edges' array in JSON structure.
        
        Args:
            obj: JSON object to search
        
        Returns:
            List of edge items or None
        """
        if isinstance(obj, dict):
            # Check for edges
            if 'edges' in obj and isinstance(obj['edges'], list) and len(obj['edges']) > 0:
                # Verify it looks like performer data
                first_edge = obj['edges'][0]
                if isinstance(first_edge, dict) and 'node' in first_edge:
                    return obj['edges']
                elif isinstance(first_edge, dict) and 'name' in first_edge:
                    return obj['edges']
            
            # Check for direct items array
            if 'items' in obj and isinstance(obj['items'], list) and len(obj['items']) > 0:
                first_item = obj['items'][0]
                if isinstance(first_item, dict) and ('name' in first_item or 'node' in first_item):
                    return [{'node': item} if 'node' not in item else item for item in obj['items']]
            
            # Recurse into values
            for value in obj.values():
                result = self._find_edges(value)
                if result is not None:
                    return result
                    
        elif isinstance(obj, list):
            for item in obj:
                result = self._find_edges(item)
                if result is not None:
                    return result
                    
        return None
    
    def _extract_from_regex_enhanced(self, html: str) -> List[Performer]:
        """
        Extract performers using enhanced regex patterns.
        
        Args:
            html: Raw HTML content
        
        Returns:
            List of Performer objects
        """
        performers = []
        seen_names = set()
        
        # Pattern 1: Look for performer data in JSON format within the HTML
        # Matches: {"name":"...","slug":"...","image":"..."}
        json_patterns = [
            r'\{[^}]*"name"\s*:\s*"([^"]+)"[^}]*"slug"\s*:\s*"([^"]+)"[^}]*\}',
            r'\{[^}]*"slug"\s*:\s*"([^"]+)"[^}]*"name"\s*:\s*"([^"]+)"[^}]*\}',
        ]
        
        for pattern in json_patterns:
            matches = re.finditer(pattern, html)
            for match in matches:
                try:
                    groups = match.groups()
                    matched_text = match.group(0)
                    
                    # Determine name and slug based on pattern order
                    if 'slug' in pattern and pattern.index('slug') < pattern.index('name'):
                        slug, name = groups[0], groups[1]
                    else:
                        name, slug = groups[0], groups[1]
                    
                    # Extract image if present
                    image_match = re.search(r'"(?:image|img|thumbnail|src)"\s*:\s*"([^"]+)"', matched_text)
                    image_url = image_match.group(1) if image_match else ''
                    
                    # Skip duplicates and invalid entries
                    if name in seen_names or not name.strip():
                        continue
                    
                    # Skip common non-performer names
                    if name.lower() in ['loading', 'error', 'null', 'undefined']:
                        continue
                    
                    seen_names.add(name)
                    
                    # Validate image URL
                    if image_url and not image_url.startswith(('http://', 'https://')):
                        image_url = ''
                    
                    performer = Performer(
                        name=name,
                        slug=slug,
                        image_url=image_url,
                        source="freeones"
                    )
                    performers.append(performer)
                    
                except Exception as e:
                    continue
            
            if performers:
                break
        
        return performers
    
    def _extract_from_dom(self, html: str) -> List[Performer]:
        """
        Extract performers using BeautifulSoup DOM parsing.
        
        Args:
            html: Raw HTML content
        
        Returns:
            List of Performer objects
        """
        performers = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # New strategy based on the provided HTML
        grid_items = soup.select('.grid-item, article')
        
        seen_names = set()
        
        for item in grid_items:
            try:
                name = None
                slug = ''
                image_url = ''
                
                # Name is often in a p tag with data-test="subject-name" or class "performer-name"
                name_elem = item.select_one('[data-test="subject-name"], .performer-name, .name')
                if name_elem:
                    name = name_elem.get_text(strip=True)
                
                # Image is in an img tag
                img_elem = item.find('img')
                if img_elem:
                    image_url = img_elem.get('src') or img_elem.get('data-src') or ''
                
                # Slug is in the href of a link
                link_elems = item.select('a[href*="/profile/"], a[href*="/feed"], a[href*="/videos"]')
                for link in link_elems:
                    href = link.get('href', '')
                    if '/my/' in href or 'credits' in href or 'transactions' in href:
                        continue
                    
                    # Extract slug. E.g., /selina-imai/feed -> selina-imai
                    parts = [p for p in href.split('/') if p and p not in ('https:', 'www.freeones.com', 'profile', 'feed', 'videos', 'photos', 'links', 'bio')]
                    if parts:
                        slug = parts[0]
                        break
                        
                # If we couldn't find the name but have a slug, use a capitalized slug as fallback
                if not name and slug:
                    name = slug.replace('-', ' ').title()
                
                # Validate and add performer
                if name and slug and name not in seen_names:
                    # Skip non-performer names
                    if any(x in name.lower() for x in ['loading', 'error', 'null', 'undefined', 'view all', 'credits', 'transactions', 'overview', 'window.', 'https:', 'path']):
                        continue
                    
                    # Skip very short or very long names
                    if len(name) < 2 or len(name) > 100:
                        continue
                    
                    seen_names.add(name)
                    
                    # Validate image URL
                    if image_url and not image_url.startswith(('http://', 'https://')):
                        image_url = ''
                    
                    performer = Performer(
                        name=name,
                        slug=slug,
                        image_url=image_url,
                        source="freeones"
                    )
                    performers.append(performer)
                    
            except Exception as e:
                continue
        
        return performers
    
    def _extract_names_only(self, html: str) -> List[Performer]:
        """
        Extract performer names only as a last resort.
        
        Args:
            html: Raw HTML content
        
        Returns:
            List of Performer objects (without images or slugs)
        """
        performers = []
        seen_names = set()
        
        # Look for patterns that typically contain performer names
        patterns = [
            r'/"profile/([^"]+)">',  # href="/profile/xxx">
            r'/profile/([^/]+)/',     # /profile/xxx/
            r'"name":"([^"]+)","slug"',  # JSON pattern
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, html)
            for match in matches:
                name = match.group(1)
                if name and name not in seen_names and len(name) > 2 and len(name) < 100:
                    # Skip common non-name patterns
                    if any(x in name.lower() for x in ['loading', 'error', 'null', 'undefined', 'credits', 'transactions', 'overview', 'window.', 'https:', 'path']):
                        continue
                    if re.match(r'^\d+$', name):  # Skip pure numbers
                        continue
                    if '\n' in name or '\r' in name: # Skip names with newlines
                        continue
                    
                    seen_names.add(name)
                    slug = name.lower().replace(' ', '-').replace("'", "")
                    
                    performer = Performer(
                        name=name,
                        slug=slug,
                        image_url='',
                        source="freeones"
                    )
                    performers.append(performer)
            
            if performers:
                break
        
        # Limit to reasonable number
        return performers[:100]
    
    def validate_image_url(self, url: str) -> bool:
        """
        Validate that an image URL is accessible.
        
        Args:
            url: Image URL to validate
        
        Returns:
            True if URL appears valid
        """
        if not url:
            return False
        
        # Basic URL format validation
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Check for common image extensions
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        url_lower = url.lower()
        
        # Some freeones URLs use query parameters for images
        if any(ext in url_lower for ext in valid_extensions):
            return True
        
        # Accept URLs that look like image CDN URLs
        if any(domain in url for domain in ['freeones.com', 'cloudfront', 'amazonaws', 'imgur']):
            return True
        
        return False