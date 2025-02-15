from dataclasses import dataclass

@dataclass
class Thumbnail:
    height: int
    url: str
    width: int
    
    def __todict__(self):
        return {
            "height": self.height,
            "url": self.url,
            "width": self.width
        }
    
    @classmethod
    def parse_thumbnail(cls, thumbnail_dict: dict) -> "Thumbnail":
        return Thumbnail(**thumbnail_dict)