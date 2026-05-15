# YouTube Transcriber MCP Server

A local MCP (Model Context Protocol) server that exposes two tools for transcribing YouTube videos:
`transcribe_youtube_api` (fast, official captions) and `transcribe_youtube_whisper` (local audio transcription fallback). The transcript text is returned directly in the tool response.

## Prerequisites

```bash
sudo apt install ffmpeg
pip install uv
```

The Whisper fallback path additionally requires:
- **Firefox** installed, logged into youtube.com, and **closed** at run time. yt-dlp reads
  cookies from Firefox's `cookies.sqlite` to bypass YouTube's bot-detection on audio
  downloads. SQLite locks the file while Firefox is running.
- Internet access on the first run to fetch the JS challenge solver from
  [yt-dlp/ejs](https://github.com/yt-dlp/ejs) (cached in `~/.cache/yt-dlp/` thereafter).

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

Equivalent module invocation (no console-script entry needed):

```bash
uv run python -m youtube_transcriber_mcp
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

Note: the Whisper fallback's Firefox-cookie requirement makes the container
unable to use that path out of the box (no Firefox profile is mounted). For
container deployments, rely on the API path or extend the image to mount a
cookies file.

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

## Inspecting the Server

### fastmcp dev (recommended)

`fastmcp dev` starts the server and opens the MCP Inspector UI in the browser automatically. Requires Node.js.

```bash
export YOUTUBE_API_KEY=your_key_here
uv run fastmcp dev youtube_transcriber_mcp/server.py
```

### MCP Inspector (standalone)

If you prefer to run the inspector separately, start the server in streamable-http mode and point the inspector at it.

```bash
# Terminal 1 — start the server
export YOUTUBE_API_KEY=your_key_here
uv run youtube-transcriber-mcp --transport streamable-http --port 8000

# Terminal 2 — open the inspector
npx @modelcontextprotocol/inspector http://localhost:8000/mcp
```

The inspector opens at `http://localhost:5173` and lets you browse tools, call `transcribe_youtube` interactively, and inspect raw JSON request/response messages.

### Inspecting a running Docker container

```bash
docker compose up -d
npx @modelcontextprotocol/inspector http://localhost:8000/mcp
```

## Tools

The server exposes two independent tools:

| Tool | Strategy | Requires | Speed |
|---|---|---|---|
| `transcribe_youtube_api` | YouTube Data API v3 — fetches official captions | `YOUTUBE_API_KEY` | Fast |
| `transcribe_youtube_whisper` | yt-dlp + OpenAI Whisper — downloads audio and transcribes locally | `ffmpeg` | Slow |

Both tools return the transcript text directly in the response.

### Agent workflow

The server instructs the agent to follow this order automatically:

```
1. Call transcribe_youtube_api
        │
        ├── success → done ✅
        │
        └── error (no captions / no API key / quota exceeded)
                │
                └── Call transcribe_youtube_whisper → done ✅
```

The agent will always report which strategy was used along with the transcript text, source, language, and word count.

### Example prompts

> "Transcribe this video: https://www.youtube.com/watch?v=..."

> "Get me the transcript of https://youtu.be/... and save it."

> "Transcribe this YouTube Short: https://www.youtube.com/shorts/..."

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
| `WHISPER_MODEL` | `small` | Whisper model size |

The caption / transcription language is now a per-call `language` parameter on each tool (default `"en"`), not an env var.
