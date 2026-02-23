"""yt-scribe CLI entry point."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .url_parser import extract_video_id
from .metadata import fetch_metadata
from .transcript import fetch_transcript
from .formatter import format_markdown, format_json, generate_filename
from .errors import YtScribeError

log = logging.getLogger("yt-scribe")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yt-scribe",
        description="Fetch YouTube transcripts and save as formatted Markdown.",
        epilog=(
            "Examples:\n"
            "  yt-scribe https://www.youtube.com/watch?v=dQw4w9WgXcQ\n"
            "  yt-scribe dQw4w9WgXcQ --lang es\n"
            "  yt-scribe dQw4w9WgXcQ --json --output ~/notes/\n"
            "  yt-scribe dQw4w9WgXcQ --enrich\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "video",
        help="YouTube video URL or video ID",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output directory (default: ./transcripts/)",
    )
    parser.add_argument(
        "-l", "--lang",
        nargs="+",
        default=["en"],
        help="Preferred transcript language(s), e.g. --lang en es (default: en)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output JSON instead of Markdown",
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        help=(
            "Use yt-dlp for richer metadata (upload date, description). "
            "Requires: pip install yt-dlp"
        ),
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print to stdout instead of writing a file",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        format="%(levelname)s: %(message)s",
        level=level,
        stream=sys.stderr,
    )

    try:
        # 1. Parse video ID
        video_id = extract_video_id(args.video)
        log.debug("Video ID: %s", video_id)

        # 2. Fetch metadata
        meta = fetch_metadata(video_id, enrich=args.enrich)
        log.debug("Title: %s", meta.title)

        # 3. Fetch transcript
        transcript = fetch_transcript(video_id, languages=args.lang)
        log.debug("Got %d segments in %s", len(transcript.segments), transcript.language)

        # 4. Backfill duration from transcript if oEmbed didn't provide it
        if meta.duration_seconds is None:
            meta.duration_seconds = transcript.duration_seconds

        # 5. Format output
        if args.json_output:
            content = format_json(meta, transcript)
            ext = ".json"
        else:
            content = format_markdown(meta, transcript)
            ext = ".md"

        # 6. Write output
        if args.stdout:
            sys.stdout.write(content)
            return 0

        output_dir = args.output or Path("transcripts")
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = generate_filename(meta) + ext
        output_path = output_dir / filename

        output_path.write_text(content, encoding="utf-8")
        print(f"Saved: {output_path}")
        return 0

    except (YtScribeError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 130
    except Exception as e:
        log.exception("Unexpected error")
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
