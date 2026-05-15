"""CLI for transcribing a local audio or video file with OpenAI Whisper.

Skips yt-dlp entirely (no download), so it works on any file ffmpeg can read.
"""
import argparse
import logging
import shutil
import sys
from pathlib import Path

from youtube_transcriber_mcp import config

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe a local audio or video file with OpenAI Whisper.",
    )
    parser.add_argument("path", help="Path to the local audio or video file")
    parser.add_argument(
        "--language", default="en",
        help="ISO 639-1 language code passed to Whisper (default: en). "
             "Use 'auto' to let Whisper detect.",
    )
    parser.add_argument(
        "--model", default=config.WHISPER_MODEL,
        choices=["tiny", "base", "small", "medium", "large"],
        help=f"Whisper model size (default: {config.WHISPER_MODEL!r}; via WHISPER_MODEL env var).",
    )
    parser.add_argument(
        "--output", "-o",
        help="Path to write the transcript to. If omitted, prints to stdout.",
    )
    parser.add_argument(
        "--device", default="auto", choices=["auto", "cpu", "cuda"],
        help="Compute device. 'auto' lets Whisper pick (CUDA if available). "
             "Use 'cpu' for medium/large models on small GPUs (<5 GB VRAM).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    file_path = Path(args.path)
    if not file_path.is_file():
        logger.error("File not found: %s", file_path)
        sys.exit(1)

    if not shutil.which("ffmpeg"):
        logger.error("ffmpeg is required. Install: sudo apt install ffmpeg")
        sys.exit(1)

    import whisper
    device = None if args.device == "auto" else args.device
    logger.info("Loading Whisper model: %s (device=%s)", args.model, args.device)
    model = whisper.load_model(args.model, device=device)

    logger.info("Transcribing %s (language=%s)", file_path.name, args.language)
    transcribe_kwargs = {} if args.language == "auto" else {"language": args.language}
    result = model.transcribe(str(file_path), **transcribe_kwargs)
    text = result["text"].strip()

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        logger.info("Wrote %d words to %s", len(text.split()), args.output)
    else:
        print(text)


if __name__ == "__main__":
    main()
