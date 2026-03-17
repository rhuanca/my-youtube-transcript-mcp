from fastmcp import FastMCP
from youtube_transcriber_mcp.transcriber import (
    transcribe_via_youtube_api,
    transcribe_via_whisper,
)

mcp = FastMCP(
    "youtube-transcriber",
    instructions=(
        "This server transcribes YouTube videos using two independent tools.\n"
        "\n"
        "Preferred workflow:\n"
        "1. Always call `transcribe_youtube_api` first — it is fast and uses official captions.\n"
        "2. If it returns status 'error' (e.g. captions unavailable, API key not set, quota exceeded),\n"
        "   call `transcribe_youtube_whisper` as the fallback — it downloads the audio and transcribes\n"
        "   locally using OpenAI Whisper. It is slower but works for any public video.\n"
        "\n"
        "Never call both tools for the same URL unless the first one failed.\n"
        "Always report to the user which strategy was used and where the transcript was saved."
    ),
)


@mcp.tool()
def transcribe_youtube_api(url: str) -> dict:
    """
    Transcribe a YouTube video using the YouTube Data API v3.

    Fetches the official caption track — fast, accurate, and requires no audio processing.
    Requires the YOUTUBE_API_KEY environment variable to be set.

    Call this tool first. If it returns an error, call transcribe_youtube_whisper instead.

    Args:
        url: Full YouTube video URL (watch, youtu.be, or shorts format).

    Returns:
        On success:  { "status": "success", "title", "transcript", "source": "youtube_api", "word_count", "language" }
        On failure:  { "status": "error", "code", "message", "suggestion" }
    """
    return transcribe_via_youtube_api(url)


@mcp.tool()
def transcribe_youtube_whisper(url: str) -> dict:
    """
    Transcribe a YouTube video by downloading its audio and running OpenAI Whisper locally.

    Works for any public YouTube video regardless of caption availability.
    Does not require a YouTube API key. Requires ffmpeg to be installed.
    Slower than transcribe_youtube_api — use this as a fallback when that tool fails.

    Args:
        url: Full YouTube video URL (watch, youtu.be, or shorts format).

    Returns:
        On success:  { "status": "success", "title", "transcript", "source": "whisper_fallback", "word_count", "language" }
        On failure:  { "status": "error", "message" }
    """
    return transcribe_via_whisper(url)
