import logging
import yt_dlp
import subprocess
from typing import Iterable, List, Dict, Any
from helper import parse_youtube_playlist_url_to_id, to_youtube_playlist_url

logger = logging.getLogger("yt.playlist")
logger.setLevel(logging.DEBUG)
logging.basicConfig(format="[%(name)s] %(levelname)s: %(message)s", level=logging.DEBUG)


def get_playlist_ids(playlist_url: str):
    """
    Uses yt-dlp in flat-playlist mode to extract video IDs.
    
    Each line of the output corresponds to one video ID.
    """
    command = [
        "yt-dlp",
        playlist_url,
        "--flat-playlist",
        "-O", "%(id)s"
    ]
    
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing yt-dlp: {e.stderr}")
        return []
    
    # Each line in stdout is a video ID.
    return result.stdout.splitlines()

def parse_playlist(playlist_url: str) -> Iterable:
    """
    Extracts and parses a YouTube playlist using yt-dlp in flat mode.

    Args:
        playlist_url (str): The URL or ID of the YouTube playlist.
    
    Returns:
        List[Dict[str, Any]]: A list of playlist entries with minimal metadata.
                              Each entry typically contains an 'id' and optionally a 'title'.
    """
    ydl_opts = {
        'quiet': False,
        'skip_download': True,
        'ignore-errors': True,
        'flat-playlist': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            playlist_id = parse_youtube_playlist_url_to_id(playlist_url)
            if playlist_id is None:
                return []
            playlist_url = to_youtube_playlist_url(playlist_id)
            result = get_playlist_ids(playlist_url)
        except Exception as e:
            logger.error(f"Error extracting playlist info: {e}")
            return []
        logger.info(f"Found {len(result)} in {playlist_url}")

    if not isinstance(result, list):
        logger.error("No playlist info found.")
        return []

    return result
