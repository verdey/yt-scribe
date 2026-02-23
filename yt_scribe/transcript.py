"""Transcript fetching via youtube-transcript-api."""
from __future__ import annotations

import html
import logging
from dataclasses import dataclass

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from .errors import TranscriptNotAvailableError, VideoNotFoundError

log = logging.getLogger(__name__)


@dataclass
class TranscriptSegment:
    """A single transcript segment with timestamp."""
    text: str
    start: float
    duration: float


@dataclass
class TranscriptResult:
    """Complete transcript result."""
    video_id: str
    language: str
    language_code: str
    is_generated: bool
    segments: list[TranscriptSegment]

    @property
    def duration_seconds(self) -> int:
        """Estimate video duration from last transcript segment."""
        if not self.segments:
            return 0
        last = self.segments[-1]
        return int(last.start + last.duration)

    @property
    def full_text(self) -> str:
        """Concatenated plain text of all segments."""
        return " ".join(seg.text for seg in self.segments)


def fetch_transcript(
    video_id: str,
    languages: list[str] | None = None,
) -> TranscriptResult:
    """Fetch transcript for a YouTube video.

    Args:
        video_id: 11-character YouTube video ID.
        languages: Preferred language codes, e.g. ["en", "es"].
                   Defaults to ["en"] if not specified.

    Returns:
        TranscriptResult with segments and metadata.
    """
    if languages is None:
        languages = ["en"]

    ytt_api = YouTubeTranscriptApi()

    try:
        transcript_list = ytt_api.list(video_id)
    except VideoUnavailable as e:
        raise VideoNotFoundError(
            f"Video {video_id} is unavailable: {e}"
        ) from e
    except TranscriptsDisabled as e:
        raise TranscriptNotAvailableError(
            f"Transcripts are disabled for video {video_id}"
        ) from e

    try:
        transcript = transcript_list.find_transcript(languages)
    except NoTranscriptFound:
        available = [
            f"{t.language} ({t.language_code})"
            for t in transcript_list
        ]
        raise TranscriptNotAvailableError(
            f"No transcript for languages {languages}. "
            f"Available: {', '.join(available) or 'none'}"
        )

    fetched = transcript.fetch()

    segments = [
        TranscriptSegment(
            text=html.unescape(snippet.text),
            start=snippet.start,
            duration=snippet.duration,
        )
        for snippet in fetched
    ]

    return TranscriptResult(
        video_id=fetched.video_id,
        language=fetched.language,
        language_code=fetched.language_code,
        is_generated=fetched.is_generated,
        segments=segments,
    )
