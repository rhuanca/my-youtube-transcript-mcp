# CLAUDE.md — YouTube Transcriber MCP Server

## Project Goal

Build a local MCP (Model Context Protocol) server that exposes a single tool:
`transcribe_youtube(url)` — it returns the transcript of a YouTube video and
saves it as a `.txt` file.

### Transcription Strategy (in order of priority)

1. **Primary — YouTube Data API v3:** fetch the official captions directly from
   Google. Fast, accurate, no audio processing needed. Requires a valid API key.
2. **Fallback — yt-dlp + Whisper:** if captions are unavailable or the API call
   fails, download the audio with `yt-dlp` and transcribe it locally with
   OpenAI Whisper. Runs fully offline; no data leaves the machine.

The caller never needs to choose — the server picks the best path automatically
and reports which strategy was used in the response.

---

## Target Environment

- **OS:** Ubuntu Linux
- **Python:** 3.11+
- **Package manager:** `uv` (install with `pip install uv`)
- **System dependency:** `ffmpeg` (install with `sudo apt install ffmpeg`)
  — required only by the yt-dlp + Whisper fallback path
- **Transport:** `stdio` (Claude Desktop / Claude Code integration)

---

## Tech Stack

| Role | Library | Path |
|---|---|---|
| MCP framework | `fastmcp` | Both paths |
| Caption fetching | `google-api-python-client` | Primary only |
| Audio download | `yt-dlp` | Fallback only |
| Transcription | `openai-whisper` | Fallback only |
| Audio processing | `ffmpeg` (system binary) | Fallback only |
| Config | `python-dotenv` | Both paths |

---

## Project Structure to Generate

```
youtube-transcriber-mcp/
├── CLAUDE.md                        ← this file
├── README.md
├── .gitignore
├── pyproject.toml
├── .env.example
├── youtube_transcriber_mcp/
│   ├── __init__.py
│   ├── __main__.py                  ← CLI entrypoint
│   ├── server.py                    ← FastMCP server + tool registration
│   ├── config.py                    ← Settings loaded from .env
│   ├── transcriber.py               ← Orchestrator: picks strategy, saves file
│   ├── utils.py                     ← Shared helpers (sanitize filename, parse SRT, etc.)
│   └── strategies/
│       ├── __init__.py
│       ├── youtube_api.py           ← Primary: YouTube Data API v3
│       └── whisper_fallback.py      ← Fallback: yt-dlp + Whisper
└── transcripts/                     ← Output folder (auto-created at runtime)
```

---

## pyproject.toml

```toml
[project]
name = "youtube-transcriber-mcp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=2.0",
    "google-api-python-client>=2.100",
    "yt-dlp>=2024.0",
    "openai-whisper>=20231117",
    "python-dotenv>=1.0",
]

[project.scripts]
youtube-transcriber-mcp = "youtube_transcriber_mcp.__main__:main"
```

---

## .gitignore

```
.env
.venv/
__pycache__/
transcripts/
/tmp/
*.pyc
```

---

## config.py

```python
import os
from dotenv import load_dotenv

load_dotenv()

# --- YouTube Data API v3 ---
# Get yours at: https://console.cloud.google.com/
# Enable "YouTube Data API v3" and create an API key (restrict it to this API only).
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# Preferred caption language code (e.g. "en", "es", "fr")
CAPTION_LANGUAGE = os.getenv("CAPTION_LANGUAGE", "en")

# --- Fallback: Whisper ---
# Model size: tiny | base | small | medium | large
# "small" is a good default: fast and accurate enough for educational content.
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")

# --- Output ---
# Absolute or relative path where .txt transcripts are saved
TRANSCRIPTS_DIR = os.getenv("TRANSCRIPTS_DIR", "./transcripts")
```

---

## .env.example

```env
# ─── YouTube Data API v3 ──────────────────────────────────────────────────────
# Required for the primary (fast) transcription path.
# Get a key: https://console.cloud.google.com/ → Enable YouTube Data API v3
# SECURITY: restrict the key to "YouTube Data API v3" only in the GCP console.
YOUTUBE_API_KEY=your_api_key_here

# Preferred caption language (ISO 639-1 code)
CAPTION_LANGUAGE=en

# ─── Fallback: Whisper ────────────────────────────────────────────────────────
# Used when captions are not available via the API.
# Options: tiny | base | small | medium | large
WHISPER_MODEL=small

# ─── Output ───────────────────────────────────────────────────────────────────
TRANSCRIPTS_DIR=./transcripts
```

---

## utils.py — Shared Helpers

```python
def extract_video_id(url: str) -> str:
    """
    Extract the YouTube video ID from common URL formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    Raise ValueError if the URL doesn't match any known format.
    """

def sanitize_filename(name: str, max_length: int = 80) -> str:
    """
    Remove characters not safe for filenames.
    Replace spaces with underscores. Truncate to max_length.
    """

def parse_srt(srt_content: str) -> str:
    """
    Strip SRT sequence numbers and timestamps.
    Return clean plain text joined by spaces.
    """
```

---

## strategies/youtube_api.py — Primary Path

### Custom exceptions

```python
class CaptionsNotAvailableError(Exception):
    """Raised when no downloadable caption track exists for this video."""

class YouTubeAPIError(Exception):
    """Raised on API quota, key, or connectivity errors."""
```

### Function to implement

```python
def fetch_captions(video_id: str) -> dict:
    """
    Fetch the official captions for a YouTube video using the YouTube Data API v3.

    Steps:
    1. Build a googleapiclient discovery client using config.YOUTUBE_API_KEY.
    2. Fetch video title via videos.list(part="snippet", id=video_id).
    3. Call captions.list(part="snippet", videoId=video_id) to list available tracks.
    4. Select the track matching config.CAPTION_LANGUAGE. If not found, try "en".
       If still not found, raise CaptionsNotAvailableError.
    5. Call captions.download(id=caption_track_id, tfmt="srt") to get SRT content.
       - If this raises HttpError 403, raise CaptionsNotAvailableError
         (auto-generated captions require OAuth — trigger fallback silently).
    6. Parse the SRT using utils.parse_srt() to get plain text.
    7. Return:
       {
           "title": "<video title>",
           "text": "<full transcript as plain text>",
           "language": "<language code used>",
           "source": "youtube_api"
       }

    Raises:
        CaptionsNotAvailableError: no suitable track found, or 403 on download.
        YouTubeAPIError: quota exceeded, invalid API key, or network failure.
    """
```

### API quota notes

- `captions.list` costs 50 units, `captions.download` costs 200 units.
- Daily free quota is 10,000 units — sufficient for nightly personal use.
- On `HttpError` 403, catch and raise `CaptionsNotAvailableError` (do not crash).
- On `HttpError` 429 or 403 with "quotaExceeded", raise `YouTubeAPIError`.

---

## strategies/whisper_fallback.py — Fallback Path

### Whisper model singleton (load once, reuse across calls)

```python
_whisper_model = None

def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        _whisper_model = whisper.load_model(config.WHISPER_MODEL)
    return _whisper_model
```

### Function to implement

```python
def transcribe_with_whisper(video_id: str, video_title: str) -> dict:
    """
    Download audio with yt-dlp and transcribe locally with OpenAI Whisper.

    Steps:
    1. Check that `ffmpeg` is available in PATH. If missing, raise RuntimeError:
       "ffmpeg is required for the Whisper fallback. Install: sudo apt install ffmpeg"
    2. Sanitize video_title with utils.sanitize_filename().
    3. Use yt-dlp to download best audio for video_id to:
       /tmp/yt_transcriber/<sanitized_title>.mp3
       Create /tmp/yt_transcriber/ if it doesn't exist.
    4. Load Whisper model via _get_whisper_model().
    5. Run model.transcribe(audio_path).
    6. Always delete the temp audio file after transcription (use try/finally).
    7. Return:
       {
           "title": video_title,
           "text": "<full transcript as plain text>",
           "language": "<detected language code>",
           "source": "whisper_fallback"
       }
    """
```

### yt-dlp options to use

```python
ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": f"/tmp/yt_transcriber/{sanitized_title}.%(ext)s",
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "128",
    }],
    "quiet": True,
    "no_warnings": True,
}
```

---

## transcriber.py — Orchestrator

```python
def transcribe_youtube(url: str) -> dict:
    """
    Main entry point. Orchestrates the dual-strategy transcription.

    Steps:
    1. Validate the URL and extract video_id using utils.extract_video_id().
       On invalid URL, return error dict immediately.

    2. [PRIMARY] If config.YOUTUBE_API_KEY is set:
       - Call youtube_api.fetch_captions(video_id).
       - On success: proceed to step 4 with the result.
       - On CaptionsNotAvailableError: log reason, continue to step 3.
       - On YouTubeAPIError: log reason, continue to step 3.

    3. [FALLBACK] Call whisper_fallback.transcribe_with_whisper(video_id, title).
       - On success: proceed to step 4.
       - On any error: return error dict with clear message.

    4. Save transcript:
       - Create config.TRANSCRIPTS_DIR if it doesn't exist.
       - Filename: utils.sanitize_filename(title) + ".txt"
       - Write UTF-8 plain text.

    5. Return:
       {
           "status": "success",
           "title": "<video title>",
           "transcript_path": "<absolute path to .txt file>",
           "source": "youtube_api" | "whisper_fallback",
           "word_count": <int>,
           "language": "<language code>"
       }

    6. On unrecoverable error, return:
       {
           "status": "error",
           "message": "<human-readable description>"
       }
    """
```

---

## server.py — MCP Tool Registration

```python
from fastmcp import FastMCP
from youtube_transcriber_mcp.transcriber import transcribe_youtube as _transcribe

mcp = FastMCP(
    name="youtube-transcriber",
    description=(
        "Transcribes YouTube videos. Uses YouTube Data API v3 (fast, accurate) "
        "when captions are available; falls back to local Whisper transcription otherwise."
    )
)

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
```

---

## __main__.py — CLI Entrypoint

```python
import logging
from youtube_transcriber_mcp.server import mcp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
```

---

## README.md — Must Include

### 1. Prerequisites

```bash
sudo apt install ffmpeg
pip install uv
```

### 2. Installation

```bash
cd youtube-transcriber-mcp
uv sync
cp .env.example .env
# Add your YOUTUBE_API_KEY to .env
```

### 3. Getting a YouTube Data API v3 Key (securely)

1. Go to https://console.cloud.google.com/
2. Create a project (or reuse an existing one).
3. Enable **YouTube Data API v3**.
4. Create an **API key** under Credentials.
5. Click **Restrict Key** → set API restrictions to **YouTube Data API v3 only**.
   This ensures the key is useless if ever leaked.
6. Paste the key into `.env` as `YOUTUBE_API_KEY=...`
7. **Never commit `.env` to git.** It is listed in `.gitignore`.

### 4. Register with Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "youtube-transcriber": {
      "command": "uv",
      "args": [
        "--directory", "/absolute/path/to/youtube-transcriber-mcp",
        "run", "youtube-transcriber-mcp"
      ]
    }
  }
}
```

### 5. Usage from Claude

> "Transcribe this video: https://www.youtube.com/watch?v=..."

The response includes the strategy used (`youtube_api` or `whisper_fallback`)
and the absolute path to the saved `.txt` file.

### 6. Strategy Decision Flow

```
transcribe_youtube(url)
        │
        ▼
YOUTUBE_API_KEY set?
   ├── Yes → fetch captions via YouTube Data API v3
   │         ├── Captions found → save .txt → ✅ (source: youtube_api)
   │         └── No captions / 403 forbidden → fallback ↓
   └── No  ──────────────────────────────────────↓
                              yt-dlp downloads audio locally
                              Whisper transcribes locally
                              save .txt → ✅ (source: whisper_fallback)
```

### 7. Whisper Model Tradeoffs (fallback path only)

| Model | Speed | Accuracy | Disk |
|---|---|---|---|
| tiny | Very fast | Low | ~75 MB |
| base | Fast | OK | ~140 MB |
| small | Good | Good | ~460 MB |
| medium | Slow | High | ~1.5 GB |
| large | Very slow | Best | ~2.9 GB |

Start with `small`. Model downloads automatically on first use.

---

## Validation Checklist

Claude Code must verify each item before finishing:

- [ ] `uv sync` completes without errors
- [ ] `uv run youtube-transcriber-mcp` starts without crashing
- [ ] A video with public captions → uses `youtube_api`, produces `.txt`, `source` = `"youtube_api"`
- [ ] A video without captions (or `YOUTUBE_API_KEY` unset) → uses `whisper_fallback`, produces `.txt`
- [ ] `source` field in response correctly reflects which path was taken
- [ ] Temp audio file in `/tmp/yt_transcriber/` is deleted after Whisper run
- [ ] Bad URL returns `{"status": "error", "message": "..."}` without crashing
- [ ] `ffmpeg` absence produces a clear, actionable error message
- [ ] `.env` is present in `.gitignore` and never committed

---

## Guardrails for Claude Code

- Do **not** hardcode the API key anywhere in source code. Always load from `.env`.
- Do **not** implement OAuth 2.0. If the API returns 403, treat as `CaptionsNotAvailableError`
  and fall back to Whisper silently.
- Do **not** add dependencies beyond those listed in `pyproject.toml`.
- The `transcripts/` folder must be created automatically if it doesn't exist.
- All `transcript_path` values must be **absolute paths**.
- Use `logging` throughout — not `print()`. Log which strategy was selected and why.
- The Whisper model must be a **module-level singleton**: loaded once, reused on
  subsequent calls within the same server session.
- Handle `KeyboardInterrupt` gracefully in `__main__.py`.
