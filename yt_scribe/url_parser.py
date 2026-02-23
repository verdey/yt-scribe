"""YouTube URL/ID parsing and validation."""
from __future__ import annotations

import re
from urllib.parse import urlparse, parse_qs

# YouTube video IDs are 11 characters: alphanumeric, hyphens, underscores
VIDEO_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")

# Patterns for path-based IDs: /embed/ID, /shorts/ID, /live/ID, /v/ID
PATH_PATTERNS = re.compile(r"^/(?:embed|shorts|live|v)/([a-zA-Z0-9_-]{11})")


def extract_video_id(url_or_id: str) -> str:
    """Extract YouTube video ID from URL or raw ID string.

    Raises ValueError if input cannot be parsed to a valid video ID.
    """
    url_or_id = url_or_id.strip()

    # Direct video ID (11 chars)
    if VIDEO_ID_RE.match(url_or_id):
        return url_or_id

    parsed = urlparse(url_or_id)

    # Standard watch URL: ?v=ID
    if parsed.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            if "v" in qs:
                vid = qs["v"][0]
                if VIDEO_ID_RE.match(vid):
                    return vid
        # Path-based: /embed/ID, /shorts/ID, /live/ID
        match = PATH_PATTERNS.match(parsed.path)
        if match:
            return match.group(1)

    # Short URL: youtu.be/ID
    if parsed.hostname == "youtu.be":
        vid = parsed.path.lstrip("/")
        if VIDEO_ID_RE.match(vid):
            return vid

    raise ValueError(f"Could not extract video ID from: {url_or_id}")
