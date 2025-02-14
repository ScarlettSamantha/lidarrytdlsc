import logging
import os
import argparse
import subprocess
import json
import random
import yt_dlp
import helper 
import questionary
import dotenv
from os import environ
from score import compare_video
from models.video import VideoData
from typing import Optional, Dict, Tuple
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

quality_presets: Dict[int, str] = {
    320: "High",
    192: "Medium",
    128: "Low"
}

dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

logging.basicConfig(level=logging.DEBUG, format="[%(name)s] | %(asctime)s.%(msecs)03d - %(levelname)s - %(message)s", datefmt='%H:%M:%S')
logger = logging.getLogger("downloader")

def interactive_prompt():
    """Prompt the user for inputs interactively using Questionary."""
    title = questionary.text("Enter video title:").ask()
    audio_quality_choice = questionary.select(
        "Select audio quality preset:",
        choices=[f"{name} ({bitrate})" for bitrate, name in quality_presets.items()]
    ).ask()
    # Extract the bitrate from the choice string and use it as the key
    selected_bitrate = int([str(bitrate) for bitrate in quality_presets.keys() 
                          if str(bitrate) in audio_quality_choice][0])
    audio_quality = str(selected_bitrate)

    tmp_dir = questionary.text("Enter temporary directory:", default="tmp/progress").ask()
    dest_dir = questionary.text("Enter destination directory (leave empty for none):", default="tmp/ready").ask()
    if dest_dir.strip() == "":
        dest_dir = None
    identify = questionary.confirm("Would you like to try to identify and write tags for the song").ask()

    return title, audio_quality, tmp_dir, dest_dir, identify


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
        self.tmp_file_path = realpath(self.tmp_file_path if self.tmp_file_path.endswith(".mp3") else self.tmp_file_path + ".mp3" )
        self.suffix: str = suffix
        self.bitrate: int = bitrate
        self.source: str = "https://github.com/ScarlettSamantha/lidarrytdlsc"
        self.try_identify: bool = try_identify
        self.logger: logging.Logger = logger
        
    def find_best_match(self, title):
        """
        Searches for videos matching the title and selects the best match based on a score.
        
        :param title: Title of the video to search.
        :return: Tuple (best_video, best_score)
        """
        results = search_youtube_unofficial(title, 20)
        logger = self.logger.getChild("matcher")
        # Its json
        if isinstance(results, str):
            results = json.loads(results)
        results = results.get('result', [])
        best_video = None
        best_score = 0.0

        for vid in results:
            video_data = VideoData.parse_video_data(vid)
            score_tuple = compare_video(title, video_data)
            logger.debug(f"Video{video_data.id} found with match {score_tuple[0]}")
            if score_tuple[0] > best_score:
                best_score = score_tuple[0]
                best_video = video_data
        if best_video is not None:
            logger.info(f"Best video found \"{best_video.title}\" {best_score}% on id ({best_video.id})")
        else:
            logger.warning(f"Could not find video that matched a little with score {best_score}")
        return best_video, best_score

    def inject_download_source(self, download_source) -> bool:
        if not download_source:
            # Nothing to inject if download_source is empty.
            return True

        try:
            # Define a temporary output file.
            
            # Build the ffmpeg command.
            # This command takes the original file, copies the streams without re-encoding,
            # and injects the metadata comment, writing the output to a temporary file.
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output file without asking.
                "-i", self.extensioned_filename,
                "-c", "copy",
                "-metadata", f"comment=Download source: {download_source}",
                self.tmp_file_path if self.tmp_file_path.endswith(".mp3") else self.tmp_file_path + ".mp3"
            ]
            
            # Optional: print the command for debugging purposes.
            self.logger.debug(f"Running command: {str(cmd)}")
            
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Replace the original file with the new one that has the embedded metadata.
            os.replace(self.tmp_file_path, self.extensioned_filename)
        except Exception as _:
            self.logger.error("Error embedding metadata")
            return False

        return True

    def download_audio(self, video, audio_quality='320', image_source=None, download_source=None) -> bool:
        """
        Downloads the audio of the given video using yt-dlp with the chosen audio quality,
        and optionally embeds an image (cover art) and a download source into the MP3 file.
        
        If no image_source is provided, the video's thumbnail (richThumbnail or thumbnails list)
        is used as the default cover art.
        
        :param video: VideoData object containing video details.
        :param audio_quality: Audio quality preset ('320', '192', or '128').
        :param image_source: Optional path to an image file to embed as cover art.
        :param download_source: Optional string representing the download source to embed as metadata.
        :return: Path to the final MP3 file.
        """
        logger = self.logger.getChild('download_audio')
        if not hasattr(video, 'id'):
            raise ValueError("The video object does not have an 'id' attribute.")

        video_id = video.id
        # Use the video id for the output filename. The final file will have a .mp3 extension.
        self.tmp_file_path = os.path.join(self.tmp_dir, video_id)

        # yt-dlp options: download best audio and extract/convert to MP3.
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': self.tmp_file_path,  # yt-dlp will add the appropriate extension (e.g. .mp3)
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': audio_quality,
            }],
            'quiet': False,
            'noplaylist': True,
        }
        
        logger.info("Downloading audio using yt-dlp...")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                url = video.url if hasattr(video, 'url') else helper.to_youtube_url(video.id)
                ydl.download([url])
        except Exception as _:
            logger.debug("Error during download: {e}")
            return False

        # Determine the downloaded file path.
        self.extensioned_filename = self.tmp_file_path if self.tmp_file_path.endswith('.mp3') else self.tmp_file_path + '.mp3'
        
        embedded_audio_with_thumbnail = None
        try:
        # Try to see if thumbnail retrival system is active
            if environ['THUMBNAIL_RETRIVAL_ENABLE'] is True:
                thumbnailInstance = ThumbnailDownloader(self.tmp_dir)
                embedded_audio_with_thumbnail = thumbnailInstance.download_thumbnail(video=video, output_path=self.extensioned_filename, image_source=image_source)
                if embedded_audio_with_thumbnail is not None:
                    os.replace(embedded_audio_with_thumbnail, self.extensioned_filename)
        except Exception as e:
            logger.warning(f"Error embedding thumbnail: {embedded_audio_with_thumbnail} -> {e}")
            
        if not self.inject_download_source(download_source=self.source):
            logger.warning(f"Error embedding source: {embedded_audio_with_thumbnail} -> {self.extensioned_filename}")

        return True

    def extract_metadata(self, src: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extracts metadata (artist, album, title) from an MP3 file using Mutagen.

        Args:
            src (str): Path to the audio file.

        Returns:
            Tuple containing (artist, album, title), where each is either a string or None.
        """
        from mutagen._file import File as MutagenFile  # local import to limit scope
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

    def move_audio(
        self,
        src: str,
        dest_dir: Optional[str] = None,
        dest_name: Optional[str] = None,
        folder_based: bool = False
    ) -> str:
        """
        Moves the downloaded audio file from the temporary folder to the destination directory.
        If folder_based is True, organizes the file into an artist/album structure based on metadata.

        Args:
            src (str): Source file path.
            dest_dir (Optional[str]): Destination directory (overrides instance's dest_dir).
            dest_name (Optional[str]): Optional new name for the file.
            folder_based (bool): If True, organize files based on metadata.

        Returns:
            str: The final path of the moved audio file.
        """
        src = src if src.endswith(".mp3") else f"{src}.mp3"
        destination = dest_dir if dest_dir else self.dest_dir
        if not destination:
            raise ValueError("Destination directory is not specified.")

        if folder_based:
            artist, album, title = self.extract_metadata(src)
            if artist and title:
                from slugify import slugify  # local import for clarity
                artist_folder = slugify(artist, separator="_", lowercase=False)
                destination = os.path.join(destination, artist_folder)
                if album:
                    album_folder = slugify(album, separator="_", lowercase=False)
                    destination = os.path.join(destination, album_folder)
                # Override dest_name with the slugified title.
                dest_name = slugify(title, separator="_", lowercase=False)
                dest_name = dest_name if dest_name.endswith(".mp3") else f"{dest_name}.mp3"
            elif dest_name is None:
                raise ValueError("Folder-based organization was requested, but metadata is missing and no dest_name was provided.")

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
        :param dest_dir: Optional destination directory to override the instance's dest_dir.
        :return: Final path of the audio file, or None if download fails.
        """
        best_video, score = self.find_best_match(title)
        if not best_video:
            self.logger.error(f"No matching video found for title: {title}")
            return None


        def print_best_video(video: VideoData, score:int | float) -> str:
            return f"{video.title}@{video.duration} - {round(score, 3)}% match"

        print_best_video(best_video, score)

        downloaded_file = self.download_audio(best_video, audio_quality=str(self.bitrate))
        if downloaded_file is False:
            self.logger.warning("Download failed.")
            return None
        else:
            self.logger.info("download success")

        if self.try_identify:
            detect_and_update_tags(f"{self.tmp_file_path}")

        if dest_dir or self.dest_dir:
            if not title.endswith(".mp3"):
                title = title + ".mp3"
            final_path = self.move_audio(self.tmp_file_path, dest_dir, title, True)
            return final_path
        else:
            self.logger.warning("No destination directory specified. Audio file remains in temporary folder: {downloaded_file}")
            return downloaded_file


if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv('../.env')
    
    parser = argparse.ArgumentParser(description="Audio Downloader Application using yt-dlp")
    parser.add_argument("title", nargs="?", help="Title of the video to search and download")
    parser.add_argument("--tmp_dir", default="tmp/progress", help="Temporary directory for downloads (default: tmp/progress)")
    parser.add_argument("--dest_dir", default="tmp/ready", help="Destination directory for the final audio file (default: tmp/ready)")
    parser.add_argument("--audio_quality", default=320, help="Audio quality preset (320,192,128) for extraction")
    parser.add_argument("--interactive", action="store_true", help="Run interactive CLI mode")
    parser.add_argument("--identify", action="store_true", default=True, help="Will attempt to correct tag's and identify the song (defualt: True)")
    args = parser.parse_args()

    if args.interactive or not args.title:
        title, audio_quality, tmp_dir, dest_dir, identify = interactive_prompt()
    else:
        title: str = args.title
        audio_quality = args.audio_quality if args.audio_quality is not None else "320"
        tmp_dir = os.path.realpath(args.tmp_dir)
        dest_dir = os.path.realpath(args.dest_dir)
        identify = args.identify if hasattr(args, 'identify') else True

    title:str = helper.strip_utf8(title.replace("\n","").lower().strip())

    downloader = VideoDownloader(tmp_dir=tmp_dir, dest_dir=dest_dir, try_identify=bool(identify))
    downloader.process(title)
