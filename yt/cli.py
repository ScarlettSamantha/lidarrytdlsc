import questionary
from vars import quality_presets

def interactive_prompt():
    """Prompt the user for inputs interactively using Questionary."""
    mode = questionary.select(
        "Choose download mode:",
        choices=[
            "Search by Title",
            "Download by Video ID",
            "Download Playlist"
        ]
    ).ask()

    # Provide a default value depending on mode.
    if mode == "Search by Title":
        default_value = "Whiplash - Architects"
        prompt_text = "Enter video title:"
    elif mode == "Download by Video ID":
        default_value = "dQw4w9WgXcQ"  # example default video ID
        prompt_text = "Enter video ID:"
    elif mode == "Download Playlist":
        default_value = "https://www.youtube.com/playlist?list=PLXXXXXX"  # example default playlist URL
        prompt_text = "Enter playlist URL:"
    else:
        default_value = ""
        prompt_text = "Enter value:"

    user_input = questionary.text(prompt_text, default=default_value).ask()

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

    return user_input, audio_quality, tmp_dir, dest_dir, identify, mode
