
import re
from typing import Optional, Dict

YOUTUBE_PLAYLIST_REGEX = re.compile(r"(?P<schema>http(s)?)\:\/\/(?P<subdomain>www|music)\.(?P<domain>youtube|yt)\.(?P<tld>com|be)\/playlist\?list\=(?P<playlist_id>\w+)(&si=(?P<some_id>\w+)|$)")
YOUTUBE_EXTRACT_INDEX = re.compile(r"(?P<schema>\w+):\/\/(?P<subdomain>www)?\.(?P<domain>youtube|yt)\.(?P<tld>com|be)\/watch\?v\=(?P<id>\w+)$")

def to_seconds(input: str) -> int:
    return (int(input.split(':')[0]) * 60) + int(input.split(':')[1])

def fix_viewers(input: str) -> int:
    try:
        return int(input.split(' ')[0].replace(',', ''))
    except ValueError:
        return 0

def to_youtube_url(video_id: str) -> str:
    if video_id.startswith("http"):
        return video_id
    return f"https://www.youtube.com/watch?v={video_id}"


def to_youtube_playlist_url(playlist_id: str) -> str:
    if playlist_id.startswith("http"):
        return playlist_id
    return f"https://www.youtube.com/playlist?list={playlist_id}"

def strip_utf8(input: str | bytes) -> str:
    if isinstance(input, bytes):
        return input.decode('utf-8', 'ignore')
    return input.encode('utf-8').decode('utf-8', 'ignore')


def parse_youtube_playlist_url(url: str) -> Optional[Dict[str, str]]:
    """Parses a YouTube playlist URL and extracts relevant groups.

    Args:
        url (str): The YouTube playlist URL.

    Returns:
        Optional[Dict[str, str]]: A dictionary of extracted groups or None if no match.
    """
    match = YOUTUBE_PLAYLIST_REGEX.match(url)
    if match:
        return match.groupdict()
    return None

def parse_youtube_url_to_id(url: str) -> Optional[str]:
    regex_result = YOUTUBE_EXTRACT_INDEX.match(url)
    if regex_result:
        return regex_result.groupdict()['id']
    return None

def parse_youtube_playlist_url_to_id(url: str) -> Optional[str]:
    regex_result = parse_youtube_playlist_url(url)
    if not regex_result:
        return None
    return regex_result['playlist_id']

def safe_copy(src: str, dest: str, chunk_size: int = 65536) -> bool:
    """
    Copies a file from 'src' to 'dest' in chunks, computing a CRC32 for the source data.
    After writing, the destination file is re-read to compute its CRC32 and the file sizes
    are compared. If they match, the source file is unlinked and the function returns True.
    Otherwise, returns False.
    """
    import os
    import zlib

    src_total = 0
    src_crc = 0

    # Open source and destination files
    with open(src, 'rb') as rfp, open(dest, 'wb') as wfp:
        while True:
            chunk = rfp.read(chunk_size)
            if not chunk:
                break
            src_total += len(chunk)
            src_crc = zlib.crc32(chunk, src_crc)
            wfp.write(chunk)

    # Verify the destination file size matches the source's
    dest_total = os.path.getsize(dest)
    if src_total != dest_total:
        return False

    # Re-read the destination file to compute its CRC32
    dest_crc = 0
    with open(dest, 'rb') as wfp:
        while True:
            chunk = wfp.read(chunk_size)
            if not chunk:
                break
            dest_crc = zlib.crc32(chunk, dest_crc)

    # Check if the CRC32 values match
    if src_crc != dest_crc:
        return False

    # Remove the source file
    os.unlink(src)
    return True
    
    


def download_and_convert_image(url, dest_dir, dest_filename=None):
    """
    Downloads an image from the given URL, converts it to JPEG format (if necessary),
    detects its dimensions, and saves it in dest_dir.

    :param url: URL of the image.
    :param dest_dir: Directory where the image will be saved.
    :param dest_filename: Optional filename for the saved image.
    :return: Tuple (path_to_image, (width, height)) if successful; otherwise (None, (0,0)).
    """
    import os
    import requests
    from PIL import Image
    from io import BytesIO
    # Derive a filename if one is not provided.
    if not dest_filename:
        dest_filename = os.path.basename(url.split("?")[0])
    # Ensure the filename has a .jpg extension.
    dest_filename = os.path.splitext(dest_filename)[0] + ".jpg"
    dest_path = os.path.join(dest_dir, dest_filename)
    
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        image_data = response.content

        # Open the image from the downloaded bytes.
        image = Image.open(BytesIO(image_data))
        # Convert to RGB if necessary (JPEG does not support alpha channels).
        if image.mode != 'RGB':
            image = image.convert('RGB')
        width, height = image.size
        print(f"Downloaded image dimensions: {width}x{height}")
        # Save the image as JPEG.
        image.save(dest_path, 'JPEG')
        return dest_path, (width, height)
    except Exception as e:
        print("Error downloading or converting image:", e)
        return None, (0, 0)
