# YouTube Transcriber MCP Server

A local MCP (Model Context Protocol) server that exposes a single tool:
`transcribe_youtube(url)` — returns the transcript of a YouTube video and saves it as a `.txt` file.

## Strategy Decision Flow

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

## Prerequisites

```bash
sudo apt install ffmpeg
pip install uv
```

## Installation

```bash
cd youtube-transcriber-mcp
uv sync
cp .env.example .env
# Add your YOUTUBE_API_KEY to .env
```

## Getting a YouTube Data API v3 Key (securely)

1. Go to https://console.cloud.google.com/
2. Create a project (or reuse an existing one).
3. Enable **YouTube Data API v3**.
4. Create an **API key** under Credentials.
5. Click **Restrict Key** → set API restrictions to **YouTube Data API v3 only**.
   This ensures the key is useless if ever leaked.
6. Paste the key into `.env` as `YOUTUBE_API_KEY=...`
7. **Never commit `.env` to git.** It is listed in `.gitignore`.

## Register with Claude Desktop (`claude_desktop_config.json`)

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

## Usage from Claude

> "Transcribe this video: https://www.youtube.com/watch?v=..."

The response includes the strategy used (`youtube_api` or `whisper_fallback`)
and the absolute path to the saved `.txt` file.

## Whisper Model Tradeoffs (fallback path only)

| Model | Speed | Accuracy | Disk |
|---|---|---|---|
| tiny | Very fast | Low | ~75 MB |
| base | Fast | OK | ~140 MB |
| small | Good | Good | ~460 MB |
| medium | Slow | High | ~1.5 GB |
| large | Very slow | Best | ~2.9 GB |

Start with `small`. Model downloads automatically on first use.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `YOUTUBE_API_KEY` | _(empty)_ | YouTube Data API v3 key |
| `CAPTION_LANGUAGE` | `en` | Preferred caption language (ISO 639-1) |
| `WHISPER_MODEL` | `small` | Whisper model size |
| `TRANSCRIPTS_DIR` | `./transcripts` | Output directory for `.txt` files |
