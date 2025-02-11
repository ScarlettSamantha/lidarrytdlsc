from dataclasses import dataclass

@dataclass
class Statistics:
    percentOfTracks: float
    sizeOnDisk: int
    totalTrackCount: int
    trackCount: int
    trackFileCount: int

    @classmethod
    def from_dict(cls, data: dict) -> 'Statistics':
        return cls(
            percentOfTracks=data.get('percentOfTracks', 0.0),
            sizeOnDisk=data.get('sizeOnDisk', 0),
            totalTrackCount=data.get('totalTrackCount', 0),
            trackCount=data.get('trackCount', 0),
            trackFileCount=data.get('trackFileCount', 0)
        )
    
    def __repr__(self) -> str:
        return (f"Statistics(trackCount={self.trackCount}, "
                f"totalTrackCount={self.totalTrackCount}, "
                f"trackFileCount={self.trackFileCount}, "
                f"percentOfTracks={self.percentOfTracks:.2f}, "
                f"sizeOnDisk={self.sizeOnDisk})")