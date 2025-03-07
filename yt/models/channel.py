from dataclasses import dataclass
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from models.thumbnail import Thumbnail
    from models.channel import Channel

@dataclass
class Channel: 
    id: str
    link: str
    name: str
    thumbnails: List["Thumbnail"]
    
    def __todict__(self):
        return {
            "id": self.id,
            "link": self.link,
            "name": self.name,
            "thumbnails": [t.__todict__() for t in self.thumbnails]
        }
    
    @classmethod
    def parse_channel(cls, channel_dict: dict) -> "Channel":
        from models.thumbnail import Thumbnail
        
        thumbnails = [Thumbnail.parse_thumbnail(t) for t in channel_dict.get('thumbnails', [])]
        return Channel(
            id=channel_dict['id'],
            link=channel_dict['link'],
            name=channel_dict['name'],
            thumbnails=thumbnails
        )