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


# ---------------------------------------------------------------------------
# Search CLI
# ---------------------------------------------------------------------------

def build_search_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yt-scribe search",
        description="Search YouTube and download transcripts as a bundle.",
    )
    parser.add_argument(
        "query",
        help="Search query string",
    )
    parser.add_argument(
        "-n", "--results",
        type=int,
        default=10,
        help="Number of results to show (default: 10, max: 25)",
    )
    parser.add_argument(
        "--bundle",
        default=None,
        help="Bundle name (default: auto-generated from query)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Base output directory (default: ./transcripts/)",
    )
    parser.add_argument(
        "-l", "--lang",
        nargs="+",
        default=["en"],
        help="Preferred transcript language(s) (default: en)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output search results as JSON to stdout (non-interactive, no prompts)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser


def _format_duration_short(seconds: int | float | None) -> str:
    """Format duration as MM:SS or H:MM:SS."""
    if seconds is None:
        return "  ???"
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:>2d}:{secs:02d}"


def _display_results(results: list) -> None:
    """Print a formatted table of search results."""
    print()
    print(f"  {'#':>3}  {'Title':<50}  {'Channel':<15}  {'Duration':>8}")
    for i, r in enumerate(results, 1):
        title = r.title[:47] + "..." if len(r.title) > 50 else r.title
        channel = r.channel[:15] if r.channel else "Unknown"
        dur = _format_duration_short(r.duration_seconds)
        print(f"  {i:>3}  {title:<50}  {channel:<15}  {dur:>8}")
    print()


def parse_selection(input_str: str, max_val: int) -> list[int]:
    """Parse user selection string into a list of 1-based indices.

    Handles: 1,3,5 | 1-5 | 1-3,7,9-10 | all
    Raises ValueError on invalid input.
    """
    input_str = input_str.strip().lower()
    if not input_str:
        raise ValueError("Empty selection")

    if input_str == "all":
        return list(range(1, max_val + 1))

    indices = []
    for part in input_str.split(","):
        part = part.strip()
        if "-" in part:
            bounds = part.split("-", 1)
            lo, hi = int(bounds[0]), int(bounds[1])
            if lo < 1 or hi > max_val or lo > hi:
                raise ValueError(f"Range {part} is out of bounds (1-{max_val})")
            indices.extend(range(lo, hi + 1))
        else:
            val = int(part)
            if val < 1 or val > max_val:
                raise ValueError(f"{val} is out of bounds (1-{max_val})")
            indices.append(val)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for idx in indices:
        if idx not in seen:
            seen.add(idx)
            unique.append(idx)
    return unique


def search_main(argv: list[str]) -> int:
    """Search YouTube, display results, and download selected transcripts as a bundle."""
    from .search import search_youtube
    from .bundle import create_bundle_dir, generate_index, slugify

    parser = build_search_parser()
    args = parser.parse_args(argv)

    max_results = min(args.results, 25)

    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        format="%(levelname)s: %(message)s",
        level=level,
        stream=sys.stderr,
    )

    try:
        # 1. Search
        if not args.json_output:
            print(f"Searching YouTube for: {args.query}")
        results = search_youtube(args.query, max_results=max_results)

        if not results:
            print("No results found.", file=sys.stderr)
            return 1

        # JSON mode: output and exit immediately
        if args.json_output:
            import json
            output = [
                {
                    "index": i,
                    "video_id": r.video_id,
                    "title": r.title,
                    "channel": r.channel,
                    "duration_seconds": r.duration_seconds,
                    "url": r.url,
                }
                for i, r in enumerate(results, 1)
            ]
            sys.stdout.write(json.dumps(output, indent=2, ensure_ascii=False))
            return 0

        # 2. Display results
        _display_results(results)

        # 3. Get selection
        while True:
            try:
                raw = input("Select videos (e.g. 1,3,5 or 1-5 or all): ")
                selected = parse_selection(raw, len(results))
                break
            except (ValueError, KeyboardInterrupt) as e:
                if isinstance(e, KeyboardInterrupt):
                    print("\nAborted.", file=sys.stderr)
                    return 130
                print(f"Invalid selection: {e}. Try again.")

        # 4. Get bundle name
        auto_slug = args.bundle or slugify(args.query)
        bundle_input = input(f"Bundle name [{auto_slug}]: ").strip()
        bundle_name = bundle_input if bundle_input else auto_slug

        # 5. Create bundle directory
        bundle_dir = create_bundle_dir(bundle_name, output_base=args.output)

        # 6. Fetch transcripts for selected videos
        saved_files: list[tuple[str, str, Path]] = []
        total = len(selected)

        for i, sel_idx in enumerate(selected, 1):
            result = results[sel_idx - 1]
            print(f"\nFetching {i}/{total}: {result.title}...")

            try:
                meta = fetch_metadata(result.video_id, enrich=True)
                transcript = fetch_transcript(result.video_id, languages=args.lang)

                # Backfill duration
                if meta.duration_seconds is None:
                    meta.duration_seconds = transcript.duration_seconds

                content = format_markdown(meta, transcript)
                filename = generate_filename(meta) + ".md"
                output_path = bundle_dir / filename

                output_path.write_text(content, encoding="utf-8")
                print(f"  Saved: {output_path}")

                saved_files.append((meta.title, meta.video_id, output_path))

            except YtScribeError as e:
                print(f"  Warning: Skipped — {e}", file=sys.stderr)
                continue
            except Exception as e:
                log.debug("Unexpected error for %s: %s", result.video_id, e)
                print(f"  Warning: Skipped — {e}", file=sys.stderr)
                continue

        if not saved_files:
            print("\nNo transcripts were saved.", file=sys.stderr)
            return 1

        # 7. Generate index
        index_path = generate_index(bundle_dir, bundle_name, args.query, saved_files)
        print(f"\nCreated index: {index_path}")
        print(f"Bundle complete: {len(saved_files)} transcripts saved to {bundle_dir}/")
        return 0

    except YtScribeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 130
    except Exception as e:
        log.exception("Unexpected error")
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 2


# ---------------------------------------------------------------------------
# Playlist CLI
# ---------------------------------------------------------------------------

def build_playlist_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yt-scribe playlist",
        description="Import a public YouTube playlist and download transcripts as a bundle.",
    )
    parser.add_argument(
        "url",
        help="YouTube playlist URL",
    )
    parser.add_argument(
        "--bundle",
        default=None,
        help="Bundle name (default: auto-generated from playlist title)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Base output directory (default: ./transcripts/)",
    )
    parser.add_argument(
        "-l", "--lang",
        nargs="+",
        default=["en"],
        help="Preferred transcript language(s) (default: en)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output playlist info as JSON to stdout (non-interactive, no prompts)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser


def playlist_main(argv: list[str]) -> int:
    """Fetch a YouTube playlist, display videos, and download selected transcripts as a bundle."""
    from .search import fetch_playlist
    from .bundle import create_bundle_dir, generate_index, slugify

    parser = build_playlist_parser()
    args = parser.parse_args(argv)

    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        format="%(levelname)s: %(message)s",
        level=level,
        stream=sys.stderr,
    )

    try:
        # 1. Fetch playlist
        if not args.json_output:
            print(f"Fetching playlist...")
        playlist_info = fetch_playlist(args.url)
        if not args.json_output:
            print(f"Fetching playlist: {playlist_info.title} ({playlist_info.video_count} videos)")

        # JSON mode: output and exit immediately
        if args.json_output:
            import json
            output = {
                "title": playlist_info.title,
                "playlist_url": playlist_info.playlist_url,
                "video_count": playlist_info.video_count,
                "videos": [
                    {
                        "index": i,
                        "video_id": v.video_id,
                        "title": v.title,
                        "channel": v.channel,
                        "duration_seconds": v.duration_seconds,
                        "url": v.url,
                    }
                    for i, v in enumerate(playlist_info.videos, 1)
                ],
            }
            sys.stdout.write(json.dumps(output, indent=2, ensure_ascii=False))
            return 0

        # 2. Display results
        _display_results(playlist_info.videos)

        # 3. Get selection
        while True:
            try:
                raw = input("Select videos (e.g. 1,3,5 or 1-5 or all): ")
                selected = parse_selection(raw, len(playlist_info.videos))
                break
            except (ValueError, KeyboardInterrupt) as e:
                if isinstance(e, KeyboardInterrupt):
                    print("\nAborted.", file=sys.stderr)
                    return 130
                print(f"Invalid selection: {e}. Try again.")

        # 4. Get bundle name
        auto_slug = args.bundle or slugify(playlist_info.title)
        bundle_input = input(f"Bundle name [{auto_slug}]: ").strip()
        bundle_name = bundle_input if bundle_input else auto_slug

        # 5. Create bundle directory
        bundle_dir = create_bundle_dir(bundle_name, output_base=args.output)

        # 6. Fetch transcripts for selected videos
        saved_files: list[tuple[str, str, Path]] = []
        total = len(selected)

        for i, sel_idx in enumerate(selected, 1):
            result = playlist_info.videos[sel_idx - 1]
            print(f"\nFetching {i}/{total}: {result.title}...")

            try:
                meta = fetch_metadata(result.video_id, enrich=True)
                transcript = fetch_transcript(result.video_id, languages=args.lang)

                # Backfill duration
                if meta.duration_seconds is None:
                    meta.duration_seconds = transcript.duration_seconds

                content = format_markdown(meta, transcript)
                filename = generate_filename(meta) + ".md"
                output_path = bundle_dir / filename

                output_path.write_text(content, encoding="utf-8")
                print(f"  Saved: {output_path}")

                saved_files.append((meta.title, meta.video_id, output_path))

            except YtScribeError as e:
                print(f"  Warning: Skipped — {e}", file=sys.stderr)
                continue
            except Exception as e:
                log.debug("Unexpected error for %s: %s", result.video_id, e)
                print(f"  Warning: Skipped — {e}", file=sys.stderr)
                continue

        if not saved_files:
            print("\nNo transcripts were saved.", file=sys.stderr)
            return 1

        # 7. Generate index
        index_path = generate_index(
            bundle_dir, bundle_name, playlist_info.title, saved_files,
            source_url=args.url,
        )
        print(f"\nCreated index: {index_path}")
        print(f"Bundle complete: {len(saved_files)} transcripts saved to {bundle_dir}/")
        return 0

    except YtScribeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 130
    except Exception as e:
        log.exception("Unexpected error")
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 2


# ---------------------------------------------------------------------------
# Batch CLI
# ---------------------------------------------------------------------------

def build_batch_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yt-scribe batch",
        description="Download transcripts for specific video IDs as a bundle (non-interactive).",
    )
    parser.add_argument(
        "videos",
        nargs="*",
        help="One or more YouTube video IDs or URLs",
    )
    parser.add_argument(
        "--from-file",
        type=Path,
        default=None,
        dest="from_file",
        help="Read video IDs/URLs from a text file (one per line, # comments and blank lines ignored)",
    )
    parser.add_argument(
        "--bundle",
        required=True,
        help="Bundle name (required)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Base output directory (default: ./transcripts/)",
    )
    parser.add_argument(
        "-l", "--lang",
        nargs="+",
        default=["en"],
        help="Preferred transcript language(s) (default: en)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON to stdout instead of human-readable progress",
    )
    parser.add_argument(
        "--jsonl",
        action="store_true",
        dest="jsonl_output",
        help="Output one JSON object per line as each video completes (streaming-friendly)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser


def _jsonl_write(obj: dict) -> None:
    """Write a JSON object as a single line to stdout, flush immediately."""
    import json
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def batch_main(argv: list[str]) -> int:
    """Download transcripts for explicit video IDs as a bundle (fully non-interactive)."""
    from .bundle import create_bundle_dir, generate_index

    parser = build_batch_parser()
    args = parser.parse_args(argv)

    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        format="%(levelname)s: %(message)s",
        level=level,
        stream=sys.stderr,
    )

    # Merge positional videos with --from-file entries
    videos = list(args.videos or [])
    if args.from_file is not None:
        if not args.from_file.is_file():
            print(f"Error: File not found: {args.from_file}", file=sys.stderr)
            return 1
        for line in args.from_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            videos.append(line)

    if not videos:
        print("Error: No videos specified. Provide video IDs/URLs as arguments or via --from-file.", file=sys.stderr)
        return 1

    quiet = args.json_output or args.jsonl_output

    try:
        # 1. Create bundle directory
        bundle_dir = create_bundle_dir(args.bundle, output_base=args.output)

        # 2. Fetch transcripts for each video
        saved_files: list[tuple[str, str, Path]] = []
        json_files: list[dict] = []
        total = len(videos)

        if args.jsonl_output:
            _jsonl_write({"event": "start", "total": total, "bundle": args.bundle})

        for i, video_arg in enumerate(videos, 1):
            try:
                video_id = extract_video_id(video_arg)

                if not quiet:
                    print(f"Fetching {i}/{total}: {video_id}...")

                meta = fetch_metadata(video_id, enrich=True)
                transcript = fetch_transcript(video_id, languages=args.lang)

                # Backfill duration
                if meta.duration_seconds is None:
                    meta.duration_seconds = transcript.duration_seconds

                content = format_markdown(meta, transcript)
                filename = generate_filename(meta) + ".md"
                output_path = bundle_dir / filename

                output_path.write_text(content, encoding="utf-8")

                if not quiet:
                    print(f"  Saved: {output_path}")

                saved_files.append((meta.title, meta.video_id, output_path))
                json_files.append({
                    "video_id": meta.video_id,
                    "title": meta.title,
                    "path": str(output_path),
                    "status": "saved",
                })

                if args.jsonl_output:
                    _jsonl_write({
                        "event": "progress",
                        "index": i,
                        "total": total,
                        "video_id": meta.video_id,
                        "title": meta.title,
                        "status": "saved",
                        "path": str(output_path),
                    })

            except (YtScribeError, ValueError) as e:
                if not quiet:
                    print(f"  Warning: Skipped {video_arg} — {e}", file=sys.stderr)
                json_files.append({
                    "video_id": video_arg,
                    "title": None,
                    "path": None,
                    "status": "skipped",
                    "error": str(e),
                })
                if args.jsonl_output:
                    _jsonl_write({
                        "event": "progress",
                        "index": i,
                        "total": total,
                        "video_id": video_arg,
                        "title": None,
                        "status": "skipped",
                        "error": str(e),
                    })
                continue
            except Exception as e:
                log.debug("Unexpected error for %s: %s", video_arg, e)
                if not quiet:
                    print(f"  Warning: Skipped {video_arg} — {e}", file=sys.stderr)
                json_files.append({
                    "video_id": video_arg,
                    "title": None,
                    "path": None,
                    "status": "skipped",
                    "error": str(e),
                })
                if args.jsonl_output:
                    _jsonl_write({
                        "event": "progress",
                        "index": i,
                        "total": total,
                        "video_id": video_arg,
                        "title": None,
                        "status": "skipped",
                        "error": str(e),
                    })
                continue

        # 3. Generate index (even if some failed, as long as we have at least one)
        if saved_files:
            generate_index(bundle_dir, args.bundle, "batch import", saved_files)

        # 4. Output
        if args.jsonl_output:
            _jsonl_write({
                "event": "complete",
                "bundle": args.bundle,
                "bundle_dir": str(bundle_dir),
                "total_saved": len(saved_files),
                "total_skipped": total - len(saved_files),
            })
            return 0

        if args.json_output:
            import json
            output = {
                "bundle": args.bundle,
                "bundle_dir": str(bundle_dir),
                "total_requested": total,
                "total_saved": len(saved_files),
                "total_skipped": total - len(saved_files),
                "files": json_files,
            }
            sys.stdout.write(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            if not saved_files:
                print("\nNo transcripts were saved.", file=sys.stderr)
                return 1
            print(f"\nBundle complete: {len(saved_files)}/{total} transcripts saved to {bundle_dir}/")

        return 0

    except YtScribeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 130
    except Exception as e:
        log.exception("Unexpected error")
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 2


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # Route to search if first arg is "search"
    if argv and argv[0] == "search":
        return search_main(argv[1:])
    if argv and argv[0] == "playlist":
        return playlist_main(argv[1:])
    if argv and argv[0] == "batch":
        return batch_main(argv[1:])

    # Existing fetch logic (unchanged)
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
