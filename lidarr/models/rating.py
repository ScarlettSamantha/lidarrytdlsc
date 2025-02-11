from dataclasses import dataclass

@dataclass
class Rating:
    value: float
    votes: int

    @classmethod
    def from_dict(cls, data: dict) -> 'Rating':
        return cls(
            value=data.get('value', 0.0),
            votes=data.get('votes', 0)
        )
    
    def __repr__(self) -> str:
        return f"Rating(value={self.value}, votes={self.votes})"