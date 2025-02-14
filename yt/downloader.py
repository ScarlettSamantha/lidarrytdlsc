import os
import argparse
import subprocess
import json
from pprint import pprint
from typing import Optional, Dict
from os import environ
import yt_dlp
import helper 
import questionary
import dotenv
from identify import detect_and_update_tags
from score import compare_video
from search import search_youtube_unofficial
from models.video import VideoData
from slugify import slugify
from thumbnail import ThumbnailDownloader

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

    tmp_dir = questionary.text("Enter temporary directory:", default="/tmp").ask()
    dest_dir = questionary.text("Enter destination directory (leave empty for none):", default="tmp/ready").ask()
    if dest_dir.strip() == "":
        dest_dir = None

    return title, audio_quality, tmp_dir, dest_dir


class VideoDownloader:
    """
    A class to search for a video by title, download its audio using yt-dlp,
    and move the resulting file to a chosen destination.
    """
    def __init__(self, tmp_dir='tmp/progress', dest_dir=None, bitrate:int=360, suffix: str=".mp3"):
        """
        Initializes the downloader with default properties.
        
        :param tmp_dir: Directory to download the audio (default: '/tmp').
        :param dest_dir: Final destination directory for the audio file.
        """
        self.tmp_dir = os.path.join(os.path.dirname(__file__), '..', tmp_dir)
        self.dest_dir = dest_dir
        self.extensioned_filename: Optional[str] = None 
        self.tmp_file_path: Optional[str] = None
        self.suffix: str = suffix
        self.bitrate: int = bitrate
        self.source: str = "https://github.com/ScarlettSamantha/lidarrytdlsc"

    def find_best_match(self, title):
        """
        Searches for videos matching the title and selects the best match based on a score.
        
        :param title: Title of the video to search.
        :return: Tuple (best_video, best_score)
        """
        results = search_youtube_unofficial(title)
        # Its json
        if isinstance(results, str):
            results = json.loads(results)
        results = results.get('result', [])
        best_video = None
        best_score = 0.0

        for vid in results:
            video_data = VideoData.parse_video_data(vid)
            score_tuple = compare_video(title, video_data)
            if score_tuple[0] > best_score:
                best_score = score_tuple[0]
                best_video = video_data

        return best_video, best_score

    def inject_download_source(self, download_source) -> bool:
        if not download_source:
            # Nothing to inject if download_source is empty.
            return True

        try:
            # Define a temporary output file.
            temp_file = self.tmp_file_path + "_temp" + self.suffix
            
            # Build the ffmpeg command.
            # This command takes the original file, copies the streams without re-encoding,
            # and injects the metadata comment, writing the output to a temporary file.
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output file without asking.
                "-i", self.extensioned_filename,
                "-c", "copy",
                "-metadata", f"comment=Download source: {download_source}",
                temp_file
            ]
            
            # Optional: print the command for debugging purposes.
            print("Running command:", str(cmd))
            
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Replace the original file with the new one that has the embedded metadata.
            os.replace(temp_file, self.extensioned_filename)
        except Exception as e:
            print("Error embedding metadata:", e)
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
        
        print("Downloading audio using yt-dlp...")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                url = video.url if hasattr(video, 'url') else helper.to_youtube_url(video.id)
                ydl.download([url])
        except Exception as e:
            print("Error during download:", e)
            return False

        # Determine the downloaded file path.
        self.extensioned_filename = self.tmp_file_path + self.suffix
        
        embedded_audio_with_thumbnail = None
        try:
        # Try to see if thumbnail retrival system is active
            if environ['THUMBNAIL_RETRIVAL_ENABLE'] is True:
                thumbnailInstance = ThumbnailDownloader(self.tmp_dir)
                embedded_audio_with_thumbnail = thumbnailInstance.download_thumbnail(video=video, output_path=self.extensioned_filename, image_source=image_source)
                if embedded_audio_with_thumbnail is not None:
                    os.replace(embedded_audio_with_thumbnail, self.extensioned_filename)
        except Exception as e:
            print(f"Error embedding thumbnail: {embedded_audio_with_thumbnail} -> {e}")
            
        if not self.inject_download_source(download_source=self.source):
            print(f"Error embedding source: {embedded_audio_with_thumbnail} -> {self.extensioned_filename}")

        return True

    def move_audio(self, src, dest_dir=None, dest_name=None, ensure_extension: Optional[str] = ".mp3"):
        """
        Moves the downloaded audio file from the temporary folder to the destination directory.
        
        :param src: Source file path.
        :param dest_dir: Destination directory (if None, uses the instance's dest_dir).
        :return: The new path of the audio file.
        """
        destination = dest_dir if dest_dir else self.dest_dir
        if not destination:
            raise ValueError("Destination directory is not specified.")

        if not os.path.exists(destination):
            os.makedirs(destination, exist_ok=True)

        # Prevent double encoding            
        if self.suffix is not None and dest_name is not None and self.suffix not in dest_name[:-4]:
            dest_name = slugify(dest_name, separator="_", lowercase=True)
            dest_name = f"{dest_name}{self.suffix}"
            
            
        if self.suffix is not None and src is not None and self.suffix not in src[:-4]:
            src = f"{src}{self.suffix}"

        dest_path = f"{destination}/{dest_name}"
        print(f"Safe copy {src} -> {dest_path}")
        helper.safe_copy(src, dest_path)
        print(os.path.realpath(dest_path))
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
            print(f"No matching video found for title: {title}")
            return None

        print(f"Input title: {title}")
        print("Best matching video details:")
        pprint(best_video)
        print(f"Match score: {score}")

        downloaded_file = self.download_audio(best_video, audio_quality=str(self.bitrate))
        if downloaded_file is False:
            print("Download failed.")
            return None
        else:
            print("download success")

        if 'ACOUST_ID_ENABLE' in environ and environ['ACOUST_ID_ENABLE'] is True:
            detect_and_update_tags(downloaded_file, environ['ACOUST_ID_API'])

        if dest_dir or self.dest_dir:
            final_path = self.move_audio(self.tmp_file_path, dest_dir, title)
            print("Audio file moved to:", final_path)
            return final_path
        else:
            print("No destination directory specified. Audio file remains in temporary folder:", downloaded_file)
            return downloaded_file


if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv('../.env')
    
    parser = argparse.ArgumentParser(description="Audio Downloader Application using yt-dlp")
    parser.add_argument("title", nargs="?", help="Title of the video to search and download")
    parser.add_argument("--tmp_dir", default="tmp/progress", help="Temporary directory for downloads (default: /tmp)")
    parser.add_argument("--dest_dir", default="tmp/ready", help="Destination directory for the final audio file")
    parser.add_argument("--audio_quality", default=320, help="Audio quality preset (320,192,128) for extraction")
    parser.add_argument("--interactive", action="store_true", help="Run interactive CLI mode")
    args = parser.parse_args()

    if args.interactive or not args.title:
        title, audio_quality, tmp_dir, dest_dir = interactive_prompt()
    else:
        title = args.title
        audio_quality = args.audio_quality if args.audio_quality is not None else "320"
        tmp_dir = args.tmp_dir
        dest_dir = args.dest_dir

    downloader = VideoDownloader(tmp_dir=tmp_dir, dest_dir=dest_dir)
    downloader.process(title)
