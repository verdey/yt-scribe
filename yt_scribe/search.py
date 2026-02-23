"""YouTube search via yt-dlp."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from .errors import MetadataFetchError

log = logging.getLogger(__name__)


@dataclass
class SearchResult:
    video_id: str
    title: str
    channel: str
    duration_seconds: int | None
    url: str


def search_youtube(query: str, max_results: int = 10) -> list[SearchResult]:
    """Search YouTube via yt-dlp and return structured results.

    Uses yt-dlp's ytsearch prefix to perform keyword search.
    extract_flat=True returns search result metadata without fetching
    each video's full info.

    Raises MetadataFetchError if yt-dlp is not installed or search fails.
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
        "extract_flat": True,
        "no_color": True,
    }

    search_query = f"ytsearch{max_results}:{query}"

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
    except Exception as e:
        raise MetadataFetchError(f"YouTube search failed: {e}") from e

    if not info or "entries" not in info:
        return []

    results = []
    for entry in info["entries"]:
        if entry is None:
            continue
        vid_id = entry.get("id", "")
        results.append(SearchResult(
            video_id=vid_id,
            title=entry.get("title", "Unknown"),
            channel=entry.get("channel", entry.get("uploader", "Unknown")),
            duration_seconds=entry.get("duration"),
            url=entry.get("url", f"https://www.youtube.com/watch?v={vid_id}"),
        ))

    return results


@dataclass
class PlaylistInfo:
    title: str
    playlist_url: str
    video_count: int
    videos: list[SearchResult]


def fetch_playlist(playlist_url: str) -> PlaylistInfo:
    """Fetch all videos from a public YouTube playlist via yt-dlp.

    Uses extract_flat=True to get metadata without downloading each video.
    Returns PlaylistInfo with the playlist title and list of SearchResult entries.

    Raises MetadataFetchError if yt-dlp fails or playlist is empty/private.
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
        "extract_flat": True,
        "no_color": True,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
    except Exception as e:
        raise MetadataFetchError(f"Playlist fetch failed: {e}") from e

    if not info or "entries" not in info:
        raise MetadataFetchError("Playlist is empty or unavailable")

    videos = []
    for entry in info["entries"]:
        if entry is None:
            continue
        vid_id = entry.get("id", "")
        videos.append(SearchResult(
            video_id=vid_id,
            title=entry.get("title", "Unknown"),
            channel=entry.get("channel", entry.get("uploader", "Unknown")),
            duration_seconds=entry.get("duration"),
            url=entry.get("url", f"https://www.youtube.com/watch?v={vid_id}"),
        ))

    if not videos:
        raise MetadataFetchError("Playlist is empty or unavailable")

    playlist_title = info.get("title", "Unknown Playlist")

    return PlaylistInfo(
        title=playlist_title,
        playlist_url=playlist_url,
        video_count=len(videos),
        videos=videos,
    )
