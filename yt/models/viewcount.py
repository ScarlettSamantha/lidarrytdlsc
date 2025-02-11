from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ViewCount:
    short: str
    text: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ViewCount":
        """
        Create a ViewCount instance from a dictionary.
        Uses default empty strings if 'short' or 'text' keys are missing.
        """
        return cls(
            short=data.get("short", ""),
            text=data.get("text", "")
        )

    @classmethod
    def from_dict_list(cls, data_list: List[Dict[str, Any]]) -> List["ViewCount"]:
        """
        Parse a list of dictionaries to create a list of ViewCount instances.
        """
        return [cls.from_dict(item) for item in data_list]