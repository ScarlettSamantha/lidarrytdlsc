import logging
import pprint
import re
from typing import Tuple
from rapidfuzz import fuzz  # pyright: ignore[reportMissingImports]

import helper
from models.video import VideoData

# Configure logging at the module level if you haven't already
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def compare_video(
    query_title: str,
    video: VideoData,
    fuzzy_score_multiplier: float = 0.9,
    view_threshold: int = 1000,
    boost_official: int = 10,         # + when "official" is in the title
    boost_music: int = 5,            # + when "music" is in the title
    boost_duration: int = 5,         # + when in preferred duration range
    boost_ultra_duration: int = 100,
    penalty_performance: int = 10,    # - when performance keywords appear
    boost_viewers: int = 5,          # + when view count above threshold
    penalty_cover: int = 20,         # - when "cover" is present (not in query)
    penalty_live: int = 40,          # - when "live"/"concert"/"session" is present (not in query)
    penalty_album: int = 10,         # - when "album"/"ep" is present
    penalty_pointless_words: int = 10,# - for "slowed", "reverb", etc.
    penalty_reaction: int = 100,     # - for "reaction", "analysis", etc.
    boost_lyrics: int = 10,          # + for "lyric"/"lyrics"
    boost_per_10000: float = 0.01,   # + (views / 10,000 * this)
    boost_official_named_channel: int = 20,  # + if channel name is in the title
    boost_age_factor: float = 0.5,   # + per year old the video is
    min_time: int = 120,
    ultra_min_time: int = 60,
    ultra_max_time: int = 1200,
    max_time: int = 600
) -> Tuple[float, str]:
    """
    Compare a query title with a video's title using fuzzy matching, and adjust
    the score with additional boosts/penalties based on video metadata.
    Logs each scoring step for debugging.

    Returns: (final_score, cleaned_video_title)
    """

    # --- 0) Clean the video title: strip non-ASCII + remove punctuation + lowercase ---
    raw_video_title = video.title or ""  # handle None-safely
    # Strip out non-ASCII
    ascii_only = raw_video_title.encode('ascii', errors='ignore').decode('ascii', errors='ignore')
    # Remove punctuation (keeping letters, numbers, whitespace)
    video_title = re.sub(r'[^a-zA-Z0-9\s]+', '', ascii_only).lower()

    # Get other video metadata
    duration_seconds = helper.to_seconds(video.duration)
    views = helper.fix_viewers(video.viewCount.text)

    # For debug
    score_steps = []

    logger.debug("Comparing query_title=%r with video_title=%r", query_title, video_title)
    logger.debug("Raw video metadata: %s", pprint.pformat(video))

    # Initialize score
    score = 0.0

    # --- STEP 2) Official & music boosts (as in your original code) ---
    if 'official' in video_title:
        old_score = score
        score += boost_official
        score_steps.append((
            "Found 'official' in title => boost",
            f"+ {boost_official}",
            score
        ))
        # Optional: remove 'official' so it doesn't affect later steps
        video_title = video_title.replace("official", "")

    if 'music' in video_title:
        old_score = score
        score += boost_music
        score_steps.append((
            "Found 'music' in title => boost",
            f"+ {boost_music}",
            score
        ))
        # Optional: remove 'music' so it doesn't affect later steps
        video_title = video_title.replace("music", "")

    # --- STEP 1) Initial fuzzy matching score ---
    #   (Original code was a bit unclear; here we multiply exactly once)
    raw_fuzz = fuzz.ratio(query_title.lower(), video_title)
    initial_score = raw_fuzz * fuzzy_score_multiplier
    score += initial_score
    score_steps.append((
        f"Initial fuzzy score * multiplier={fuzzy_score_multiplier}",
        f"= {initial_score:.2f}",
        score
    ))

    # --- STEP 1.5) Small bonus for “same words in same order” + length ratio ---
    query_words = query_title.lower().split()
    vid_words   = video_title.split()

    matched_in_order = 0
    i, j = 0, 0
    while i < len(query_words) and j < len(vid_words):
        if query_words[i] == vid_words[j]:
            matched_in_order += 1
            i += 1
            j += 1
        else:
            j += 1

    fraction_matched = (matched_in_order / len(query_words)) if query_words else 0.0
    length_ratio = (len(vid_words) / len(query_words)) if query_words else 1.0

    # Example threshold: ≥50% same-order matches AND length ratio ~1
    if fraction_matched >= 0.5 and 0.7 <= length_ratio <= 1.3:
        old_score = score
        score += 1
        score_steps.append((
            "STEP 1.5: Same-order match >= 50% & length ratio ~1 => small bonus",
            "+ 1",
            score
        ))

    # --- STEP 3) Performance penalty ---
    performance_keywords = ["perform", "performs", "performance", "performed", "instrumental", "live", "acoustic"]
    if any(word.lower() in video_title for word in performance_keywords):
        old_score = score
        score -= penalty_performance
        score_steps.append((
            "Found performance-related keyword => penalty",
            f"- {penalty_performance}",
            score
        ))

    # --- STEP 4) Cover penalty ---
    cover_synonyms = ["cover", "rendition", "remake"]
    if any(cov in video_title for cov in cover_synonyms):
        # If not also in the query => apply penalty
        if not any(cov.lower() in query_title.lower() for cov in cover_synonyms):
            old_score = score
            score -= penalty_cover
            score_steps.append((
                "Found 'cover'/'rendition'/'remake' in title (not in query) => penalty",
                f"- {penalty_cover}",
                score
            ))

    # --- STEP 5) Live penalty ---
    live_synonyms = ["live", "concert", "session", "acoustic", "unplugged", "multicam", "livestream", "broadcast", "live-stream"]
    if any(liv.lower() in video_title for liv in live_synonyms):
        # If not also in the query => apply penalty
        if not any(liv.lower() in query_title.lower() for liv in live_synonyms):
            old_score = score
            score -= penalty_live
            score_steps.append((
                "Found 'live'/synonym in title (not in query) => penalty",
                f"- {penalty_live}",
                score
            ))

    # --- STEP 6) Reaction/analysis penalty ---
    reaction_synonyms = ["reaction", "analysis", "reacts", "react", "responds", "review"]
    if any(word in video_title for word in reaction_synonyms):
        old_score = score
        score -= penalty_reaction
        score_steps.append((
            "Found reaction/analysis keyword => penalty",
            f"- {penalty_reaction}",
            score
        ))

    # --- STEP 7) Slowed/reverb penalty ---
    slowed_synonyms = ["slowed", "reverb", "reverbed", "slow"]
    if any(word in video_title for word in slowed_synonyms):
        old_score = score
        score -= penalty_pointless_words
        score_steps.append((
            "Found slow/reverb keyword => penalty",
            f"- {penalty_pointless_words}",
            score
        ))

    # --- STEP 8) Album penalty ---
    album_synonyms = ["album", "albums", "ep"]
    if any(word in video_title for word in album_synonyms):
        old_score = score
        score -= penalty_album
        score_steps.append((
            "Found album keyword => penalty",
            f"- {penalty_album}",
            score
        ))

    # --- STEP 9) Lyrics boost ---
    lyrics_synonyms = ["lyric", "lyrics"]
    if any(word in video_title for word in lyrics_synonyms):
        old_score = score
        score += boost_lyrics
        score_steps.append((
            "Found lyrics keyword => boost",
            f"+ {boost_lyrics}",
            score
        ))

    # --- STEP 10) Channel name in title => official boost ---
    #   (We look for any chunk of the video's title in the channel name)
    if any(part.lower() in video.channel.name.lower() for part in video_title.split()):
        old_score = score
        score += boost_official_named_channel
        score_steps.append((
            "Channel name found in title => official boost",
            f"+ {boost_official_named_channel}",
            score
        ))

    # --- STEP 11) Duration-based boost ---
    if min_time <= duration_seconds <= max_time:
        old_score = score
        score += boost_duration
        score_steps.append((
            f"Duration in {min_time}-{max_time}s range => boost",
            f"+ {boost_duration}",
            score
        ))
        
        # --- STEP 11.5) Duration-based boost ---
    if ultra_min_time >= duration_seconds >= ultra_max_time:
        old_score = score
        score -= boost_ultra_duration
        score_steps.append((
            f"Duration in {min_time}-{max_time}s range => boost way to long or short",
            f"+ {boost_duration}",
            score
        ))

    # --- STEP 12) View count threshold boost ---
    if views > view_threshold:
        old_score = score
        score += boost_viewers
        score_steps.append((
            f"View count ({views}) > threshold ({view_threshold}) => boost",
            f"+ {boost_viewers}",
            score
        ))

    # --- STEP 13) Additional per-10k views boost ---
    if views > 0:
        extra_boost = (views / 10000.0) * boost_per_10000
        # For example, ensure a minimum of +10
        add_val = min(extra_boost, 10)
        old_score = score
        score += add_val
        score_steps.append((
            f"Boost per 10k views => {extra_boost:.2f}",
            f"+ {add_val:.2f} (min 10)",
            score
        ))

    # --- STEP 14) Age-based scoring (Video's published time) ---
    video_age_years = 0
    if video.publishedTime:
        match_years = re.search(r'(\d+)\s+year', video.publishedTime.lower())
        if match_years:
            video_age_years = int(match_years.group(1))

    if video_age_years > 0:
        age_boost = video_age_years * boost_age_factor
        old_score = score
        score += age_boost
        score_steps.append((
            f"Video age is {video_age_years} year(s) => age-based boost",
            f"+ {age_boost:.2f}",
            score
        ))

    # === Final debugging table ===
    logger.debug("\n\n=== Score Debug Table for: %s ===", video_title)
    logger.debug("| Step # | Description                                        | Change       | Resulting Score |")
    logger.debug("|--------|----------------------------------------------------|--------------|-----------------|")
    for idx, (description, change, resulting_score) in enumerate(score_steps, start=1):
        # If we see '1.5' in the description, manually print "1.5" for that row
        step_label = "1.5" if "1.5" in description else str(idx)
        logger.debug(
            "| %6s | %-50s | %-12s | %15.2f |",
            step_label, description[:50], change, resulting_score
        )

    logger.debug("FINAL SCORE for '%s': %.2f \n\n", video_title, score)

    return score, video_title
