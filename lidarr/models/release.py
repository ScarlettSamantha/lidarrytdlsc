from dataclasses import dataclass
from typing import List, TYPE_CHECKING
from models.media import Media

@dataclass
class Release:
    albumId: int
    country: List[str]
    disambiguation: str
    duration: int
    foreignReleaseId: str
    format: str
    id: int
    label: List[str]
    media: List[Media]
    mediumCount: int
    monitored: bool
    status: str
    title: str
    trackCount: int

    @classmethod
    def from_dict(cls, data: dict) -> 'Release':
        return cls(
            albumId=data.get('albumId', 0),
            country=data.get('country', []),
            disambiguation=data.get('disambiguation', ''),
            duration=data.get('duration', 0),
            foreignReleaseId=data.get('foreignReleaseId', ''),
            format=data.get('format', ''),
            id=data.get('id', 0),
            label=data.get('label', []),
            media=[Media.from_dict(m) for m in data.get('media', [])],
            mediumCount=data.get('mediumCount', 0),
            monitored=data.get('monitored', False),
            status=data.get('status', ''),
            title=data.get('title', ''),
            trackCount=data.get('trackCount', 0)
        )
    
    def __repr__(self) -> str:
        return (f"Release(id={self.id}, title={self.title!r}, "
                f"format={self.format!r}, trackCount={self.trackCount})")

