"""Tests for yt_scribe.search — mocked yt-dlp, no real API calls."""
import sys
from unittest.mock import MagicMock, patch

import pytest

from yt_scribe.errors import MetadataFetchError


def _make_mock_ytdlp(entries):
    """Create a mock yt_dlp module that returns given entries from extract_info."""
    mock_module = MagicMock()
    mock_ydl_instance = MagicMock()
    mock_ydl_instance.extract_info.return_value = {"entries": entries}
    mock_module.YoutubeDL.return_value.__enter__ = MagicMock(return_value=mock_ydl_instance)
    mock_module.YoutubeDL.return_value.__exit__ = MagicMock(return_value=False)
    return mock_module


class TestSearchYoutube:
    """Test search_youtube() with mocked yt-dlp."""

    def test_returns_search_results(self):
        mock_ytdlp = _make_mock_ytdlp([
            {
                "id": "abc12345678",
                "title": "Test Video",
                "channel": "Test Channel",
                "duration": 120,
                "url": "https://www.youtube.com/watch?v=abc12345678",
            }
        ])

        with patch.dict(sys.modules, {"yt_dlp": mock_ytdlp}):
            from yt_scribe.search import search_youtube
            results = search_youtube("test query", max_results=1)

        assert len(results) == 1
        assert results[0].video_id == "abc12345678"
        assert results[0].title == "Test Video"
        assert results[0].channel == "Test Channel"
        assert results[0].duration_seconds == 120

    def test_empty_results(self):
        mock_ytdlp = _make_mock_ytdlp([])

        with patch.dict(sys.modules, {"yt_dlp": mock_ytdlp}):
            from yt_scribe.search import search_youtube
            results = search_youtube("no results query")

        assert results == []

    def test_skips_none_entries(self):
        mock_ytdlp = _make_mock_ytdlp([
            None,
            {
                "id": "valid123456",
                "title": "Valid Video",
                "channel": "Channel",
                "duration": 60,
                "url": "https://www.youtube.com/watch?v=valid123456",
            },
            None,
        ])

        with patch.dict(sys.modules, {"yt_dlp": mock_ytdlp}):
            from yt_scribe.search import search_youtube
            results = search_youtube("test")

        assert len(results) == 1
        assert results[0].video_id == "valid123456"

    def test_handles_no_info(self):
        mock_module = MagicMock()
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = None
        mock_module.YoutubeDL.return_value.__enter__ = MagicMock(return_value=mock_ydl_instance)
        mock_module.YoutubeDL.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict(sys.modules, {"yt_dlp": mock_module}):
            from yt_scribe.search import search_youtube
            results = search_youtube("test")

        assert results == []

    def test_missing_optional_fields(self):
        mock_ytdlp = _make_mock_ytdlp([
            {
                "id": "min12345678",
                "title": "Minimal",
            }
        ])

        with patch.dict(sys.modules, {"yt_dlp": mock_ytdlp}):
            from yt_scribe.search import search_youtube
            results = search_youtube("test")

        assert len(results) == 1
        assert results[0].channel == "Unknown"
        assert results[0].duration_seconds is None

    def test_uses_uploader_fallback(self):
        mock_ytdlp = _make_mock_ytdlp([
            {
                "id": "fall1234567",
                "title": "Fallback",
                "uploader": "Uploader Name",
            }
        ])

        with patch.dict(sys.modules, {"yt_dlp": mock_ytdlp}):
            from yt_scribe.search import search_youtube
            results = search_youtube("test")

        assert results[0].channel == "Uploader Name"

    def test_constructs_url_when_missing(self):
        mock_ytdlp = _make_mock_ytdlp([
            {"id": "nourl123456", "title": "No URL"}
        ])

        with patch.dict(sys.modules, {"yt_dlp": mock_ytdlp}):
            from yt_scribe.search import search_youtube
            results = search_youtube("test")

        assert results[0].url == "https://www.youtube.com/watch?v=nourl123456"


class TestFetchPlaylist:
    """Test fetch_playlist() with mocked yt-dlp."""

    def test_returns_playlist_info(self):
        mock_module = MagicMock()
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = {
            "title": "My Playlist",
            "entries": [
                {
                    "id": "vid12345678",
                    "title": "Video 1",
                    "channel": "Channel",
                    "duration": 300,
                    "url": "https://www.youtube.com/watch?v=vid12345678",
                },
                {
                    "id": "vid23456789",
                    "title": "Video 2",
                    "channel": "Channel",
                    "duration": 200,
                    "url": "https://www.youtube.com/watch?v=vid23456789",
                },
            ],
        }
        mock_module.YoutubeDL.return_value.__enter__ = MagicMock(return_value=mock_ydl_instance)
        mock_module.YoutubeDL.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict(sys.modules, {"yt_dlp": mock_module}):
            from yt_scribe.search import fetch_playlist
            info = fetch_playlist("https://www.youtube.com/playlist?list=PLtest")

        assert info.title == "My Playlist"
        assert info.video_count == 2
        assert len(info.videos) == 2
        assert info.videos[0].video_id == "vid12345678"
        assert info.playlist_url == "https://www.youtube.com/playlist?list=PLtest"

    def test_empty_playlist_raises(self):
        mock_module = MagicMock()
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = {"entries": [None, None]}
        mock_module.YoutubeDL.return_value.__enter__ = MagicMock(return_value=mock_ydl_instance)
        mock_module.YoutubeDL.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict(sys.modules, {"yt_dlp": mock_module}):
            from yt_scribe.search import fetch_playlist
            with pytest.raises(MetadataFetchError):
                fetch_playlist("https://www.youtube.com/playlist?list=PLempty")

    def test_no_entries_raises(self):
        mock_module = MagicMock()
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = None
        mock_module.YoutubeDL.return_value.__enter__ = MagicMock(return_value=mock_ydl_instance)
        mock_module.YoutubeDL.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict(sys.modules, {"yt_dlp": mock_module}):
            from yt_scribe.search import fetch_playlist
            with pytest.raises(MetadataFetchError):
                fetch_playlist("https://www.youtube.com/playlist?list=PLbad")
