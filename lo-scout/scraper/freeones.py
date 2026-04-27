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

from .base import BaseScraper, ScraperError
from ..models.performer import Performer
from ..models.filters import FilterConfig

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
            params["page"] = str(page)
        
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
        
        # Strategy 2: Enhanced regex extraction
        try:
            performers = self._extract_from_regex_enhanced(html)
            if performers:
                logger.info(f"Enhanced regex extraction successful: {len(performers)} performers")
                return performers
        except Exception as e:
            logger.warning(f"Enhanced regex extraction failed: {e}")
        
        # Strategy 3: BeautifulSoup DOM parsing
        try:
            performers = self._extract_from_dom(html)
            if performers:
                logger.info(f"DOM extraction successful: {len(performers)} performers")
                return performers
        except Exception as e:
            logger.warning(f"DOM extraction failed: {e}")
        
        logger.error("All extraction strategies failed")
        return []
    
    def _extract_from_json(self, html: str) -> List[Performer]:
        """
        Extract performers from Next.js JSON data.
        
        Args:
            html: Raw HTML content
        
        Returns:
            List of Performer objects
        """
        soup = BeautifulSoup(html, 'html.parser')
        script_tag = soup.find('script', id='__NEXT_DATA__')
        
        if not script_tag or not script_tag.string:
            return []
        
        try:
            data = json.loads(script_tag.string)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse __NEXT_DATA__ JSON: {e}")
            return []
        
        # Recursively search for 'edges' in the JSON structure
        edges = self._find_edges(data)
        if not edges:
            return []
        
        performers = []
        for item in edges:
            try:
                node = item.get('node', {})
                if not node:
                    continue
                
                name = node.get('name')
                if not name:
                    continue
                
                slug = node.get('slug', '')
                
                # Extract image URL
                image_url = ''
                main_image = node.get('mainImage', {})
                if main_image:
                    # Try different image size fields
                    image_url = (
                        main_image.get('urls', {}).get('large') or
                        main_image.get('urls', {}).get('medium') or
                        main_image.get('urls', {}).get('small') or
                        main_image.get('url', '')
                    )
                
                # Extract gender if available
                gender = 'female'  # Default
                if 'gender' in node:
                    gender_value = node.get('gender', '').lower()
                    if 'male' in gender_value:
                        gender = 'male'
                
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
            if 'edges' in obj and isinstance(obj['edges'], list):
                return obj['edges']
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
        
        # Pattern for performer data in JSON-like format
        patterns = [
            # Pattern for name, slug, and image together
            r'"name"\s*:\s*"([^"]+)"\s*,\s*"slug"\s*:\s*"([^"]+)".*?"image"\s*:\s*"([^"]+)"',
            r'"name"\s*:\s*"([^"]+)"\s*,\s*"slug"\s*:\s*"([^"]+)"',
            # Alternative pattern
            r'"slug"\s*:\s*"([^"]+)"\s*,\s*"name"\s*:\s*"([^"]+)"',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, html)
            for match in matches:
                try:
                    groups = match.groups()
                    
                    if len(groups) >= 2:
                        # Determine order based on pattern
                        if 'slug' in pattern and pattern.index('slug') < pattern.index('name'):
                            slug, name = groups[0], groups[1]
                            image_url = groups[2] if len(groups) > 2 else ''
                        else:
                            name, slug = groups[0], groups[1]
                            image_url = groups[2] if len(groups) > 2 else ''
                        
                        # Skip duplicates and invalid entries
                        if name in seen_names or not name.strip():
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
                    logger.warning(f"Error parsing regex match: {e}")
                    continue
            
            if performers:
                break  # Use results from first successful pattern
        
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
        
        # Look for performer cards/containers
        # Freeones uses various class names for performer listings
        container_selectors = [
            '[data-test=" performer-card"]',
            '.performer-card',
            '.performer-link',
            'a[href^="/profile/"]',
        ]
        
        seen_names = set()
        
        for selector in container_selectors:
            elements = soup.select(selector)
            
            for element in elements:
                try:
                    # Extract name
                    name_element = element.find(
                        ['span', 'div', 'p'],
                        class_=re.compile(r'name|performer', re.I)
                    )
                    if not name_element:
                        name_element = element
                    
                    name = name_element.get_text(strip=True)
                    if not name or name in seen_names:
                        continue
                    
                    # Extract slug from href
                    href = element.get('href', '')
                    slug = ''
                    if '/profile/' in href:
                        slug = href.split('/profile/')[-1].strip('/')
                    
                    # Extract image
                    img_element = element.find('img')
                    image_url = ''
                    if img_element:
                        image_url = (
                            img_element.get('data-src') or
                            img_element.get('src') or
                            ''
                        )
                    
                    if name and slug:
                        seen_names.add(name)
                        performer = Performer(
                            name=name,
                            slug=slug,
                            image_url=image_url,
                            source="freeones"
                        )
                        performers.append(performer)
                        
                except Exception as e:
                    logger.warning(f"Error parsing DOM element: {e}")
                    continue
            
            if performers:
                break  # Use results from first successful selector
        
        return performers
    
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
        if any(domain in url for domain in ['freeones.com', 'cloudfront', 'amazonaws']):
            return True
        
        return False