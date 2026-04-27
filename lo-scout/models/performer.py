"""
Performer data model for lo-scout application.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import re


@dataclass
class Performer:
    """Data class representing an adult performer."""
    
    name: str  # Required: Performer name
    slug: str  # Required: URL-friendly identifier
    image_url: str = ""  # Thumbnail image URL (can be empty)
    height: Optional[int] = None  # Height in cm
    weight: Optional[int] = None  # Weight in kg
    gender: str = "female"  # "female" or "male"
    source: str = "freeones"  # Source website identifier
    
    def __post_init__(self):
        """Validate required fields after initialization."""
        if not self.name or not self.name.strip():
            raise ValueError("Performer name is required")
        if not self.slug or not self.slug.strip():
            raise ValueError("Performer slug is required")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert performer to dictionary."""
        return {
            "name": self.name,
            "slug": self.slug,
            "image_url": self.image_url,
            "height": self.height,
            "weight": self.weight,
            "gender": self.gender,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Performer":
        """Create Performer from dictionary."""
        return cls(
            name=data.get("name", ""),
            slug=data.get("slug", ""),
            image_url=data.get("image_url", ""),
            height=data.get("height"),
            weight=data.get("weight"),
            gender=data.get("gender", "female"),
            source=data.get("source", "freeones")
        )
    
    def get_external_search_urls(self, external_sites: list) -> Dict[str, str]:
        """
        Generate search URLs for external sites.
        
        Args:
            external_sites: List of site configs with 'name', 'pattern', 'icon'
        
        Returns:
            Dictionary mapping site name to search URL
        """
        # URL-encode the performer name for search queries
        query = self.name.replace(" ", "+")
        
        urls = {}
        for site in external_sites:
            pattern = site["pattern"]
            url = pattern.format(query=query)
            urls[site["name"]] = url
        
        return urls
    
    @property
    def has_image(self) -> bool:
        """Check if performer has a valid image URL."""
        if not self.image_url:
            return False
        
        # Basic URL validation
        return self.image_url.startswith(("http://", "https://"))
    
    @property
    def height_cm(self) -> Optional[int]:
        """Get height in centimeters."""
        return self.height
    
    @property
    def weight_kg(self) -> Optional[int]:
        """Get weight in kilograms."""
        return self.weight
    
    def __str__(self) -> str:
        """String representation of performer."""
        return f"Performer(name='{self.name}', slug='{self.slug}')"