from abc import ABC, abstractmethod
import cloudscraper
import time
from typing import Any, Dict, List, Optional
from fake_useragent import UserAgent

class ScraperError(Exception):
    """Custom exception for scraper-related errors."""
    pass

class BaseScraper(ABC):
    site_name: str
    base_url: str
    timeout: int = 30
    retries: int = 3
    retry_delay: float = 2.0

    def __init__(self, timeout: int = 30, max_retries: int = 3, retry_delay: float = 2.0):
        self.scraper = cloudscraper.create_scraper()
        self.ua = UserAgent()
        self.timeout = timeout
        self.retries = max_retries
        self.retry_delay = retry_delay

    def fetch_page(self, url: str) -> str:
        """Makes an HTTP request with retries and returns raw HTML content."""
        headers = self.get_headers()
        for attempt in range(self.retries):
            try:
                response = self.scraper.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except Exception as e:
                if attempt < self.retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise ScraperError(f"Failed to fetch {url} after {self.retries} attempts: {e}") from e
        return ""

    @abstractmethod
    def fetch_performers(self, page: int, filters: Any) -> List[Any]:
        """Abstract method to fetch performers for a given page and filters."""
        pass

    @abstractmethod
    def parse_performers(self, html: str) -> List[Any]:
        """Abstract method to parse performer data from raw HTML."""
        pass

    def get_headers(self) -> Dict[str, str]:
        """Returns default headers with a random user agent."""
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": self.base_url,
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }

    def handle_error(self, message: str, original_exception: Optional[Exception] = None):
        """Logs and raises a ScraperError."""
        if original_exception:
            raise ScraperError(f"{message}: {original_exception}") from original_exception
        else:
            raise ScraperError(message)
