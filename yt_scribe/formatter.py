"""Output formatting: Markdown and JSON."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from .metadata import VideoMetadata
from .transcript import TranscriptResult


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS or MM:SS format."""
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _format_duration(seconds: int) -> str:
    """Format duration as human-readable string."""
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def format_markdown(
    meta: VideoMetadata,
    transcript: TranscriptResult,
) -> str:
    """Format video metadata + transcript as Markdown."""
    lines: list[str] = []

    duration = meta.duration_seconds or transcript.duration_seconds

    # YAML frontmatter
    lines.append("---")
    lines.append(f'title: "{meta.title}"')
    lines.append(f'channel: "{meta.channel}"')
    lines.append(f'video_id: "{meta.video_id}"')
    lines.append(f'url: "https://www.youtube.com/watch?v={meta.video_id}"')
    if duration:
        lines.append(f'duration: "{_format_duration(duration)}"')
    if meta.upload_date:
        lines.append(f'upload_date: "{meta.upload_date}"')
    lines.append(f'language: "{transcript.language}"')
    lines.append(f'transcript_type: "{"auto-generated" if transcript.is_generated else "manual"}"')
    lines.append(f'fetched_at: "{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}"')
    lines.append("---")
    lines.append("")

    # Heading
    lines.append(f"# {meta.title}")
    lines.append("")
    lines.append(f"**Channel:** [{meta.channel}]({meta.channel_url})")
    if duration:
        lines.append(f"**Duration:** {_format_duration(duration)}")
    if meta.upload_date:
        lines.append(f"**Uploaded:** {meta.upload_date}")
    lines.append(
        f"**Language:** {transcript.language}"
        f" ({'auto-generated' if transcript.is_generated else 'manual'})"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    # Transcript body
    lines.append("## Transcript")
    lines.append("")
    for segment in transcript.segments:
        ts = _format_timestamp(segment.start)
        lines.append(f"**[{ts}]** {segment.text}")
        lines.append("")

    return "\n".join(lines)


def format_json(
    meta: VideoMetadata,
    transcript: TranscriptResult,
) -> str:
    """Format video metadata + transcript as JSON."""
    data = {
        "video_id": meta.video_id,
        "title": meta.title,
        "channel": meta.channel,
        "channel_url": meta.channel_url,
        "url": f"https://www.youtube.com/watch?v={meta.video_id}",
        "duration_seconds": meta.duration_seconds or transcript.duration_seconds,
        "upload_date": meta.upload_date,
        "thumbnail_url": meta.thumbnail_url,
        "language": transcript.language,
        "language_code": transcript.language_code,
        "is_generated": transcript.is_generated,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "segments": [
            {
                "text": seg.text,
                "start": round(seg.start, 2),
                "duration": round(seg.duration, 2),
                "timestamp": _format_timestamp(seg.start),
            }
            for seg in transcript.segments
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def generate_filename(meta: VideoMetadata) -> str:
    """Generate a filesystem-safe filename from video metadata.

    Format: {sanitized_title}_{video_id}
    """
    safe = "".join(
        c if c.isalnum() or c in " -" else "_"
        for c in meta.title
    )
    # Collapse multiple underscores/spaces, strip, truncate
    safe = "_".join(safe.split())[:80]
    return f"{safe}_{meta.video_id}"
