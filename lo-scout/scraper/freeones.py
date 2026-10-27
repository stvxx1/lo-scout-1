import re
from urllib.parse import urlencode, urljoin
from typing import List

from bs4 import BeautifulSoup

from scraper.base import BaseScraper
from models.performer import Performer
from models.filters import FilterConfig
from thumbnails import pick_largest_srcset


def best_image_url(img_elem) -> str:
    """Return the best portrait URL available on a listing card.

    ``src`` normally holds the real signed CDN URL, but lazy-loaded markup
    sometimes leaves a placeholder there and defers the real URL to
    ``data-src``/``srcset``; checking them in order keeps the grid populated
    if Freeones changes the markup.
    """
    if not img_elem:
        return ""
    for attr in ("src", "data-src", "data-original"):
        value = (img_elem.get(attr) or "").strip()
        if value and not value.startswith("data:"):
            return value
    srcset = img_elem.get("srcset") or img_elem.get("data-srcset") or ""
    return pick_largest_srcset(srcset)


class FreeonesScraper(BaseScraper):
    site_name: str = "freeones"
    base_url: str = "https://www.freeones.com"

    def __init__(self, timeout: int = 30, max_retries: int = 3, retry_delay: float = 2.0):
        super().__init__(timeout=timeout, max_retries=max_retries, retry_delay=retry_delay)

    def build_search_url(self, filters: FilterConfig, page: int) -> str:
        """Build a listing URL that stays inside freeones.com/robots.txt.

        robots.txt disallows ``*s=``, ``*o=``, ``*l=`` and ``*p=1$``, so the URL
        carries the filters only, plus ``p`` from page 2 onward. Nothing is
        lost: the default listing order is already rank ascending (verified --
        the default page returns the same name sequence as
        ``s=rank.currentRank&o=asc``), and the default page size matches
        ITEMS_PER_PAGE.
        """
        params = filters.to_url_params()
        if page > 1:
            params["p"] = page
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
                image_url = best_image_url(img_elem)
                
                if name and slug:
                    performers.append(Performer(
                        name=name,
                        slug=slug,
                        image_url=image_url,
                        source=self.site_name
                    ))
            except Exception:
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
