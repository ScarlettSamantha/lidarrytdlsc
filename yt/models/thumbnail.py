from dataclasses import dataclass

@dataclass
class Thumbnail:
    height: int
    url: str
    width: int
    
    @classmethod
    def parse_thumbnail(cls, thumbnail_dict: dict) -> "Thumbnail":
        return Thumbnail(**thumbnail_dict)