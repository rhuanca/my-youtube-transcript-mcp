import re
from urllib.parse import urlparse, parse_qs


def extract_video_id(url: str) -> str:
    """
    Extract the YouTube video ID from common URL formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    Raise ValueError if the URL doesn't match any known format.
    """
    parsed = urlparse(url)

    if parsed.netloc in ("youtu.be",):
        video_id = parsed.path.lstrip("/").split("/")[0]
        if video_id:
            return video_id

    if parsed.netloc in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        if parsed.path.startswith("/shorts/"):
            video_id = parsed.path.split("/shorts/")[1].split("/")[0]
            if video_id:
                return video_id

        qs = parse_qs(parsed.query)
        if "v" in qs and qs["v"][0]:
            return qs["v"][0]

    raise ValueError(f"Could not extract a YouTube video ID from URL: {url!r}")


def sanitize_filename(name: str, max_length: int = 80) -> str:
    """
    Remove characters not safe for filenames.
    Replace spaces with underscores. Truncate to max_length.
    """
    name = re.sub(r'[\\/:*?"<>|]', "", name)
    name = name.replace(" ", "_")
    name = re.sub(r"_+", "_", name)
    name = name.strip("_.")
    return name[:max_length]


def parse_srt(srt_content: str) -> str:
    """
    Strip SRT sequence numbers and timestamps.
    Return clean plain text joined by spaces.
    """
    lines = srt_content.splitlines()
    text_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.match(r"^\d+$", line):
            continue
        if re.match(r"^\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}$", line):
            continue
        text_lines.append(line)
    return " ".join(text_lines)
