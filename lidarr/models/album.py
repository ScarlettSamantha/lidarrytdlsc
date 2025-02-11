from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

from models.artist import Artist
from models.image import Image
from models.link import Link
from models.media import Media
from models.rating import Rating
from models.release import Release
from models.statistics import Statistics

from helper import parse_datetime

@dataclass
class Album:
    albumType: str
    anyReleaseOk: bool
    artist: Artist
    artistId: int
    disambiguation: str
    duration: int
    foreignAlbumId: str
    genres: List[str]
    id: int
    images: List[Image]
    links: List[Link]
    media: List[Media]
    mediumCount: int
    monitored: bool
    overview: str
    profileId: int
    ratings: Rating
    releaseDate: Optional[datetime]
    releases: List[Release]
    secondaryTypes: List[str]
    statistics: Statistics
    title: str

    @classmethod
    def from_dict(cls, data: dict) -> 'Album':
        return cls(
            albumType=data.get('albumType', ''),
            anyReleaseOk=data.get('anyReleaseOk', False),
            artist=Artist.from_dict(data.get('artist', {})),
            artistId=data.get('artistId', 0),
            disambiguation=data.get('disambiguation', ''),
            duration=data.get('duration', 0),
            foreignAlbumId=data.get('foreignAlbumId', ''),
            genres=data.get('genres', []),
            id=data.get('id', 0),
            images=[Image.from_dict(img) for img in data.get('images', [])],
            links=[Link.from_dict(link) for link in data.get('links', [])],
            media=[Media.from_dict(m) for m in data.get('media', [])],
            mediumCount=data.get('mediumCount', 0),
            monitored=data.get('monitored', False),
            overview=data.get('overview', ''),
            profileId=data.get('profileId', 0),
            ratings=Rating.from_dict(data.get('ratings', {})),
            releaseDate=parse_datetime(data.get('releaseDate')),
            releases=[Release.from_dict(rel) for rel in data.get('releases', [])],
            secondaryTypes=data.get('secondaryTypes', []),
            statistics=Statistics.from_dict(data.get('statistics', {})),
            title=data.get('title', '')
        )
    
    def __repr__(self) -> str:
        return (f"Album(id={self.id}, title={self.title!r}, "
                f"artist={self.artist.artistName!r}, releaseDate={self.releaseDate}, "
                f"foreignAlbumId={self.foreignAlbumId!r})")
