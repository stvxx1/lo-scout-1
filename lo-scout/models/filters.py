from dataclasses import dataclass
from typing import Optional, Dict, Any

# Freeones expresses numeric filters as inclusive ranges on the facet name, e.g.
#   r[appearance.metric.height]=195,215
# Facet name -> (min field, max field, floor, ceiling, males_only).
# Floor is the domain minimum, not 0: a 0 lower bound also matches profiles with
# no recorded value, which floods max-only filters with unrelated results.
RANGE_FACETS = {
    "appearance.metric.height": ("min_height", "max_height", 100, 300, False),
    "appearance.metric.weight": ("min_weight", "max_weight", 30, 500, False),
    "appearance.metric.penisLength": ("min_dick_length", "max_dick_length", 1, 50, True),
}

@dataclass
class FilterConfig:
    gender: str = "babes"
    min_height: Optional[int] = None
    max_height: Optional[int] = None
    min_weight: Optional[int] = None
    max_weight: Optional[int] = None
    min_dick_length: Optional[int] = None
    max_dick_length: Optional[int] = None

    def __post_init__(self):
        if self.gender not in ["babes", "males"]:
            raise ValueError("Gender must be \"babes\" or \"males\".")

        if self.min_height is not None and self.max_height is not None and self.min_height > self.max_height:
            raise ValueError("min_height cannot be greater than max_height.")
        if self.min_weight is not None and self.max_weight is not None and self.min_weight > self.max_weight:
            raise ValueError("min_weight cannot be greater than max_weight.")
        if self.min_dick_length is not None and self.max_dick_length is not None and self.min_dick_length > self.max_dick_length:
            raise ValueError("min_dick_length cannot be greater than max_dick_length.")

    def to_url_params(self) -> Dict[str, Any]:
        # Maps babes to babe and males to male for the new f[performerType] parameter
        performer_type = "babe" if self.gender == "babes" else "male"
        params = {
            "f[performerType]": performer_type,
            "filter_mode[performerType]": "and"
        }
        
        for facet, (min_field, max_field, floor, ceiling, males_only) in RANGE_FACETS.items():
            if males_only and self.gender != "males":
                continue

            low = getattr(self, min_field)
            high = getattr(self, max_field)

            # An open-ended range is sent as the full extent of the facet.
            low = floor if low is None else low
            high = ceiling if high is None else high

            if (low, high) == (floor, ceiling):
                continue

            params[f"r[{facet}]"] = f"{low},{high}"
        
        return params

    def has_filters(self) -> bool:
        """Check if any filters other than gender are active."""
        return any([
            self.min_height is not None,
            self.max_height is not None,
            self.min_weight is not None,
            self.max_weight is not None,
            self.min_dick_length is not None,
            self.max_dick_length is not None
        ])


