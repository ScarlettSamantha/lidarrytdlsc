import logging
import pprint
import re
from typing import Tuple, List, Any
from rapidfuzz import fuzz  # pyright: ignore[reportMissingImports]

import helper
from models.video import VideoData

# Configure logging at the module level if you haven't already
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def count_keywords(text: str, keywords: List[str]) -> int:
    """
    Count the total number of occurrences of any of the keywords in the given text.
    Matching is done on whole words in a case-insensitive manner.
    """
    total = 0
    for keyword in keywords:
        # Use regex with word boundaries and IGNORECASE flag.
        total += len(re.findall(r'\b' + re.escape(keyword) + r'\b', text, flags=re.IGNORECASE))
    return total


def compare_video(
    query_title: str,
    video: VideoData,
    fuzzy_score_multiplier: float = 0.9,
    view_threshold: int = 1000,
    boost_official: int = 10,         # + when "official" is in the title (applied once)
    boost_music: int = 5,             # + when "music" is in the title (applied once)
    boost_duration: int = 5,          # + when in preferred duration range
    boost_ultra_duration: int = 100,  # big penalty when duration is out of ultra bounds
    penalty_performance: int = 10,    # - per occurrence for performance-related keywords
    boost_viewers: int = 5,           # + when view count above threshold
    penalty_cover: int = 30,          # - per occurrence when cover-related keywords appear (if not in query)
    penalty_live: int = 40,           # - per occurrence when live-related keywords appear (if not in query)
    penalty_album: int = 10,          # - per occurrence for album-related keywords
    penalty_pointless_words: int = 10,# - per occurrence for "slowed", "reverb", etc.
    penalty_reaction: int = 100,      # - per occurrence for reaction/analysis keywords
    boost_lyrics: int = 10,           # + when lyric-related keywords appear (applied once)
    boost_per_10000: float = 0.03,    # + (views / 10,000 * this)
    boost_official_named_channel: int = 20,  # + if channel name is in the title (applied once)
    boost_age_factor: float = 0.5,    # + per year old the video is
    # New parameter for the title format boost:
    boost_title_format: int = 15,
    min_time: int = 120,
    ultra_min_time: int = 60,
    ultra_max_time: int = 1200,
    max_time: int = 600,
    debug_output_object: bool = False  # if True, return raw object (list of dicts) for debugging
) -> Tuple[float, str, Any]:
    """
    Compare a query title with a video's title using fuzzy matching and adjust
    the score with additional boosts/penalties based on video metadata.

    If debug_output_object is True, the third returned value is a raw Python object
    (a list of dictionaries) describing each scoring step.

    Returns:
      final_score (float),
      cleaned_video_title (str),
      debug_output (object) -> raw object if debug_output_object=True, else an empty list.
    """

    # --- Preserve the original title for regex checks ---
    raw_video_title = video.title or ""
    original_title = raw_video_title.strip()

    # --- Clean the video title for general processing ---
    # Remove punctuation except spaces and convert to lowercase.
    ascii_only = raw_video_title.encode("ascii", errors="ignore").decode("ascii", errors="ignore")
    video_title = re.sub(r"[^a-zA-Z0-9\s]+", "", ascii_only).lower()

    duration_seconds = helper.to_seconds(video.duration)
    views = helper.fix_viewers(video.viewCount.text if video.viewCount else "0")

    score_steps: List[dict] = []
    logger.debug("Comparing query_title=%r with video_title=%r", query_title, video_title)
    logger.debug("Raw video metadata: %s", pprint.pformat(video))

    score = 0.0

    # --- Boosts applied only once (then remove the term) ---
    if count_keywords(video_title, ["official"]) > 0:
        score += boost_official
        score_steps.append({
            "step": "Official boost",
            "description": "Found 'official' in title",
            "change": f"+ {boost_official}",
            "score": score,
        })
        video_title = re.sub(r"\bofficial\b", "", video_title, flags=re.IGNORECASE)

    if count_keywords(video_title, ["music"]) > 0:
        score += boost_music
        score_steps.append({
            "step": "Music boost",
            "description": "Found 'music' in title",
            "change": f"+ {boost_music}",
            "score": score,
        })
        video_title = re.sub(r"\bmusic\b", "", video_title, flags=re.IGNORECASE)

    # --- Initial fuzzy matching score ---
    raw_fuzz = fuzz.ratio(query_title.lower(), video_title)
    initial_score = raw_fuzz * fuzzy_score_multiplier
    score += initial_score
    score_steps.append({
        "step": "Initial fuzzy score",
        "description": f"Fuzzy ratio * multiplier ({fuzzy_score_multiplier})",
        "change": f"+ {initial_score:.2f}",
        "score": score,
    })

    # --- Same-order partial match bonus ---
    query_words = query_title.lower().split()
    vid_words = video_title.split()
    matched_in_order = 0
    i, j = 0, 0
    while i < len(query_words) and j < len(vid_words):
        if query_words[i] == vid_words[j]:
            matched_in_order += 1
            i += 1
            j += 1
        else:
            j += 1
    if query_words:
        fraction_matched = matched_in_order / len(query_words)
    else:
        fraction_matched = 0.0
    length_ratio = (len(vid_words) / len(query_words)) if query_words else 1.0
    if fraction_matched >= 0.5 and 0.7 <= length_ratio <= 1.3:
        score += 1
        score_steps.append({
            "step": "Same-order bonus",
            "description": ">=50% words match in order with reasonable length ratio",
            "change": "+ 1",
            "score": score,
        })

    # --- Penalty: Performance-related keywords (repeat penalty) ---
    performance_keywords = ["perform", "performs", "performance", "performed", "instrumental", "live", "acoustic"]
    performance_count = count_keywords(video_title, performance_keywords)
    if performance_count:
        penalty = penalty_performance * performance_count
        score -= penalty
        score_steps.append({
            "step": "Performance penalty",
            "description": f"Found performance-related keywords {performance_count} time(s)",
            "change": f"- {penalty_performance} * {performance_count} = -{penalty}",
            "score": score,
        })

    # --- Penalty: Cover-related keywords (apply only if not in query) ---
    cover_synonyms = ["cover", "rendition", "remake"]
    if count_keywords(query_title, cover_synonyms) == 0:
        cover_count = count_keywords(video_title, cover_synonyms)
        if cover_count:
            penalty = penalty_cover * cover_count
            score -= penalty
            score_steps.append({
                "step": "Cover penalty",
                "description": f"Found cover-related keywords {cover_count} time(s) (not in query)",
                "change": f"- {penalty_cover} * {cover_count} = -{penalty}",
                "score": score,
            })

    # --- Penalty: Live-related keywords (apply only if not in query) ---
    live_synonyms = [
        "live", "concert", "session", "acoustic", "unplugged", "multicam",
        "livestream", "broadcast", "live-stream", "playthrough", "adaptation", "transcription"
    ]
    if count_keywords(query_title, live_synonyms) == 0:
        live_count = count_keywords(video_title, live_synonyms)
        if live_count:
            penalty = penalty_live * live_count
            score -= penalty
            score_steps.append({
                "step": "Live penalty",
                "description": f"Found live-related keywords {live_count} time(s) (not in query)",
                "change": f"- {penalty_live} * {live_count} = -{penalty}",
                "score": score,
            })

    # --- Penalty: Reaction/analysis keywords ---
    reaction_synonyms = ["reaction", "analysis", "reacts", "react", "responds", "review", "playthrough"]
    reaction_count = count_keywords(video_title, reaction_synonyms)
    if reaction_count:
        penalty = penalty_reaction * reaction_count
        score -= penalty
        score_steps.append({
            "step": "Reaction penalty",
            "description": f"Found reaction/analysis keywords {reaction_count} time(s)",
            "change": f"- {penalty_reaction} * {reaction_count} = -{penalty}",
            "score": score,
        })

    # --- Penalty: Slowed/reverb keywords ---
    slowed_synonyms = ["slowed", "reverb", "reverbed", "slow"]
    slowed_count = count_keywords(video_title, slowed_synonyms)
    if slowed_count:
        penalty = penalty_pointless_words * slowed_count
        score -= penalty
        score_steps.append({
            "step": "Slowed/Reverb penalty",
            "description": f"Found slowed/reverb keywords {slowed_count} time(s)",
            "change": f"- {penalty_pointless_words} * {slowed_count} = -{penalty}",
            "score": score,
        })

    # --- Penalty: Album-related keywords ---
    album_synonyms = ["album", "albums", "ep"]
    album_count = count_keywords(video_title, album_synonyms)
    if album_count:
        penalty = penalty_album * album_count
        score -= penalty
        score_steps.append({
            "step": "Album penalty",
            "description": f"Found album-related keywords {album_count} time(s)",
            "change": f"- {penalty_album} * {album_count} = -{penalty}",
            "score": score,
        })

    # --- Boost: Lyrics keywords (applied once) ---
    if count_keywords(video_title, ["lyric", "lyrics"]) > 0:
        score += boost_lyrics
        score_steps.append({
            "step": "Lyrics boost",
            "description": "Found lyric/lyrics keyword in title",
            "change": f"+ {boost_lyrics}",
            "score": score,
        })

    # --- Boost: Uncensored keyword (applied once) ---
    if count_keywords(video_title, ["uncensored"]) > 0:
        score += boost_lyrics
        score_steps.append({
            "step": "Uncensored boost",
            "description": "Found 'uncensored' in title",
            "change": f"+ {boost_lyrics}",
            "score": score,
        })

    # --- Boost: Channel name in title ---
    if video.channel and any(word.lower() in video.channel.name.lower() for word in video_title.split()):
        score += boost_official_named_channel
        score_steps.append({
            "step": "Channel boost",
            "description": "Channel name found in title",
            "change": f"+ {boost_official_named_channel}",
            "score": score,
        })

    # --- Duration-based boost/penalty ---
    if min_time <= duration_seconds <= max_time:
        score += boost_duration
        score_steps.append({
            "step": "Duration boost",
            "description": f"Duration in {min_time}-{max_time}s",
            "change": f"+ {boost_duration}",
            "score": score,
        })

    if "behind the scenes" in video_title:
        score -= penalty_cover
        score_steps.append({
            "step": "Behind the Scenes penalty",
            "description": "Found 'behind the scenes' in title",
            "change": f"- {penalty_cover}",
            "score": score,
        })

    if duration_seconds < ultra_min_time or duration_seconds > ultra_max_time:
        score -= boost_ultra_duration
        score_steps.append({
            "step": "Ultra duration penalty",
            "description": f"Duration < {ultra_min_time}s or > {ultra_max_time}s",
            "change": f"- {boost_ultra_duration}",
            "score": score,
        })

    # --- View count boosts ---
    if views > view_threshold:
        score += boost_viewers
        score_steps.append({
            "step": "Viewers boost",
            "description": f"View count ({views}) > threshold ({view_threshold})",
            "change": f"+ {boost_viewers}",
            "score": score,
        })

    if views > 0:
        extra_boost = (views / 10000.0) * boost_per_10000
        add_val = min(extra_boost, 10)
        score += add_val
        score_steps.append({
            "step": "Per 10k views boost",
            "description": f"Boost per 10k views: {extra_boost:.2f} (capped at 10)",
            "change": f"+ {add_val:.2f}",
            "score": score,
        })

    # --- Age-based scoring ---
    video_age_years = 0
    if video.publishedTime:
        match = re.search(r"(\d+)\s+year", video.publishedTime.lower())
        if match:
            video_age_years = int(match.group(1))
    if video_age_years > 0:
        age_boost = video_age_years * boost_age_factor
        score += age_boost
        score_steps.append({
            "step": "Age boost",
            "description": f"Video age: {video_age_years} year(s)",
            "change": f"+ {age_boost:.2f}",
            "score": score,
        })

    # --- Title Format Boost ---
    # This regex checks for titles that match the pattern:
    # "Song Title - Artist (tag)" where the tag contains 'official'
    format_pattern = re.compile(
        r"^\s*(?P<song>(?:\w+\s+){1,6}\w+)\s*-\s*(?P<artist>(?:\w+\s+){0,2}\w+)\s*\((?P<tag>.*?official.*?)\)\s*$",
        flags=re.IGNORECASE
    )
    if format_pattern.match(original_title):
        score += boost_title_format
        score_steps.append({
            "step": "Title format boost",
            "description": "Title matches 'Song Title - Artist (tag)' pattern with 'official' in tag",
            "change": f"+ {boost_title_format}",
            "score": score,
        })

    # --- Final logging ---
    logger.debug("\n\n=== Score Debug Steps for: %s ===", video_title)
    for idx, step in enumerate(score_steps, start=1):
        logger.debug("Step %s: %s | Change: %s | Score: %.2f",
                     idx, step["description"], step["change"], step["score"])
    logger.debug("FINAL SCORE for '%s': %.2f", video_title, score)

    debug_output = score_steps if debug_output_object else []

    return score, video_title, debug_output