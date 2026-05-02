from dataclasses import dataclass, field
from typing import Optional, Dict, Any

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
        params = {"gender": self.gender}
        if self.min_height is not None: params["height_min"] = self.min_height
        if self.max_height is not None: params["height_max"] = self.max_height
        if self.min_weight is not None: params["weight_min"] = self.min_weight
        if self.max_weight is not None: params["weight_max"] = self.max_weight
        if self.gender == "males":
            if self.min_dick_length is not None: params["dick_length_min"] = self.min_dick_length
            if self.max_dick_length is not None: params["dick_length_max"] = self.max_dick_length
        return params

    @classmethod
    def from_streamlit_state(cls, session_state: Dict[str, Any]):
        return cls(
            gender=session_state.get("gender", "babes"),
            min_height=session_state.get("min_height"),
            max_height=session_state.get("max_height"),
            min_weight=session_state.get("min_weight"),
            max_weight=session_state.get("max_weight"),
            min_dick_length=session_state.get("min_dick_length"),
            max_dick_length=session_state.get("max_dick_length"),
        )
