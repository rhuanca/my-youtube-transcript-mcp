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
git clone <repo-url> youtube-transcriber-mcp
cd youtube-transcriber-mcp
uv sync
```

## Getting a YouTube Data API v3 Key (securely)

1. Go to https://console.cloud.google.com/
2. Create a project (or reuse an existing one).
3. Enable **YouTube Data API v3**.
4. Create an **API key** under Credentials.
5. Click **Restrict Key** → set API restrictions to **YouTube Data API v3 only**.
   This ensures the key is useless if ever leaked.
6. Export the key in your shell: `export YOUTUBE_API_KEY=your_key_here`
7. **Never commit your API key to git.**

## Running the Server

### stdio (Claude Desktop / Claude Code)

The default transport. Claude Desktop spawns the process and communicates over stdin/stdout.

```bash
export YOUTUBE_API_KEY=your_key_here
uv run youtube-transcriber-mcp
```

Register in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "youtube-transcriber": {
      "command": "uv",
      "args": [
        "--directory", "/absolute/path/to/youtube-transcriber-mcp",
        "run", "youtube-transcriber-mcp"
      ],
      "env": {
        "YOUTUBE_API_KEY": "your_key_here"
      }
    }
  }
}
```

### streamable-http (remote / network clients)

Runs an HTTP server that clients connect to over the network.

```bash
export YOUTUBE_API_KEY=your_key_here
uv run youtube-transcriber-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

Connect from Claude Desktop:

```json
{
  "mcpServers": {
    "youtube-transcriber": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### Docker

Build and run the container (uses streamable-http on port 8000):

```bash
docker build -t youtube-transcriber-mcp .
docker run -p 8000:8000 -e YOUTUBE_API_KEY=your_key_here youtube-transcriber-mcp
```

To persist transcripts on the host:

```bash
docker run -p 8000:8000 \
  -e YOUTUBE_API_KEY=your_key_here \
  -v $(pwd)/transcripts:/app/transcripts \
  youtube-transcriber-mcp
```

### Docker Compose

```bash
YOUTUBE_API_KEY=your_key_here docker compose up
```

Or export the variable first:

```bash
export YOUTUBE_API_KEY=your_key_here
docker compose up
```

To run in the background:

```bash
docker compose up -d
docker compose logs -f   # follow logs
docker compose down      # stop
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
