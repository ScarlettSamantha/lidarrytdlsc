import logging
import os
import argparse
import subprocess
import json
import random
import yt_dlp
import helper 
import dotenv
from debug import write_debug_log
from playlist import parse_playlist

from os import environ
from score import compare_video
from models.video import VideoData
from typing import Optional, Tuple, List
from thumbnail import ThumbnailDownloader
from os.path import join, realpath, dirname
from identify import detect_and_update_tags
from search import search_youtube_unofficial

# Monkey-patch httpx to remove the 'proxies' argument, fixing the error in youtubesearchpython.
import httpx

original_post = httpx.post
def patched_post(*args, **kwargs):
    kwargs.pop('proxies', None)
    return original_post(*args, **kwargs)
httpx.post = patched_post

dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

logging.basicConfig(
    level=logging.DEBUG, 
    format="[%(name)s] | %(asctime)s.%(msecs)03d - %(levelname)s - %(message)s", 
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("downloader")

class VideoDownloader:
    """
    A class to search for a video by title, download its audio using yt-dlp,
    and move the resulting file to a chosen destination.
    """
    def __init__(self, tmp_dir='tmp/progress', dest_dir=None, bitrate:int=360, suffix: str=".mp3", try_identify: bool = True, logger: logging.Logger = logger):
        """
        Initializes the downloader with default properties.
        
        :param tmp_dir: Directory to download the audio (default: '/tmp').
        :param dest_dir: Final destination directory for the audio file.
        """
        self.tmp_dir = realpath(join(dirname(__file__), '..', tmp_dir))
        self.dest_dir = dest_dir
        self.extensioned_filename: str 
        self.tmp_file_path: str = realpath(join(self.tmp_dir, str(random.randrange(11111111, 999999999))))
        self.tmp_file_path = realpath(self.tmp_file_path if self.tmp_file_path.endswith(".mp3") else self.tmp_file_path + ".mp3")
        self.suffix: str = suffix
        self.bitrate: int = bitrate
        self.source: str = "https://github.com/ScarlettSamantha/lidarrytdlsc"
        self.try_identify: bool = try_identify
        self.logger: logging.Logger = logger

    def find_best_match(self, title, debug: bool = True):
        """
        Searches for videos matching the title and selects the best match based on a score.
        
        :param title: Title of the video to search.
        :param debug: If True, generates a debug log file.
        :return: Tuple (best_video, best_score)
        """
        results = search_youtube_unofficial(title, 20)
        logger_child = self.logger.getChild("matcher")
        
        # If results is a JSON string, load it.
        if isinstance(results, str):
            results = json.loads(results)
        results = results.get('result', [])
        
        best_video: Optional[VideoData] = None
        best_score: float = 0.0
        debug_entries: List = []  # List to collect debug data for each video

        for vid in results:
            video_data = VideoData.parse_video_data(vid)
            score, cleaned_title, debug_steps = compare_video(
                title, video_data, debug_output_object=True
            )
            if debug:
                debug_entries.append({
                    "video_id": video_data.id,
                    "score": score,
                    "video_data": video_data.__todict__(),
                    "debug": debug_steps
                })
            logger_child.debug(f"Video {cleaned_title}({video_data.id}) found with match score {score:.2f}")
            if score > best_score:
                best_score = score
                best_video = video_data

        if debug:
            write_debug_log(debug_entries, title, best_video.title if best_video else "no-match-found", self.logger)

        if best_video:
            self.logger.info(f"Best video found \"{best_video.title}\" with score {best_score:.2f} (ID: {best_video.id})")
        else:
            self.logger.warning(f"Could not find video that matched sufficiently (score {best_score:.2f})")
        
        return best_video, best_score

    def inject_download_source(self, download_source) -> bool:
        if not download_source:
            return True

        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-i", self.extensioned_filename,
                "-c", "copy",
                "-metadata", f"comment=Download source: {download_source}",
                self.tmp_file_path if self.tmp_file_path.endswith(".mp3") else self.tmp_file_path + ".mp3"
            ]
            self.logger.debug(f"Running command: {str(cmd)}")
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.replace(self.tmp_file_path, self.extensioned_filename)
        except Exception as _:
            self.logger.error("Error embedding metadata")
            return False

        return True

    def download_audio(self, video, audio_quality='320', image_source=None, download_source=None) -> bool:
        """
        Downloads the audio of the given video using yt-dlp.
        
        :param video: VideoData object containing video details.
        :param audio_quality: Audio quality preset ('320', '192', or '128').
        :param image_source: Optional path to an image file to embed as cover art.
        :param download_source: Optional string representing the download source.
        :return: True if download succeeds, False otherwise.
        """
        logger_child = self.logger.getChild('download_audio')
        if not hasattr(video, 'id'):
            raise ValueError("The video object does not have an 'id' attribute.")

        video_id = video.id
        self.tmp_file_path = os.path.join(self.tmp_dir, video_id)

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': self.tmp_file_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': audio_quality,
            }],
            'quiet': False,
            'noplaylist': True,
        }
        
        logger_child.info("Downloading audio using yt-dlp...")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                url = video.link if hasattr(video, 'link') else helper.to_youtube_url(video.id)
                ydl.download([url])
        except Exception as e:
            logger_child.debug(f"Error during download: {e}")
            return False

        self.extensioned_filename = self.tmp_file_path if self.tmp_file_path.endswith('.mp3') else self.tmp_file_path + '.mp3'
        
        embedded_audio_with_thumbnail = None
        try:
            if environ.get('THUMBNAIL_RETRIVAL_ENABLE') is True:
                thumbnailInstance = ThumbnailDownloader(self.tmp_dir)
                embedded_audio_with_thumbnail = thumbnailInstance.download_thumbnail(video=video, output_path=self.extensioned_filename, image_source=image_source)
                if embedded_audio_with_thumbnail is not None:
                    os.replace(embedded_audio_with_thumbnail, self.extensioned_filename)
        except Exception as e:
            logger_child.warning(f"Error embedding thumbnail: {embedded_audio_with_thumbnail} -> {e}")
            
        if not self.inject_download_source(download_source=self.source):
            logger_child.warning(f"Error embedding source into {self.extensioned_filename}")

        return True

    def extract_metadata(self, src: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extracts metadata (artist, album, title) from an MP3 file.
        
        :param src: Path to the audio file.
        :return: Tuple containing (artist, album, title).
        """
        from mutagen._file import File as MutagenFile
        audio = MutagenFile(src)
        artist, album, title = None, None, None

        if audio and getattr(audio, "tags", None):
            tags = audio.tags
            if 'TPE1' in tags and tags['TPE1'].text:
                artist = tags['TPE1'].text[0]
            elif 'artist' in tags:
                artist_val = tags.get('artist')
                artist = artist_val[0] if isinstance(artist_val, list) else artist_val

            if 'TALB' in tags and tags['TALB'].text:
                album = tags['TALB'].text[0]
            elif 'album' in tags:
                album_val = tags.get('album')
                album = album_val[0] if isinstance(album_val, list) else album_val

            if 'TIT2' in tags and tags['TIT2'].text:
                title = tags['TIT2'].text[0]
            elif 'title' in tags:
                title_val = tags.get('title')
                title = title_val[0] if isinstance(title_val, list) else title_val

        return artist, album, title

    def move_audio(self, src: str, dest_dir: Optional[str] = None, dest_name: Optional[str] = None, folder_based: bool = False) -> str:
        """
        Moves the downloaded audio file to the destination directory.
        
        :param src: Source file path.
        :param dest_dir: Destination directory.
        :param dest_name: New name for the file.
        :param folder_based: Organize files into an artist/album structure if True.
        :return: Final path of the moved audio file.
        """
        src = src if src.endswith(".mp3") else f"{src}.mp3"
        destination = dest_dir if dest_dir else self.dest_dir
        if not destination:
            raise ValueError("Destination directory is not specified.")

        if folder_based:
            artist, album, title = self.extract_metadata(src)
            if artist and title:
                from slugify import slugify
                artist_folder = slugify(artist, separator="_", lowercase=False)
                destination = os.path.join(destination, artist_folder)
                if album:
                    album_folder = slugify(album, separator="_", lowercase=False)
                    destination = os.path.join(destination, album_folder)
                dest_name = slugify(title, separator="_", lowercase=False)
                dest_name = dest_name if dest_name.endswith(".mp3") else f"{dest_name}.mp3"
            elif dest_name is None:
                raise ValueError("Folder-based organization requested, but metadata is missing and no dest_name was provided.")

        if not os.path.exists(destination):
            os.makedirs(destination, exist_ok=True)

        if dest_name is None:
            raise ValueError("Destination file name (dest_name) cannot be None.")

        dest_name = dest_name if dest_name.endswith(".mp3") else f"{dest_name}.mp3"
        dest_path = os.path.abspath(os.path.join(destination, dest_name))
        self.logger.info("Moving file from %s to %s", src, dest_path)
        helper.safe_copy(src, dest_path)
        return dest_path

    def process(self, title, dest_dir: Optional[str]=None):
        """
        Searches for the best matching video, downloads its audio, and moves it if needed.
        
        :param title: The title of the video to search for.
        :param dest_dir: Optional destination directory.
        :return: Final path of the audio file, or None if download fails.
        """
        best_video, score = self.find_best_match(title)
        if not best_video:
            self.logger.error(f"No matching video found for title: {title}")
            return None

        def print_best_video(video: VideoData, score: float) -> str:
            return f"{video.title}@{video.duration} - {round(score, 3)}% match"

        print_best_video(best_video, score)

        downloaded_file = self.download_audio(best_video, audio_quality=str(self.bitrate))
        if downloaded_file is False:
            self.logger.warning("Download failed.")
            return None
        else:
            self.logger.info("Download succeeded.")

        if self.try_identify:
            detect_and_update_tags(f"{self.tmp_file_path}")

        if dest_dir or self.dest_dir:
            if not title.endswith(".mp3"):
                title = title + ".mp3"
            final_path = self.move_audio(self.tmp_file_path, dest_dir, title, folder_based=True)
            return final_path
        else:
            self.logger.warning(f"No destination directory specified. Audio file remains in temporary folder: {downloaded_file}")
            return downloaded_file


if __name__ == "__main__":
    from cli import interactive_prompt
    dotenv.load_dotenv('../.env')
    
    parser = argparse.ArgumentParser(description="Audio Downloader Application using yt-dlp")
    parser.add_argument("title", nargs="?", help="Title, video ID or playlist URL to download")
    parser.add_argument("--tmp_dir", default="tmp/progress", help="Temporary directory for downloads (default: tmp/progress)")
    parser.add_argument("--dest_dir", default="tmp/ready", help="Destination directory for the final audio file (default: tmp/ready)")
    parser.add_argument("--audio_quality", default=320, help="Audio quality preset (320,192,128) for extraction")
    parser.add_argument("--interactive", action="store_true", help="Run interactive CLI mode")
    parser.add_argument("--identify", action="store_true", default=True, help="Attempt to correct tags and identify the song (default: True)")
    parser.add_argument("--mode", type=str, 
                        choices=["Search by Title", "Download by Video ID", "Download Playlist"],
                        default="Search by Title", 
                        help="Mode to run the downloader in")
    args = parser.parse_args()

    if args.interactive or not args.title:
        user_input, audio_quality, tmp_dir, dest_dir, identify, mode = interactive_prompt()
    else:
        user_input = args.title
        audio_quality = args.audio_quality if args.audio_quality is not None else "320"
        tmp_dir = os.path.realpath(args.tmp_dir)
        dest_dir = os.path.realpath(args.dest_dir)
        identify = args.identify if hasattr(args, 'identify') else True
        mode = args.mode  # Use the mode provided by the command line

    value = helper.strip_utf8(user_input.replace("\n", "").strip())

    downloader = VideoDownloader(tmp_dir=tmp_dir, dest_dir=dest_dir, try_identify=bool(identify))

    if mode == "Search by Title":
        downloader.process(value)
    elif mode == "Download by Video ID":
        from models.video import VideoData
        video = VideoData(id=value, title=f"Video {value}", url=helper.to_youtube_url(value))
        downloader.download_audio(video, audio_quality=audio_quality)
    elif mode == "Download Playlist":
        # First parse the playlist to retrieve its entries
        entries = parse_playlist(value)
        if not entries or not isinstance(entries, dict):
            logger.error("No entries found in the playlist.")
        else:
            for entry in entries["entries"]:
                video_id = entry["id"]
                if not video_id:
                    logger.warning("Skipping an entry with no video ID.")
                    continue
                # Create a minimal VideoData object
                from models.video import VideoData
                video = VideoData(
                    id=video_id,  
                    url=helper.to_youtube_url(video_id),
                    link=helper.to_youtube_url(video_id)
                )
                success = downloader.download_audio(video, audio_quality=audio_quality)
                if success:
                    if downloader.try_identify:
                        detect_and_update_tags(downloader.tmp_file_path)
                    if dest_dir or downloader.dest_dir:
                        final_name = video.title + ".mp3"
                        try:
                            final_path = downloader.move_audio(downloader.tmp_file_path, dest_dir, final_name, folder_based=True)
                            logger.info(f"Downloaded and moved: {final_path}")
                        except Exception as e:
                            logger.error(f"Failed to move audio file for video {video.title}: {e}")
                    else:
                        logger.info(f"Downloaded: {downloader.tmp_file_path}")
                else:
                    logger.error(f"Download failed for video {video.title}")
