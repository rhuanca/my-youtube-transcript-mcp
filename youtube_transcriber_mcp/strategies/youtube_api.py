import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from youtube_transcriber_mcp import config
from youtube_transcriber_mcp import utils

logger = logging.getLogger(__name__)


class CaptionsNotAvailableError(Exception):
    """Raised when no downloadable caption track exists for this video."""


class YouTubeAPIError(Exception):
    """Raised on API quota, key, or connectivity errors."""


def fetch_captions(video_id: str) -> dict:
    """
    Fetch the official captions for a YouTube video using the YouTube Data API v3.
    """
    try:
        youtube = build("youtube", "v3", developerKey=config.YOUTUBE_API_KEY)
    except Exception as exc:
        raise YouTubeAPIError(f"Failed to build YouTube API client: {exc}") from exc

    # Step 2: Fetch video title
    try:
        video_response = youtube.videos().list(part="snippet", id=video_id).execute()
    except HttpError as exc:
        status = exc.resp.status
        if status in (403, 429):
            raise YouTubeAPIError(f"YouTube API quota/auth error (HTTP {status})") from exc
        raise YouTubeAPIError(f"YouTube API error fetching video info: {exc}") from exc

    items = video_response.get("items", [])
    if not items:
        raise CaptionsNotAvailableError(f"Video {video_id!r} not found or not accessible.")
    title = items[0]["snippet"]["title"]

    # Step 3: List caption tracks
    try:
        captions_response = youtube.captions().list(part="snippet", videoId=video_id).execute()
    except HttpError as exc:
        status = exc.resp.status
        if status == 403:
            raise CaptionsNotAvailableError(
                f"Access denied listing captions for {video_id!r} (HTTP 403)."
            ) from exc
        if status in (429,):
            raise YouTubeAPIError(f"YouTube API quota exceeded (HTTP {status})") from exc
        raise YouTubeAPIError(f"YouTube API error listing captions: {exc}") from exc

    caption_items = captions_response.get("items", [])
    if not caption_items:
        raise CaptionsNotAvailableError(f"No caption tracks available for video {video_id!r}.")

    # Step 4: Select best matching track
    preferred_lang = config.CAPTION_LANGUAGE
    track_id = None
    language_used = None

    for item in caption_items:
        lang = item["snippet"]["language"]
        if lang == preferred_lang:
            track_id = item["id"]
            language_used = lang
            break

    if track_id is None:
        for item in caption_items:
            lang = item["snippet"]["language"]
            if lang == "en":
                track_id = item["id"]
                language_used = lang
                break

    if track_id is None:
        raise CaptionsNotAvailableError(
            f"No caption track found for language {preferred_lang!r} or 'en' "
            f"for video {video_id!r}."
        )

    logger.info("Selected caption track %r (language: %s)", track_id, language_used)

    # Step 5: Download the caption track
    try:
        srt_bytes = youtube.captions().download(id=track_id, tfmt="srt").execute()
    except HttpError as exc:
        status = exc.resp.status
        if status == 403:
            raise CaptionsNotAvailableError(
                f"Cannot download captions for {video_id!r} (HTTP 403 — likely auto-generated)."
            ) from exc
        if status in (429,):
            raise YouTubeAPIError(f"YouTube API quota exceeded downloading captions (HTTP {status})") from exc
        raise YouTubeAPIError(f"YouTube API error downloading captions: {exc}") from exc

    if isinstance(srt_bytes, bytes):
        srt_content = srt_bytes.decode("utf-8", errors="replace")
    else:
        srt_content = str(srt_bytes)

    # Step 6: Parse SRT to plain text
    text = utils.parse_srt(srt_content)

    # Step 7: Return result
    return {
        "title": title,
        "text": text,
        "language": language_used,
        "source": "youtube_api",
    }
