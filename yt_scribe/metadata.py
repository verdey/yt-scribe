"""Video metadata fetching.

Primary: YouTube oEmbed API (zero dependencies beyond requests).
Optional: yt-dlp for enriched metadata (upload date, duration, description).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

from .errors import MetadataFetchError

log = logging.getLogger(__name__)

OEMBED_URL = "https://www.youtube.com/oembed"


@dataclass
class VideoMetadata:
    """Structured video metadata."""
    video_id: str
    title: str
    channel: str
    channel_url: str = ""
    duration_seconds: int | None = None
    upload_date: str | None = None
    description: str | None = None
    thumbnail_url: str | None = None
    source: str = "oembed"


def fetch_metadata_oembed(video_id: str) -> VideoMetadata:
    """Fetch basic metadata via YouTube oEmbed endpoint.

    Returns title, channel name, channel URL, thumbnail URL.
    Does NOT return duration or upload date.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        resp = requests.get(
            OEMBED_URL,
            params={"url": url, "format": "json"},
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise MetadataFetchError(f"oEmbed request failed: {e}") from e

    data = resp.json()
    return VideoMetadata(
        video_id=video_id,
        title=data.get("title", "Unknown Title"),
        channel=data.get("author_name", "Unknown Channel"),
        channel_url=data.get("author_url", ""),
        thumbnail_url=data.get("thumbnail_url"),
        source="oembed",
    )


def fetch_metadata_ytdlp(video_id: str) -> VideoMetadata:
    """Fetch enriched metadata via yt-dlp (optional dependency).

    Returns everything oEmbed does PLUS: duration, upload_date, description.
    """
    try:
        import yt_dlp
    except ImportError:
        raise MetadataFetchError(
            "yt-dlp is not installed. Install with: pip install yt-dlp"
        )

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "no_color": True,
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        raise MetadataFetchError(f"yt-dlp extraction failed: {e}") from e

    raw_date = info.get("upload_date", "")
    iso_date = None
    if raw_date and len(raw_date) == 8:
        iso_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"

    return VideoMetadata(
        video_id=video_id,
        title=info.get("title", "Unknown Title"),
        channel=info.get("channel", info.get("uploader", "Unknown Channel")),
        channel_url=info.get("channel_url", info.get("uploader_url", "")),
        duration_seconds=info.get("duration"),
        upload_date=iso_date,
        description=info.get("description"),
        thumbnail_url=info.get("thumbnail"),
        source="yt-dlp",
    )


def fetch_metadata(video_id: str, enrich: bool = False) -> VideoMetadata:
    """Fetch video metadata. Uses oEmbed by default, yt-dlp if enrich=True."""
    if enrich:
        try:
            return fetch_metadata_ytdlp(video_id)
        except MetadataFetchError:
            log.warning("yt-dlp enrichment failed, falling back to oEmbed")
    return fetch_metadata_oembed(video_id)
