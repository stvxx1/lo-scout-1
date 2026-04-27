"""
Filter configuration model for lo-scout application.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class FilterConfig:
    """Configuration for filtering performer searches on freeones.com."""
    
    gender: str = "babes"  # "babes" or "males" - determines freeones URL
    min_height: Optional[int] = None  # Minimum height in cm
    max_height: Optional[int] = None  # Maximum height in cm
    min_weight: Optional[int] = None  # Minimum weight in kg
    max_weight: Optional[int] = None  # Maximum weight in kg
    min_dick_length: Optional[int] = None  # Minimum dick length in cm (males only)
    max_dick_length: Optional[int] = None  # Maximum dick length in cm (males only)
    
    def __post_init__(self):
        """Validate filter configuration."""
        # Validate gender
        if self.gender not in ["babes", "males"]:
            raise ValueError("Gender must be 'babes' or 'males'")
        
        # Validate height range
        if (self.min_height is not None and self.max_height is not None and 
            self.min_height > self.max_height):
            raise ValueError("Minimum height cannot be greater than maximum height")
        
        # Validate weight range
        if (self.min_weight is not None and self.max_weight is not None and 
            self.min_weight > self.max_weight):
            raise ValueError("Minimum weight cannot be greater than maximum weight")
        
        # Validate dick length range (males only)
        if self.gender == "males":
            if (self.min_dick_length is not None and self.max_dick_length is not None and 
                self.min_dick_length > self.max_dick_length):
                raise ValueError("Minimum dick length cannot be greater than maximum dick length")
        else:
            # Reset dick length for females
            self.min_dick_length = None
            self.max_dick_length = None
    
    def to_url_params(self) -> Dict[str, str]:
        """
        Convert filter configuration to URL query parameters.
        
        Returns:
            Dictionary of URL query parameters
        """
        params = {
            "s": "rank.currentRank",
            "o": "desc",
            "gender": self.gender
        }
        
        # Add height filters
        if self.min_height is not None:
            params["height_min"] = str(self.min_height)
        if self.max_height is not None:
            params["height_max"] = str(self.max_height)
        
        # Add weight filters
        if self.min_weight is not None:
            params["weight_min"] = str(self.min_weight)
        if self.max_weight is not None:
            params["weight_max"] = str(self.max_weight)
        
        # Add dick length filters (males only)
        if self.gender == "males":
            if self.min_dick_length is not None:
                params["dick_min"] = str(self.min_dick_length)
            if self.max_dick_length is not None:
                params["dick_max"] = str(self.max_dick_length)
        
        return params
    
    def build_url(self, base_url: str = "https://www.freeones.com/performers") -> str:
        """
        Build complete freeones search URL with filters.
        
        Args:
            base_url: Base URL for freeones performers page
        
        Returns:
            Complete URL with query parameters
        """
        from urllib.parse import urlencode
        
        params = self.to_url_params()
        query_string = urlencode(params)
        
        return f"{base_url}?{query_string}"
    
    @classmethod
    def from_streamlit_state(cls, prefix: str = "filter") -> "FilterConfig":
        """
        Create FilterConfig from Streamlit session state.
        
        Args:
            prefix: Prefix for session state keys
        
        Returns:
            FilterConfig instance
        """
        import streamlit as st
        
        def get_state(key: str) -> Any:
            return st.session_state.get(f"{prefix}_{key}")
        
        return cls(
            gender=get_state("gender") or "babes",
            min_height=get_state("min_height"),
            max_height=get_state("max_height"),
            min_weight=get_state("min_weight"),
            max_weight=get_state("max_weight"),
            min_dick_length=get_state("min_dick_length"),
            max_dick_length=get_state("max_dick_length")
        )
    
    def has_filters(self) -> bool:
        """Check if any filters are applied beyond default gender."""
        return any([
            self.min_height is not None,
            self.max_height is not None,
            self.min_weight is not None,
            self.max_weight is not None,
            self.min_dick_length is not None,
            self.max_dick_length is not None
        ])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert filter config to dictionary."""
        return {
            "gender": self.gender,
            "min_height": self.min_height,
            "max_height": self.max_height,
            "min_weight": self.min_weight,
            "max_weight": self.max_weight,
            "min_dick_length": self.min_dick_length,
            "max_dick_length": self.max_dick_length
        }
    
    def __str__(self) -> str:
        """String representation of filter config."""
        parts = [f"gender={self.gender}"]
        if self.min_height is not None:
            parts.append(f"height>={self.min_height}cm")
        if self.max_height is not None:
            parts.append(f"height<={self.max_height}cm")
        if self.min_weight is not None:
            parts.append(f"weight>={self.min_weight}kg")
        if self.max_weight is not None:
            parts.append(f"weight<={self.max_weight}kg")
        if self.gender == "males":
            if self.min_dick_length is not None:
                parts.append(f"dick>={self.min_dick_length}cm")
            if self.max_dick_length is not None:
                parts.append(f"dick<={self.max_dick_length}cm")
        return f"FilterConfig({', '.join(parts)})"