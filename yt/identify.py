import asyncio
import json
import requests
import logging
from typing import Optional
from mutagen.id3 import ID3
from mutagen.id3._util import error
from mutagen.id3._frames import TIT2, TPE1, TALB, TDRC, TCON, TXXX, APIC

logging.basicConfig(level=logging.INFO, format="[%(name)s] | %(asctime)s.%(msecs)03d - %(levelname)s - %(message)s", datefmt='%H:%M:%S')
logger = logging.getLogger("identify")


def detect_and_update_tags(file_path: str, thumbnail_path: Optional[str] = None, logger: logging.Logger = logger, **kwargs) -> bool:
    """
    Detects song metadata using ShazamIO and updates the MP3 file's ID3 tags.
    Standard tags (Title, Artist, Album, etc.) are updated to ensure compatibility with
    file managers (like Dolphin) that expect common frames. Additional metadata (like the 
    MusicBrainz ID) is stored as custom TXXX frames.
    """
    # Ensure the file has an .mp3 extension
    file_path = file_path if file_path.endswith(".mp3") else file_path + ".mp3"
    logger = logger.getChild("identification")
    
    async def recognize_and_update():
        from shazamio import Shazam  # Ensure shazamio is installed
        logger.info(f"Searching info for {file_path}...")
        shazam = Shazam()
        result = await shazam.recognize(file_path)
        
        track = result.get("track", {})
        title = track.get("title")
        artist = track.get("subtitle")
        if not title or not artist:
            logger.warning("Could not identify the track properly.")
            return False
        
        logger.info(f"Detected: Title='{title}', Artist='{artist}'")
        
        # Extract additional metadata
        album = None
        label = None
        release_date = track.get("releasedate")
        genre = track.get("genres", {}).get("primary")
        isrc = track.get("isrc")
        track_url = track.get("url")
        share_text = track.get("share", {}).get("text")
        hub = track.get("hub")
        joecolor = track.get("images", {}).get("joecolor")
        # Use high-quality cover art if available
        coverart_url = track.get("images", {}).get("coverarthq") or track.get("images", {}).get("coverart")
        
        # Attempt to extract album, label, and released info from sections metadata
        sections = track.get("sections", [])
        for section in sections:
            if section.get("type", "").upper() == "SONG":
                metadata_list = section.get("metadata", [])
                for metadata in metadata_list:
                    meta_title = metadata.get("title", "").lower()
                    if meta_title == "album":
                        album = metadata.get("text")
                    elif meta_title == "label":
                        label = metadata.get("text")
                    elif meta_title == "released":
                        release_date = metadata.get("text")
        
        # Open (or create) the ID3 tag object
        try:
            audio = ID3(file_path)
        except error:
            audio = ID3()
        
        # Update standard tags (ensure deletion of any existing frames first)
        audio.delall("TIT2")
        audio.add(TIT2(encoding=3, text=title))
        
        audio.delall("TPE1")
        audio.add(TPE1(encoding=3, text=artist))
        
        if album:
            audio.delall("TALB")
            audio.add(TALB(encoding=3, text=album))
        
        if release_date:
            audio.delall("TDRC")
            audio.add(TDRC(encoding=3, text=release_date))
        
        if genre:
            audio.delall("TCON")
            audio.add(TCON(encoding=3, text=genre))
        
        # Add extra metadata as TXXX (custom) frames
        if isrc:
            audio.delall("TXXX:ISRC")
            audio.add(TXXX(encoding=3, desc="ISRC", text=isrc))
        if label:
            audio.delall("TXXX:Label")
            audio.add(TXXX(encoding=3, desc="Label", text=label))
        if track_url:
            audio.delall("TXXX:Track URL")
            audio.add(TXXX(encoding=3, desc="Track URL", text=track_url))
        if share_text:
            audio.delall("TXXX:Share Text")
            audio.add(TXXX(encoding=3, desc="Share Text", text=share_text))
        if hub:
            audio.delall("TXXX:Hub Info")
            audio.add(TXXX(encoding=3, desc="Hub Info", text=json.dumps(hub)))
        if joecolor:
            audio.delall("TXXX:JoeColor")
            audio.add(TXXX(encoding=3, desc="JoeColor", text=joecolor))
        
        # Add any extra keyword arguments as custom TXXX frames
        for key, value in kwargs.items():
            audio.delall(f"TXXX:{key}")
            audio.add(TXXX(encoding=3, desc=key, text=str(value)))
        
        # Subfunction: Query MusicBrainz for a recording ID using the ISRC
        def fetch_musicbrainz_id(isrc_code: str) -> Optional[str]:
            mb_url = f"https://musicbrainz.org/ws/2/recording/?query=isrc:{isrc_code}&fmt=json"
            headers = {"User-Agent": "YourAppName/1.0 ( your-email@example.com )"}
            try:
                mb_response = requests.get(mb_url, headers=headers)
                if mb_response.status_code == 200:
                    mb_data = mb_response.json()
                    recordings = mb_data.get("recordings", [])
                    if recordings:
                        return recordings[0]["id"]
                    else:
                        logging.warning("No MusicBrainz recordings found for this ISRC.")
                        return None
                else:
                    logging.error(f"MusicBrainz query failed with status code: {mb_response.status_code}")
                    return None
            except Exception as e:
                logging.error(f"Error querying MusicBrainz: {e}")
                return None
        
        # If ISRC is available, add the MusicBrainz recording ID as a custom tag.
        if isrc:
            mbid = fetch_musicbrainz_id(isrc)
            if mbid:
                audio.delall("TXXX:MusicBrainz Track Id")
                audio.add(TXXX(encoding=3, desc="MusicBrainz Track Id", text=mbid))
                logging.info(f"Added MusicBrainz ID: {mbid}")
        
        # Add cover art: prefer the local thumbnail if provided; otherwise, download from coverart_url.
        if thumbnail_path:
            try:
                with open(thumbnail_path, "rb") as img:
                    img_data = img.read()
                audio.delall("APIC")
                audio.add(APIC(
                    encoding=3,
                    mime="image/jpeg",  # Adjust if you have a PNG thumbnail
                    type=3,             # 3 is for the front cover image
                    desc="Cover",
                    data=img_data
                ))
            except Exception as thumb_exc:
                logging.error(f"Failed to add thumbnail from path: {thumb_exc}")
        elif coverart_url:
            try:
                r = requests.get(coverart_url)
                if r.status_code == 200:
                    img_data = r.content
                    # Use the Content-Type header if available; otherwise, default to image/jpeg.
                    mime = r.headers.get("Content-Type", "image/jpeg")
                    audio.delall("APIC")
                    audio.add(APIC(
                        encoding=3,
                        mime=mime,
                        type=3,
                        desc="Cover",
                        data=img_data
                    ))
                else:
                    logging.info(f"Failed to download cover art, status code {r.status_code}")
            except Exception as e:
                logging.error(f"Failed to download cover art: {e}")
        
        # Save all changes back to the file using ID3v2.3 for better compatibility (e.g., with Dolphin)
        audio.save(file_path, v2_version=3)
        logging.info(f"Updated tags for '{file_path}'")
        return True

    try:
        # Run the async function in a synchronous context.
        return asyncio.run(recognize_and_update())
    except Exception as exc:
        logging.critical(f"An error occurred: {exc}")
        return False


# Example usage:
if __name__ == "__main__":
    # Replace 'your_song.mp3' with your actual file path.
    success = detect_and_update_tags("your_song.mp3")
    logger.info("Operation successful: success")
