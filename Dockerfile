FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY youtube_transcriber_mcp/ ./youtube_transcriber_mcp/

# Install Python dependencies
RUN uv sync --no-dev

EXPOSE 8000

CMD ["uv", "run", "youtube-transcriber-mcp", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
