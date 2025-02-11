from dataclasses import dataclass
from typing import Optional

@dataclass
class Image:
    coverType: str
    extension: str
    remoteUrl: Optional[str]
    url: str

    @classmethod
    def from_dict(cls, data: dict) -> 'Image':
        return cls(
            coverType=data.get('coverType', ''),
            extension=data.get('extension', ''),
            remoteUrl=data.get('remoteUrl'),
            url=data.get('url', '')
        )
    
    def __repr__(self) -> str:
        return (f"Image(coverType={self.coverType!r}, extension={self.extension!r}, "
                f"remoteUrl={self.remoteUrl!r}, url={self.url!r})")