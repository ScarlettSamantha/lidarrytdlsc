from typing import Optional
from datetime import datetime

def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Helper to convert ISO date strings (with a trailing 'Z') to datetime objects."""
    if dt_str is None:
        return None
    # Replace 'Z' with '+00:00' so that fromisoformat can parse it.
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))