import json
import re
from urllib.parse import urlencode, urljoin
from typing import List, Dict, Any, Optional

from bs4 import BeautifulSoup

from lo_scout.scraper.base import BaseScraper, ScraperError
from lo_scout.models.performer import Performer
from lo_scout.models.filters import FilterConfig

class FreeonesScraper(BaseScraper):
    site_name: str = "freeones"
    base_url: str = "https://www.freeones.com"

    def __init__(self):
        super().__init__()
        self.performer_url_base = urljoin(self.base_url, "/html/{slug}.html")

    def build_search_url(self, filters: FilterConfig, page: int) -> str:
        params = filters.to_url_params()
        params["s"] = "rank.currentRank"
        params["o"] = "desc"
        params["page"] = page
        return f"{urljoin(self.base_url, "/performers")}?{urlencode(params)}"

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
            # Fallback to regex if JSON extraction fails or yields no performers
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
            # Navigate to the relevant data structure, adjust as per actual Freeones JSON structure
            props = data.get("props", {}).get("pageProps", {})
            search_results = props.get("search", {}).get("results", []) \
                             or props.get("performers", {}).get("results", [])

            for item in search_results:
                name = item.get("name")
                slug = item.get("slug")
                image_url = item.get("image", {}).get("src") if item.get("image") else ""
                gender = item.get("gender", "").lower()
                height = item.get("measurements", {}).get("height", {}).get("cm")
                weight = item.get("measurements", {}).get("weight", {}).get("kg")

                # Basic image URL validation
                if image_url and not (image_url.startswith("http") or image_url.startswith("//")):
                    image_url = "" # Invalidate relative or malformed URLs for now

                if name and slug:
                    performers.append(Performer(
                        name=name,
                        slug=slug,
                        image_url=image_url,
                        height=height,
                        weight=weight,
                        gender=gender,
                        source=self.site_name
                    ))
        except KeyError as e:
            self.handle_error(f"Unexpected JSON structure in _parse_json_data: {e}", e)
        except Exception as e:
            self.handle_error(f"Error parsing JSON data: {e}", e)
        return performers

    def _extract_from_regex(self, html: str) -> List[Performer]:
        performers = []
        # Fallback regex for performer names and slugs. This is less reliable for images and other data.
        # This regex looks for links to performer profiles
        name_slug_pattern = re.compile(r'<a\s+[^>]*href="/performers/([^/]+)"[^>]*>\s*([^<]+?)\s*</a>')
        matches = name_slug_pattern.findall(html)

        for slug, name in matches:
            # Clean up name if necessary
            name = BeautifulSoup(name, "html.parser").get_text(strip=True)
            if name and slug:
                performers.append(Performer(
                    name=name,
                    slug=slug,
                    image_url="", # Regex fallback doesn't reliably get images
                    source=self.site_name
                ))
        return performers
