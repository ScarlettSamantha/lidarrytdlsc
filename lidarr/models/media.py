from dataclasses import dataclass

@dataclass
class Media:
    mediumFormat: str
    mediumName: str
    mediumNumber: int

    @classmethod
    def from_dict(cls, data: dict) -> 'Media':
        return cls(
            mediumFormat=data.get('mediumFormat', ''),
            mediumName=data.get('mediumName', ''),
            mediumNumber=data.get('mediumNumber', 0)
        )
    
    def __repr__(self) -> str:
        return (f"Media(mediumFormat={self.mediumFormat!r}, "
                f"mediumName={self.mediumName!r}, mediumNumber={self.mediumNumber})")