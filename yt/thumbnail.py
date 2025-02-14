from models.video import VideoData
from typing import Optional
import subprocess
import os
import helper
import requests
from io import BytesIO
from PIL import Image

class ThumbnailDownloader:
    
    def __init__(self, tmp_dir: str):
        self.tmp_dir: str = tmp_dir
    
    def download_thumbnail(self, video: VideoData, output_path: str, image_source: Optional[str] = None) -> Optional[str]:
        # If no image_source is provided, try to use the video's thumbnail.
        if image_source is None:
            thumbnail_url = None
            # Prefer richThumbnail if available.
            if hasattr(video, 'richThumbnail') and video.richThumbnail and hasattr(video.richThumbnail, 'url'):
                thumbnail_url = video.richThumbnail.url
            # Otherwise, fallback to the first thumbnail in the thumbnails list.
            elif hasattr(video, 'thumbnails') and video.thumbnails:
                thumbnail_obj = video.thumbnails[0]
                thumbnail_url = getattr(thumbnail_obj, 'url', None)
            
            if thumbnail_url:
                print("No image source provided; attempting to use video thumbnail as cover art.")
                # Use the helper function to download and convert the image.
                converted_path, dimensions = helper.download_and_convert_image(
                    thumbnail_url, self.tmp_dir, f"{video.id}_thumbnail.jpg"
                )
                if converted_path:
                    image_source = converted_path
                else:
                    print("Failed to obtain a valid image source from the thumbnail.")

        # If still no image source, return None.


        # Otherwise, use ffmpeg to embed the image.
        embedded_audio = output_path + "_embedded.mp3"
        if not image_source:
            return embedded_audio
        cmd = ["ffmpeg", "-y", "-i", output_path]
        
        # Add the image as a second input.
        cmd.extend(["-i", image_source])
        
        # Map the audio and image streams.
        cmd.extend(["-map", "0", "-map", "1"])
        
        # Copy audio without re-encoding.
        cmd.extend(["-c:a", "copy"])
        
        # Encode the image as JPEG.
        cmd.extend(["-c:v", "mjpeg", "-q:v", "2"])
        
        # Write ID3v2 metadata.
        cmd.extend(["-id3v2_version", "3", "-metadata:s:v", "title=Cover", "-metadata:s:v", "comment=Cover (front)"])
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return embedded_audio  # Return the path to the new file on success.
        except Exception as e:
            print("Error embedding metadata/image:", e)
            return embedded_audio  # Fallback return.
        
        
def download_and_convert_image(url, dest_dir, dest_filename=None):
    """
    Downloads an image from the given URL, converts it to JPEG format (if necessary),
    detects its dimensions, and saves it in dest_dir.

    :param url: URL of the image.
    :param dest_dir: Directory where the image will be saved.
    :param dest_filename: Optional filename for the saved image.
    :return: Tuple (path_to_image, (width, height)) if successful; otherwise (None, (0,0)).
    """
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
