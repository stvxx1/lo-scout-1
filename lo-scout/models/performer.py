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
    age: Optional[int] = None
    ethnicity: Optional[str] = None
    measurements: Optional[str] = None
    hair_color: Optional[str] = None
    eye_color: Optional[str] = None

    def __post_init__(self):
        if not self.name or not self.slug:
            raise ValueError("Performer name and slug are required.")
        # Normalize gender if it exists
        if self.gender:
            self.gender = self.gender.lower()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "slug": self.slug,
            "image_url": self.image_url,
            "height": self.height,
            "weight": self.weight,
            "gender": self.gender,
            "source": self.source,
            "age": self.age,
            "ethnicity": self.ethnicity,
            "measurements": self.measurements,
            "hair_color": self.hair_color,
            "eye_color": self.eye_color
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
