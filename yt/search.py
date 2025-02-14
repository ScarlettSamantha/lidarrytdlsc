from typing import Dict
from youtubesearchpython import VideosSearch # pyright: ignore[reportMissingImports]

def search_youtube_unofficial(query, max_results=10) -> str | Dict:
    videosSearch = VideosSearch(query, limit=max_results)
    return videosSearch.result()