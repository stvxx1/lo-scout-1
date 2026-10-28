from dataclasses import dataclass
from typing import Optional, Dict, Any

from config import ETHNICITY_OPTIONS, PIERCING_OPTIONS, TATTOO_OPTIONS

# Freeones expresses numeric filters as inclusive ranges on the facet name, e.g.
#   r[appearance.metric.height]=195,215
# Facet name -> (min field, max field, floor, ceiling, males_only).
# Floor is the domain minimum, not 0: a 0 lower bound also matches profiles with
# no recorded value, which floods max-only filters with unrelated results.
RANGE_FACETS = {
    "age": ("min_age", "max_age", 18, 99, False),
    "appearance.metric.height": ("min_height", "max_height", 100, 300, False),
    "appearance.metric.weight": ("min_weight", "max_weight", 30, 500, False),
    "appearance.metric.penisLength": ("min_dick_length", "max_dick_length", 1, 50, True),
}

# Facets that take a slug instead of a range, e.g. f[ethnicity]=caucasian.
# Facet name -> (field, allowed slugs).
#
# One value per facet, deliberately: a comma list is read as a single unknown
# value and returns nothing, bracketed arrays return nothing, and repeating the
# key keeps only the last occurrence -- so a multi-select would need UI that
# promises more than the URL can carry.
SELECT_FACETS = {
    "ethnicity": ("ethnicity", ETHNICITY_OPTIONS),
    "tattoos": ("tattoos", TATTOO_OPTIONS),
    "piercings": ("piercings", PIERCING_OPTIONS),
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
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    ethnicity: Optional[str] = None
    tattoos: Optional[str] = None
    piercings: Optional[str] = None

    def __post_init__(self):
        if self.gender not in ["babes", "males"]:
            raise ValueError("Gender must be \"babes\" or \"males\".")

        if self.min_height is not None and self.max_height is not None and self.min_height > self.max_height:
            raise ValueError("min_height cannot be greater than max_height.")
        if self.min_weight is not None and self.max_weight is not None and self.min_weight > self.max_weight:
            raise ValueError("min_weight cannot be greater than max_weight.")
        if self.min_dick_length is not None and self.max_dick_length is not None and self.min_dick_length > self.max_dick_length:
            raise ValueError("min_dick_length cannot be greater than max_dick_length.")
        if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
            raise ValueError("min_age cannot be greater than max_age.")

        # Reject unknown slugs here rather than at the site: freeones answers an
        # unknown value with an empty page, so a typo would reach the user as
        # "no performers match these filters" instead of as an error.
        for field, options in SELECT_FACETS.values():
            value = getattr(self, field)
            if value is not None and value not in options:
                raise ValueError(f"{field} must be one of {sorted(options)}, got {value!r}.")

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

        for facet, (field, _options) in SELECT_FACETS.items():
            value = getattr(self, field)
            if value:
                params[f"f[{facet}]"] = value

        return params

    def has_filters(self) -> bool:
        """Check if any filters other than gender are active."""
        return any([
            self.min_height is not None,
            self.max_height is not None,
            self.min_weight is not None,
            self.max_weight is not None,
            self.min_dick_length is not None,
            self.max_dick_length is not None,
            self.min_age is not None,
            self.max_age is not None,
            self.ethnicity is not None,
            self.tattoos is not None,
            self.piercings is not None
        ])


