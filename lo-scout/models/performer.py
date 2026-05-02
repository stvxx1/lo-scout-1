from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class Performer:
    name: str
    slug: str
    image_url: str = ""
    height: Optional[int] = None
    weight: Optional[int] = None
    gender: str = ""
    source: str = ""

    def __post_init__(self):
        if not self.name or not self.slug:
            raise ValueError("Performer name and slug are required.")
        if self.gender and self.gender not in ["female", "male"]:
            raise ValueError("Gender must be 'female' or 'male'.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "slug": self.slug,
            "image_url": self.image_url,
            "height": self.height,
            "weight": self.weight,
            "gender": self.gender,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)

    def get_external_search_urls(self, external_sites: list) -> Dict[str, str]:
        urls = {}
        for site in external_sites:
            query = self.name.replace(" ", "+")  # Basic URL-encoding
            urls[site["name"]] = site["pattern"].format(query=query)
        return urls
