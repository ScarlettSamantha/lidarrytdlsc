from typing import Optional
import acoustid
import musicbrainzngs
from os import environ
from mutagen.id3 import ID3
from mutagen.id3._frames import TIT2, TPE1, TXXX, APIC
from mutagen.id3._util import error

# Initialize MusicBrainz with your user agent details
musicbrainzngs.set_useragent("MyMusicTagger", "0.1", "your-email@example.com")

length_of_api_key: int = 10

def detect_and_update_tags(file_path, api_key: str, thumbnail_path: Optional[str] = None, **kwargs) -> bool:
    if environ['ACOUST_ID_ENABLE'] is True:
        return False
    
    if environ['ACOUST_ID_API'].__len__() != length_of_api_key:
        print(f"Invalid Acout ID API key, must be {environ['ACOUST_ID_API'].__len__()} length")
        return False
    
    try:
        # Use pyacoustid to match the audio file
        results = acoustid.match(api_key, file_path)
        
        # Process the results; typically, the best match is the first one.
        for score, recording_id, title, artist in results:
            print(f"Detected: Score={score}, Title='{title}', Artist='{artist}', RecordingID={recording_id}")
            
            # Optional: Query MusicBrainz for more details using the recording_id
            try:
                mb_result = musicbrainzngs.get_recording_by_id(recording_id, includes=["artists", "releases"])
                print("MusicBrainz data:", mb_result.get("recording", {}))
            except Exception as mb_exc:
                print("MusicBrainz query failed:", mb_exc)
            
            # Update the MP3 file's metadata using mutagen's ID3 interface
            try:
                audio = ID3(file_path)
            except error:
                audio = ID3()
            
            # Set standard tags for title and artist
            audio.setall("TIT2", [TIT2(encoding=3, text=title)])
            audio.setall("TPE1", [TPE1(encoding=3, text=artist)])
            
            # Add any extra keyword arguments as custom TXXX frames
            for key, value in kwargs.items():
                audio.add(TXXX(encoding=3, desc=key, text=str(value)))
            
            # If a thumbnail image is provided, add it as cover art (APIC frame)
            if thumbnail_path:
                try:
                    with open(thumbnail_path, "rb") as img:
                        img_data = img.read()
                    # Adjust the mime type if your image is not JPEG
                    audio.add(APIC(
                        encoding=3,
                        mime='image/jpeg',  # Change to 'image/png' if needed
                        type=3,             # 3 is for the cover (front) image
                        desc="Cover",
                        data=img_data
                    ))
                except Exception as thumb_exc:
                    print(f"Failed to add thumbnail: {thumb_exc}")
            
            # Save all changes back to the file
            audio.save(file_path)
            print(f"Updated tags for '{file_path}'")
            break  # Update using the first (best) match and exit the loop

    except acoustid.AcoustidError as e:
        print(f"Error during acoustic fingerprinting: {e}")
    return True
