from abc import ABC, abstractmethod
import cloudscraper
import time
from typing import Any, Dict, List

class ScraperError(Exception):
    """Custom exception for scraper-related errors."""
    pass

class BaseScraper(ABC):
    site_name: str
    base_url: str
    timeout: int = 30
    retries: int = 3

    def __init__(self):
        self.scraper = cloudscraper.create_scraper()  # Create a cloudscraper instance

    def fetch_page(self, url: str) -> str:
        """Makes an HTTP request with retries and returns raw HTML content."""
        for attempt in range(self.retries):
            try:
                response = self.scraper.get(url, timeout=self.timeout)
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                return response.text
            except Exception as e:
                if attempt < self.retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise ScraperError(f"Failed to fetch {url} after {self.retries} attempts: {e}") from e
        return "" # Should not be reached

    @abstractmethod
    def fetch_performers(self, page: int, filters: Any) -> List[Any]:
        """Abstract method to fetch performers for a given page and filters."""
        pass

    @abstractmethod
    def parse_performers(self, html: str) -> List[Any]:
        """Abstract method to parse performer data from raw HTML."""
        pass

    def get_headers(self) -> Dict[str, str]:
        """Returns default headers for requests. Can be overridden by subclasses."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def handle_error(self, message: str, original_exception: Optional[Exception] = None):
        """Logs and raises a ScraperError."""
        if original_exception:
            raise ScraperError(f"{message}: {original_exception}") from original_exception
        else:
            raise ScraperError(message)
