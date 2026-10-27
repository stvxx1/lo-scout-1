from dataclasses import dataclass
from typing import Optional, Dict, Any

from links import build_search_urls

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
        """Return ``{site_name: search_url}`` for the configured tube sites.

        Encoding lives in :mod:`links` because each site expects a different
        one, and a naive ``name.replace(" ", "+")`` corrupts names that contain
        ``&``, ``'`` or ``#``.
        """
        return build_search_urls(external_sites, self.name)
