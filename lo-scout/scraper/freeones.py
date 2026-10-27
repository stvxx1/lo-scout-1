import re
from urllib.parse import urlencode, urljoin
from typing import List

from bs4 import BeautifulSoup

from scraper.base import BaseScraper
from models.performer import Performer
from models.filters import FilterConfig
from config import ITEMS_PER_PAGE

class FreeonesScraper(BaseScraper):
    site_name: str = "freeones"
    base_url: str = "https://www.freeones.com"

    def __init__(self, timeout: int = 30, max_retries: int = 3, retry_delay: float = 2.0):
        super().__init__(timeout=timeout, max_retries=max_retries, retry_delay=retry_delay)

    def build_search_url(self, filters: FilterConfig, page: int) -> str:
        params = filters.to_url_params()
        # "p" is the pagination parameter Freeones actually honours ("page" is ignored).
        # Rank is ascending: rank 1 is the most-viewed profile, so "asc" is best-first.
        params["s"] = "rank.currentRank"
        params["o"] = "asc"
        params["p"] = page
        params["l"] = ITEMS_PER_PAGE
        query_string = urlencode({k: v for k, v in params.items() if v is not None})
        return f"{urljoin(self.base_url, '/performers')}?{query_string}"

    def fetch_performers(self, page: int, filters: FilterConfig) -> List[Performer]:
        url = self.build_search_url(filters, page)
        html_content = self.fetch_page(url)
        return self.parse_performers(html_content)

    def parse_performers(self, html: str) -> List[Performer]:
        """Parse a listing page.

        Freeones renders with Vue, so there is no embedded JSON payload to read:
        the server-rendered DOM is the only source of truth.
        """
        performers = self._extract_from_bs4(html)
        if not performers:
            # Last resort if the markup changes shape
            performers = self._extract_from_regex(html)

        return performers

    def _extract_from_bs4(self, html: str) -> List[Performer]:
        performers = []
        soup = BeautifulSoup(html, "html.parser")
        teaser_divs = soup.find_all("div", class_="teaser-subject")
        
        for div in teaser_divs:
            try:
                # Name
                name_elem = div.find("p", {"data-test": "subject-name"})
                if not name_elem:
                    name_elem = div.find("img", class_="image-content")
                    name = name_elem.get("alt") if name_elem else None
                else:
                    name = name_elem.get_text(strip=True)
                
                # Slug
                link_elem = div.find("a", class_="teaser__link")
                if link_elem and link_elem.get("href"):
                    href = link_elem.get("href")
                    # href is usually "/slug/feed"
                    slug = href.strip("/").split("/")[0]
                else:
                    slug = None
                
                # Image
                img_elem = div.find("img", class_="image-content")
                image_url = img_elem.get("src") if img_elem else ""
                
                if name and slug:
                    performers.append(Performer(
                        name=name,
                        slug=slug,
                        image_url=image_url,
                        source=self.site_name
                    ))
            except Exception as e:
                continue
                
        return performers

    def _extract_from_regex(self, html: str) -> List[Performer]:
        performers = []
        # Updated regex for performer names and slugs
        name_slug_pattern = re.compile(r'href="/([^/]+)/feed"[^>]*data-test="subject-name"[^>]*title="\s*([^"]+)"')
        matches = name_slug_pattern.findall(html)

        if not matches:
             # Try another pattern
             name_slug_pattern = re.compile(r'href="/([^/]+)/feed".*?alt="([^"]+)"')
             matches = name_slug_pattern.findall(html)

        for slug, name in matches:
            if name and slug:
                performers.append(Performer(
                    name=name.strip(),
                    slug=slug,
                    image_url="", 
                    source=self.site_name
                ))
        return performers
