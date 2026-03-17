import os

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

