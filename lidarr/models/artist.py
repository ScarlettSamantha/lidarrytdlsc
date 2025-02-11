from dataclasses import dataclass
from typing import List, Optional, Any
from datetime import datetime
from models.image import Image
from models.link import Link
from models.rating import Rating
from helper import parse_datetime

@dataclass
class Artist:
    added: Optional[datetime]
    artistName: str
    artistType: str
    cleanName: str
    disambiguation: str
    discogsId: int
    ended: bool
    foreignArtistId: str
    genres: List[str]
    id: int
    images: List[Image]
    lastAlbum: Optional[Any]
    links: List[Link]
    metadataProfileId: int
    monitorNewItems: str
    monitored: bool
    nextAlbum: Optional[Any]
    overview: str
    path: str
    qualityProfileId: int
    ratings: Rating
    sortName: str
    status: str
    tadbId: int
    tags: List[Any]

    @classmethod
    def from_dict(cls, data: dict) -> 'Artist':
        return cls(
            added=parse_datetime(data.get('added')),
            artistName=data.get('artistName', ''),
            artistType=data.get('artistType', ''),
            cleanName=data.get('cleanName', ''),
            disambiguation=data.get('disambiguation', ''),
            discogsId=data.get('discogsId', 0),
            ended=data.get('ended', False),
            foreignArtistId=data.get('foreignArtistId', ''),
            genres=data.get('genres', []),
            id=data.get('id', 0),
            images=[Image.from_dict(img) for img in data.get('images', [])],
            lastAlbum=data.get('lastAlbum'),
            links=[Link.from_dict(link) for link in data.get('links', [])],
            metadataProfileId=data.get('metadataProfileId', 0),
            monitorNewItems=data.get('monitorNewItems', ''),
            monitored=data.get('monitored', False),
            nextAlbum=data.get('nextAlbum'),
            overview=data.get('overview', ''),
            path=data.get('path', ''),
            qualityProfileId=data.get('qualityProfileId', 0),
            ratings=Rating.from_dict(data.get('ratings', {})),
            sortName=data.get('sortName', ''),
            status=data.get('status', ''),
            tadbId=data.get('tadbId', 0),
            tags=data.get('tags', [])
        )
    
    def __repr__(self) -> str:
        return (f"Artist(id={self.id}, artistName={self.artistName!r}, "
                f"discogsId={self.discogsId})")