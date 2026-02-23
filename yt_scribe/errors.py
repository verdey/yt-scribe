"""Custom exceptions for yt-scribe."""


class YtScribeError(Exception):
    """Base exception for all yt-scribe errors."""


class VideoNotFoundError(YtScribeError):
    """Video does not exist or is private/unavailable."""


class TranscriptNotAvailableError(YtScribeError):
    """No transcript available for the requested video/language."""


class MetadataFetchError(YtScribeError):
    """Failed to fetch video metadata."""
