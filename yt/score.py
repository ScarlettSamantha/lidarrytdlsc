from typing import Tuple
from rapidfuzz import fuzz # pyright: ignore[reportMissingImports]
import helper
from models.video import VideoData


def compare_video(
    query_title: str,
    video: VideoData,
    view_trashhold: int = 1000,
    boost_official: int = 10,
    boost_music: int = 5,
    boost_duration: int = 5,
    boost_viewers: int = 5,
    boost_cover: int = -10,
    boost_per_10000: int = 1,
    min_time: int = 120,
    max_time: int = 600
) -> Tuple[float, str]:
    """
    Compare a query title with a video's title using fuzzy matching, and adjust the score with additional boosts based on video metadata.

    The function calculates an initial fuzzy matching score between the query title and the video's title,
    then applies additional boosts based on the following criteria:
      - If the video title contains the word "official", add `boost_official` points.
      - If the video title contains the word "music", add `boost_music` points.
      - If the video duration (converted to seconds) is between `min_time` and `max_time`, add `boost_duration` points.
      - If the video's view count exceeds `view_trashhold`, add `boost_viewers` points.

    Args:
        query_title (str): The search query title.
        video (VideoData): The video object containing metadata such as title, duration, and view count.
        view_trashhold (int, optional): The minimum view count required to apply a viewer boost (default is 1000).
        boost_official (int, optional): Points to add if the video title contains "official" (default is 10).
        boost_music (int, optional): Points to add if the video title contains "music" (default is 5).
        boost_duration (int, optional): Points to add if the video duration is between `min_time` and `max_time` (default is 5).
        boost_viewers (int, optional): Points to add if the video's view count exceeds `view_trashhold` (default is 5).
        min_time (int, optional): Minimum duration in seconds for applying the duration boost (default is 120 seconds, i.e., 2 minutes).
        max_time (int, optional): Maximum duration in seconds for applying the duration boost (default is 600 seconds, i.e., 10 minutes).

    Returns:
        Tuple[float, str]: A tuple where the first element is the final score (capped at 100) representing the match quality,
                           and the second element is the video's title.
    """
    # Retrieve video metadata
    video_title = video.title
    duration_seconds = helper.to_seconds(video.duration)
    views = helper.fix_viewers(video.viewCount.text)
    
    # Calculate the basic fuzzy matching score between the query title and the video title
    score = fuzz.ratio(query_title.lower(), video_title.lower())
    
    # Boost if 'official' is found in the video title
    if 'official' in video_title.lower():
        score += boost_official
    
    # Boost if 'music' is found in the video title
    if 'music' in video_title.lower():
        score += boost_music
        
    if 'cover' in video_title.lower() and 'cover' not in query_title.lower():
        score += boost_cover

    # Boost if the video duration is between min_time and max_time seconds
    if min_time <= duration_seconds <= max_time:
        score += boost_duration
        
    # Boost if the video's view count exceeds the specified threshold
    if views > view_trashhold:
        score += boost_viewers
        
    score += views * boost_per_10000

    # Ensure the final score does not exceed 100
    return min(score, 100), video_title



