import json
import re
from urllib.parse import urlencode, urljoin
from typing import List, Dict, Any, Optional

from bs4 import BeautifulSoup

from scraper.base import BaseScraper, ScraperError
from models.performer import Performer
from models.filters import FilterConfig
from config import ITEMS_PER_PAGE

class FreeonesScraper(BaseScraper):
    site_name: str = "freeones"
    base_url: str = "https://www.freeones.com"

    def __init__(self, timeout: int = 30, max_retries: int = 3, retry_delay: float = 2.0):
        super().__init__(timeout=timeout, max_retries=max_retries, retry_delay=retry_delay)
        self.performer_url_base = urljoin(self.base_url, "/html/{slug}.html")

    def build_search_url(self, filters: FilterConfig, page: int) -> str:
        params = filters.to_url_params()
        params["s"] = "rank.currentRank"
        params["o"] = "desc"
        params["page"] = page
        params["l"] = ITEMS_PER_PAGE
        query_string = urlencode({k: v for k, v in params.items() if v is not None})
        return f"{urljoin(self.base_url, '/performers')}?{query_string}"

    def fetch_performers(self, page: int, filters: FilterConfig) -> List[Performer]:
        url = self.build_search_url(filters, page)
        html_content = self.fetch_page(url)
        return self.parse_performers(html_content)

    def parse_performers(self, html: str) -> List[Performer]:
        performers = []
        data = self._extract_from_json(html)
        if data:
            performers.extend(self._parse_json_data(data))
        
        if not performers:
            # Fallback to BeautifulSoup if JSON extraction fails or yields no performers
            performers.extend(self._extract_from_bs4(html))

        if not performers:
            # Last resort: regex
            performers.extend(self._extract_from_regex(html))

        return performers

    def _extract_from_json(self, html: str) -> Optional[Dict[str, Any]]:
        # Attempt to extract __NEXT_DATA__ JSON block
        match = re.search(r"<script id=\"__NEXT_DATA__\" type=\"application/json\">(.*?)</script>", html)
        if match:
            try:
                json_data = json.loads(match.group(1))
                return json_data
            except json.JSONDecodeError as e:
                self.handle_error("Failed to decode __NEXT_DATA__ JSON", e)
        return None

    def _parse_json_data(self, data: Dict[str, Any]) -> List[Performer]:
        performers = []
        try:
            # Navigate to the relevant data structure
            props = data.get("props", {}).get("pageProps", {})
            search_results = props.get("search", {}).get("results", []) \
                             or props.get("performers", {}).get("results", [])

            for item in search_results:
                name = item.get("name")
                slug = item.get("slug")
                image_data = item.get("image", {})
                image_url = image_data.get("src") or image_data.get("url") or ""
                gender = item.get("gender", "").lower()
                
                measurements_data = item.get("measurements", {})
                height = measurements_data.get("height", {}).get("cm")
                weight = measurements_data.get("weight", {}).get("kg")
                
                # Additional metadata
                age = item.get("age")
                ethnicity = item.get("ethnicity")
                hair_color = item.get("hair", {}).get("color") if item.get("hair") else None
                eye_color = item.get("eyes", {}).get("color") if item.get("eyes") else None
                
                # Bra/Cup size
                bra_size = measurements_data.get("braSize")
                cup_size = measurements_data.get("cupSize")
                measurements_str = f"{bra_size}{cup_size}" if bra_size and cup_size else None

                # Basic image URL validation
                if image_url and not (image_url.startswith("http") or image_url.startswith("//")):
                    image_url = ""

                if name and slug:
                    performers.append(Performer(
                        name=name,
                        slug=slug,
                        image_url=image_url,
                        height=height,
                        weight=weight,
                        gender=gender,
                        source=self.site_name,
                        age=age,
                        ethnicity=ethnicity,
                        measurements=measurements_str,
                        hair_color=hair_color,
                        eye_color=eye_color
                    ))
        except Exception as e:
            self.handle_error(f"Error parsing JSON data: {e}", e)
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
