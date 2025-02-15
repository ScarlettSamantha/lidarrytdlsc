from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class Accessibility:
    duration: str
    title: str

    def __todict__(self):
        return {
            "duration": self.duration,
            "title": self.title
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Accessibility":
        """
        Create an Accessibility instance from a dictionary.
        If the keys 'duration' or 'title' are missing, default to an empty string.
        """
        return cls(
            duration=data.get("duration", ""),
            title=data.get("title", "")
        )

    @classmethod
    def from_dict_list(cls, data_list: List[Dict[str, Any]]) -> List["Accessibility"]:
        """
        Parse a list of dictionaries to create a list of Accessibility instances.
        """
        return [cls.from_dict(item) for item in data_list]