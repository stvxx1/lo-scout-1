"""
Base scraper module for lo-scout application.
Provides abstract base class for all site scrapers.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import time
import logging

import cloudscraper
from fake_useragent import UserAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Custom exception for scraper errors."""
    pass


class BaseScraper(ABC):
    """Abstract base class for all site scrapers."""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3, retry_delay: float = 2.0):
        """
        Initialize base scraper.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Initialize cloudscraper with rotating user agents
        self.scraper = cloudscraper.create_scraper()
        self.ua = UserAgent()
        
        # Cache for fetched pages
        self._cache: Dict[str, str] = {}
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get request headers with rotating user agent.
        
        Returns:
            Dictionary of HTTP headers
        """
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
    def fetch_page(self, url: str, use_cache: bool = True) -> str:
        """
        Fetch HTML content from URL with retry logic.
        
        Args:
            url: URL to fetch
            use_cache: Whether to use cached content if available
        
        Returns:
            Raw HTML content as string
        
        Raises:
            ScraperError: If fetching fails after all retries
        """
        # Check cache first
        if use_cache and url in self._cache:
            logger.info(f"Using cached content for {url}")
            return self._cache[url]
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Fetching {url} (attempt {attempt + 1}/{self.max_retries})")
                
                headers = self._get_headers()
                response = self.scraper.get(
                    url, 
                    headers=headers, 
                    timeout=self.timeout
                )
                
                response.raise_for_status()
                
                # Cache the result
                self._cache[url] = response.text
                
                return response.text
                
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                
                if attempt < self.max_retries - 1:
                    logger.info(f"Waiting {self.retry_delay}s before retry...")
                    time.sleep(self.retry_delay)
        
        # All retries failed
        error_msg = f"Failed to fetch {url} after {self.max_retries} attempts: {last_error}"
        logger.error(error_msg)
        raise ScraperError(error_msg)
    
    def clear_cache(self):
        """Clear the page cache."""
        self._cache.clear()
    
    @property
    @abstractmethod
    def site_name(self) -> str:
        """Return the name of the site being scraped."""
        pass
    
    @property
    @abstractmethod
    def base_url(self) -> str:
        """Return the base URL for the site."""
        pass
    
    @abstractmethod
    def fetch_performers(self, page: int = 1, filters: Any = None) -> List[Any]:
        """
        Fetch performers from the site.
        
        Args:
            page: Page number to fetch (1-indexed)
            filters: Optional filter configuration
        
        Returns:
            List of Performer objects
        """
        pass
    
    @abstractmethod
    def parse_performers(self, html: str) -> List[Any]:
        """
        Parse performer data from HTML content.
        
        Args:
            html: Raw HTML content
        
        Returns:
            List of Performer objects
        """
        pass
    
    def _handle_error(self, error: Exception, context: str = "") -> None:
        """
        Handle scraper errors with logging.
        
        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
        """
        error_msg = f"Error in {self.site_name} scraper"
        if context:
            error_msg += f" ({context})"
        error_msg += f": {error}"
        
        logger.error(error_msg)