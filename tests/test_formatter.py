"""Tests for yt_scribe.formatter — pure logic, no mocks needed."""
import json

from yt_scribe.metadata import VideoMetadata
from yt_scribe.transcript import TranscriptSegment, TranscriptResult
from yt_scribe.formatter import format_markdown, format_json, generate_filename


def _make_metadata(**overrides) -> VideoMetadata:
    defaults = dict(
        video_id="test123abcd",
        title="Test Video Title",
        channel="Test Channel",
        channel_url="https://youtube.com/@test",
        source="oembed",
    )
    defaults.update(overrides)
    return VideoMetadata(**defaults)


def _make_transcript(**overrides) -> TranscriptResult:
    defaults = dict(
        video_id="test123abcd",
        language="English",
        language_code="en",
        is_generated=False,
        segments=[
            TranscriptSegment(text="Hello world", start=0.0, duration=2.5),
            TranscriptSegment(text="This is a test", start=2.5, duration=3.0),
        ],
    )
    defaults.update(overrides)
    return TranscriptResult(**defaults)


class TestGenerateFilename:
    """Test generate_filename() sanitization."""

    def test_basic_title(self):
        meta = _make_metadata(title="My Video")
        assert generate_filename(meta) == "My_Video_test123abcd"

    def test_special_chars_replaced(self):
        meta = _make_metadata(title="Test: Video! #1 (HD)")
        result = generate_filename(meta)
        assert result == "Test__Video___1__HD__test123abcd"

    def test_hyphens_preserved(self):
        meta = _make_metadata(title="A-B-C")
        assert generate_filename(meta) == "A-B-C_test123abcd"

    def test_long_title_truncated(self):
        meta = _make_metadata(title="A" * 100)
        result = generate_filename(meta)
        # Title portion should be truncated to 80 chars max
        title_part = result.rsplit("_test123abcd", 1)[0]
        assert len(title_part) <= 80

    def test_spaces_become_underscores(self):
        meta = _make_metadata(title="Hello   World")
        assert generate_filename(meta) == "Hello_World_test123abcd"


class TestFormatMarkdown:
    """Test format_markdown() output structure."""

    def test_has_yaml_frontmatter(self):
        md = format_markdown(_make_metadata(), _make_transcript())
        assert md.startswith("---\n")
        # Should have opening and closing ---
        parts = md.split("---")
        assert len(parts) >= 3

    def test_frontmatter_contains_title(self):
        md = format_markdown(_make_metadata(title="My Title"), _make_transcript())
        assert 'title: "My Title"' in md

    def test_frontmatter_contains_channel(self):
        md = format_markdown(_make_metadata(channel="My Channel"), _make_transcript())
        assert 'channel: "My Channel"' in md

    def test_frontmatter_contains_video_id(self):
        md = format_markdown(_make_metadata(), _make_transcript())
        assert 'video_id: "test123abcd"' in md

    def test_includes_duration_when_present(self):
        md = format_markdown(
            _make_metadata(duration_seconds=125),
            _make_transcript(),
        )
        assert 'duration: "2m 5s"' in md

    def test_includes_upload_date_when_present(self):
        md = format_markdown(
            _make_metadata(upload_date="2024-01-15"),
            _make_transcript(),
        )
        assert 'upload_date: "2024-01-15"' in md
        assert "**Uploaded:** 2024-01-15" in md

    def test_omits_duration_when_none(self):
        md = format_markdown(
            _make_metadata(duration_seconds=None),
            _make_transcript(segments=[]),
        )
        assert "duration:" not in md

    def test_contains_transcript_heading(self):
        md = format_markdown(_make_metadata(), _make_transcript())
        assert "## Transcript" in md

    def test_contains_timestamps(self):
        md = format_markdown(_make_metadata(), _make_transcript())
        assert "**[0:00]** Hello world" in md
        assert "**[0:02]** This is a test" in md

    def test_language_info(self):
        md = format_markdown(_make_metadata(), _make_transcript(is_generated=True))
        assert "auto-generated" in md

    def test_manual_transcript_label(self):
        md = format_markdown(_make_metadata(), _make_transcript(is_generated=False))
        assert "manual" in md


class TestFormatJson:
    """Test format_json() output structure."""

    def test_valid_json(self):
        output = format_json(_make_metadata(), _make_transcript())
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_contains_required_fields(self):
        output = format_json(_make_metadata(), _make_transcript())
        data = json.loads(output)
        assert data["video_id"] == "test123abcd"
        assert data["title"] == "Test Video Title"
        assert data["channel"] == "Test Channel"
        assert data["language"] == "English"

    def test_segments_structure(self):
        output = format_json(_make_metadata(), _make_transcript())
        data = json.loads(output)
        assert len(data["segments"]) == 2
        seg = data["segments"][0]
        assert seg["text"] == "Hello world"
        assert seg["start"] == 0.0
        assert "timestamp" in seg

    def test_none_fields_handled(self):
        output = format_json(
            _make_metadata(duration_seconds=None, upload_date=None, thumbnail_url=None),
            _make_transcript(),
        )
        data = json.loads(output)
        assert data["upload_date"] is None
        assert data["thumbnail_url"] is None

    def test_url_format(self):
        output = format_json(_make_metadata(), _make_transcript())
        data = json.loads(output)
        assert data["url"] == "https://www.youtube.com/watch?v=test123abcd"
