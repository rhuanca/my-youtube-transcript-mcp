import logging
import os

from youtube_transcriber_mcp import config
from youtube_transcriber_mcp import utils
from youtube_transcriber_mcp.strategies import youtube_api, whisper_fallback

logger = logging.getLogger(__name__)


def _save_transcript(title: str, text: str) -> str:
    """Save transcript text to a .txt file and return the absolute path."""
    transcripts_dir = os.path.abspath(config.TRANSCRIPTS_DIR)
    os.makedirs(transcripts_dir, exist_ok=True)
    filename = utils.sanitize_filename(title) + ".txt"
    transcript_path = os.path.join(transcripts_dir, filename)
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(text)
    logger.info("Transcript saved to: %s", transcript_path)
    return transcript_path


def transcribe_via_youtube_api(url: str) -> dict:
    """
    Transcribe using the YouTube Data API v3 (primary strategy).
    Returns an error dict if YOUTUBE_API_KEY is not set, the URL is invalid,
    captions are unavailable, or the API call fails.
    """
    if not config.YOUTUBE_API_KEY:
        return {
            "status": "error",
            "message": "YOUTUBE_API_KEY is not set. Set the environment variable and retry, or use transcribe_youtube_whisper instead.",
        }

    try:
        video_id = utils.extract_video_id(url)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    logger.info("Fetching captions via YouTube Data API v3 for video: %s", video_id)
    try:
        result = youtube_api.fetch_captions(video_id)
    except youtube_api.CaptionsNotAvailableError as exc:
        return {
            "status": "error",
            "code": "captions_unavailable",
            "message": str(exc),
            "suggestion": "No captions found for this video. Use transcribe_youtube_whisper to transcribe via local audio instead.",
        }
    except youtube_api.YouTubeAPIError as exc:
        return {
            "status": "error",
            "code": "api_error",
            "message": str(exc),
            "suggestion": "YouTube API call failed. Use transcribe_youtube_whisper to transcribe via local audio instead.",
        }

    transcript_path = _save_transcript(result["title"], result["text"])
    return {
        "status": "success",
        "title": result["title"],
        "transcript_path": transcript_path,
        "source": "youtube_api",
        "word_count": len(result["text"].split()),
        "language": result["language"],
    }


def transcribe_via_whisper(url: str) -> dict:
    """
    Transcribe by downloading audio with yt-dlp and running OpenAI Whisper locally (fallback strategy).
    Works for any public YouTube video regardless of caption availability. Requires ffmpeg.
    """
    try:
        video_id = utils.extract_video_id(url)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    logger.info("Transcribing via yt-dlp + Whisper for video: %s", video_id)
    try:
        result = whisper_fallback.transcribe_with_whisper(video_id, video_title=video_id)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    transcript_path = _save_transcript(result["title"], result["text"])
    return {
        "status": "success",
        "title": result["title"],
        "transcript_path": transcript_path,
        "source": "whisper_fallback",
        "word_count": len(result["text"].split()),
        "language": result["language"],
    }
