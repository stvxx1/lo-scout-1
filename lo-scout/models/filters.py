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
    min_age: Optional[int] = None  # Minimum age
    max_age: Optional[int] = None  # Maximum age
    piercings: Optional[str] = None  # "yes", "no", or None
    tattoos: Optional[str] = None  # "yes", "no", or None
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
        Convert filter configuration to URL query parameters using the new site structure.
        
        Returns:
            Dictionary of URL query parameters
        """
        params = {
            "q": "",
            "filter_mode[global]": "and"
        }
        
        # Performer Type (Gender)
        p_type = "babe" if self.gender == "babes" else "male"
        params["f[performerType]"] = p_type
        params["filter_mode[performerType]"] = "and"
        
        # Age Range
        if self.min_age is not None or self.max_age is not None:
            min_a = self.min_age if self.min_age is not None else 18
            max_a = self.max_age if self.max_age is not None else 99
            params["r[age]"] = f"{min_a},{max_a}"
        
        # Height Range
        if self.min_height is not None or self.max_height is not None:
            min_h = self.min_height if self.min_height is not None else 0
            max_h = self.max_height if self.max_height is not None else 300
            params["r[appearance.metric.height]"] = f"{min_h},{max_h}"
        
        # Weight Range
        if self.min_weight is not None or self.max_weight is not None:
            min_w = self.min_weight if self.min_weight is not None else 0
            max_w = self.max_weight if self.max_weight is not None else 500
            params["r[appearance.metric.weight]"] = f"{min_w},{max_w}"
        
        # Piercings
        if self.piercings:
            params["f[piercings]"] = self.piercings
            params["filter_mode[piercings]"] = "and"
            
        # Tattoos
        if self.tattoos:
            params["f[tattoos]"] = self.tattoos
            params["filter_mode[tattoos]"] = "and"
        
        # Dick length (males only) - using old params if still supported, 
        # or we might need to find the new r[...] equivalent if it fails.
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