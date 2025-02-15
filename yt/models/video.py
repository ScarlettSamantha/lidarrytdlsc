from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List, Optional, Dict, Any

if TYPE_CHECKING:
        from models.accessibility import Accessibility
        from models.channel import Channel
        from models.description_snippit_part import DescriptionSnippetPart
        from models.thumbnail import Thumbnail
        from models.viewcount import ViewCount

@dataclass
class VideoData:
    accessibility: "Accessibility"
    channel: "Channel"
    descriptionSnippet: List["DescriptionSnippetPart"]
    duration: str
    id: str
    link: str
    publishedTime: Optional[str]
    richThumbnail: Optional["Thumbnail"]
    shelfTitle: Optional[str]
    thumbnails: List["Thumbnail"]
    title: str
    type: str
    viewCount: "ViewCount"
    
    def __repr__(self) -> str:
        desc_count = len(self.descriptionSnippet)
        thumbs_count = len(self.thumbnails)
        return (
            f"{self.__class__.__name__}("
            f"id={self.id!r}, title={self.title!r}, duration={self.duration!r}, "
            f"publishedTime={self.publishedTime!r}, type={self.type!r}, "
            f"viewCount={self.viewCount!r}, channel={self.channel!r}, "
            f"descriptionSnippet_count={desc_count}, thumbnails_count={thumbs_count}, "
            f"richThumbnail={self.richThumbnail!r}, shelfTitle={self.shelfTitle!r}"
            f")"
        )
        
    def __todict__(self) -> Dict[str, Any]:
        return {
            "accessibility": self.accessibility.__todict__(),
            "channel": self.channel.__todict__(),
            'descriptionSnippet': [part.__todict__() for part in self.descriptionSnippet],
            'duration':self.duration,
            'id':self.id,
            'link':self.link,
            'publishedTime':self.publishedTime,
            'richThumbnail':self.richThumbnail,
            'shelfTitle':self.shelfTitle,
            'thumbnails':[thumb.__todict__() for thumb in self.thumbnails],
            'title':self.title,
            'type':':self.type',
            'viewCount':self.viewCount.__todict__()
        }
    
    @classmethod
    def parse_video_data(cls, data: dict) -> "VideoData":
        # Local imports to avoid circular dependencies at module level   
        from models.accessibility import Accessibility
        from models.channel import Channel
        from models.thumbnail import Thumbnail
        from models.description_snippit_part import DescriptionSnippetPart
        from models.viewcount import ViewCount
             
        accessibility = Accessibility(**data['accessibility'])
        channel = Channel.parse_channel(data['channel'])
        description_snippet = DescriptionSnippetPart.parse_description_snippet(data['descriptionSnippet'] if data['descriptionSnippet'] is not None else [])
        thumbnails = [Thumbnail.parse_thumbnail(t) for t in data.get('thumbnails', [])]
        view_count = ViewCount(**data['viewCount'])
        
        return cls(
            accessibility=accessibility,
            channel=channel,
            descriptionSnippet=description_snippet,
            duration=data['duration'],
            id=data['id'],
            link=data['link'],
            publishedTime=data.get('publishedTime'),
            richThumbnail=data.get('richThumbnail'),
            shelfTitle=data.get('shelfTitle'),
            thumbnails=thumbnails,
            title=data['title'],
            type=data['type'],
            viewCount=view_count
        )
