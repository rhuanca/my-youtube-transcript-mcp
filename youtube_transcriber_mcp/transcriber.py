import logging
import os

from youtube_transcriber_mcp import config
from youtube_transcriber_mcp import utils
from youtube_transcriber_mcp.strategies import youtube_api, whisper_fallback
from youtube_transcriber_mcp.strategies.youtube_api import (
    CaptionsNotAvailableError,
    YouTubeAPIError,
)

logger = logging.getLogger(__name__)


def transcribe_youtube(url: str) -> dict:
    """
    Main entry point. Orchestrates the dual-strategy transcription.
    """
    # Step 1: Validate URL and extract video ID
    try:
        video_id = utils.extract_video_id(url)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    logger.info("Transcribing video ID: %s", video_id)

    result = None
    video_title = None

    # Step 2: Try YouTube Data API if key is configured
    if config.YOUTUBE_API_KEY:
        logger.info("Attempting primary strategy: YouTube Data API v3")
        try:
            result = youtube_api.fetch_captions(video_id)
            logger.info("Primary strategy succeeded (source: youtube_api)")
        except CaptionsNotAvailableError as exc:
            logger.info("Captions not available, falling back to Whisper: %s", exc)
        except YouTubeAPIError as exc:
            logger.warning("YouTube API error, falling back to Whisper: %s", exc)
    else:
        logger.info("YOUTUBE_API_KEY not set, skipping primary strategy")

    # Step 3: Fallback to Whisper if primary failed or was skipped
    if result is None:
        video_title = video_title or video_id
        logger.info("Attempting fallback strategy: yt-dlp + Whisper")
        try:
            result = whisper_fallback.transcribe_with_whisper(video_id, video_title)
            logger.info("Fallback strategy succeeded (source: whisper_fallback)")
        except Exception as exc:
            logger.error("Whisper fallback failed: %s", exc)
            return {"status": "error", "message": str(exc)}

    # Step 4: Save transcript to file
    title = result["title"]
    text = result["text"]

    transcripts_dir = os.path.abspath(config.TRANSCRIPTS_DIR)
    os.makedirs(transcripts_dir, exist_ok=True)

    filename = utils.sanitize_filename(title) + ".txt"
    transcript_path = os.path.join(transcripts_dir, filename)

    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(text)

    logger.info("Transcript saved to: %s", transcript_path)

    # Step 5: Return success response
    word_count = len(text.split())
    return {
        "status": "success",
        "title": title,
        "transcript_path": transcript_path,
        "source": result["source"],
        "word_count": word_count,
        "language": result["language"],
    }
