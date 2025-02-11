from dataclasses import dataclass

@dataclass
class Link:
    name: str
    url: str

    @classmethod
    def from_dict(cls, data: dict) -> 'Link':
        return cls(
            name=data.get('name', ''),
            url=data.get('url', '')
        )
    
    def __repr__(self) -> str:
        return f"Link(name={self.name!r}, url={self.url!r})"