import logging
import os
import shutil

from youtube_transcriber_mcp import config
from youtube_transcriber_mcp import utils

logger = logging.getLogger(__name__)

_whisper_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        logger.info("Loading Whisper model: %s", config.WHISPER_MODEL)
        _whisper_model = whisper.load_model(config.WHISPER_MODEL)
    return _whisper_model


def transcribe_with_whisper(video_id: str, video_title: str) -> dict:
    """
    Download audio with yt-dlp and transcribe locally with OpenAI Whisper.
    """
    # Step 1: Check ffmpeg availability
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "ffmpeg is required for the Whisper fallback. Install: sudo apt install ffmpeg"
        )

    # Step 2: Sanitize title for filesystem use
    sanitized_title = utils.sanitize_filename(video_title) if video_title else video_id

    # Step 3: Set up temp directory and download audio
    tmp_dir = "/tmp/yt_transcriber"
    os.makedirs(tmp_dir, exist_ok=True)

    audio_path = os.path.join(tmp_dir, f"{sanitized_title}.mp3")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(tmp_dir, f"{sanitized_title}.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
        "quiet": True,
        "no_warnings": True,
    }

    logger.info("Downloading audio for video %r via yt-dlp", video_id)
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
    except Exception as exc:
        raise RuntimeError(f"yt-dlp failed to download audio: {exc}") from exc

    # Step 4 & 5: Load model and transcribe
    try:
        model = _get_whisper_model()
        logger.info("Transcribing audio with Whisper model %r", config.WHISPER_MODEL)
        result = model.transcribe(audio_path)
    finally:
        # Step 6: Always clean up temp audio
        if os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info("Deleted temp audio file: %s", audio_path)

    # Step 7: Return result
    return {
        "title": video_title,
        "text": result["text"].strip(),
        "language": result.get("language", "unknown"),
        "source": "whisper_fallback",
    }
