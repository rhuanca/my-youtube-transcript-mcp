from fastmcp import FastMCP
from youtube_transcriber_mcp.transcriber import transcribe_youtube as _transcribe

mcp = FastMCP("youtube-transcriber")


@mcp.tool()
def transcribe_youtube(url: str) -> dict:
    """
    Transcribe a YouTube video and save the result to a .txt file.

    Args:
        url: Full YouTube video URL.
             Supported formats:
             - https://www.youtube.com/watch?v=VIDEO_ID
             - https://youtu.be/VIDEO_ID
             - https://www.youtube.com/shorts/VIDEO_ID

    Returns:
        On success:
          {
            "status": "success",
            "title": "Video title",
            "transcript_path": "/absolute/path/to/transcript.txt",
            "source": "youtube_api" or "whisper_fallback",
            "word_count": 1234,
            "language": "en"
          }
        On failure:
          {
            "status": "error",
            "message": "Human-readable explanation"
          }
    """
    return _transcribe(url)
