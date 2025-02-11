from youtubesearchpython import VideosSearch # pyright: ignore[reportMissingImports]

def search_youtube_unofficial(query, max_results=10):
    videosSearch = VideosSearch(query, limit=max_results)
    return videosSearch.result()