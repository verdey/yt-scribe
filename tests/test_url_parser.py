"""Tests for yt_scribe.url_parser — pure logic, no mocks needed."""
import pytest

from yt_scribe.url_parser import extract_video_id, VIDEO_ID_RE


class TestExtractVideoId:
    """Test every URL pattern handled by extract_video_id."""

    # --- Standard watch URLs ---

    def test_standard_url(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_standard_url_with_extra_params(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120") == "dQw4w9WgXcQ"

    def test_standard_url_param_order(self):
        assert extract_video_id("https://www.youtube.com/watch?t=120&v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_standard_url_no_www(self):
        assert extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    # --- Mobile URLs ---

    def test_mobile_url(self):
        assert extract_video_id("https://m.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    # --- Short URLs ---

    def test_short_url(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url_with_timestamp(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ?t=30") == "dQw4w9WgXcQ"

    # --- Embed URLs ---

    def test_embed_url(self):
        assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    # --- Shorts URLs ---

    def test_shorts_url(self):
        assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    # --- Live URLs ---

    def test_live_url(self):
        assert extract_video_id("https://www.youtube.com/live/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    # --- Legacy /v/ URLs ---

    def test_legacy_url(self):
        assert extract_video_id("https://www.youtube.com/v/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    # --- Raw video ID ---

    def test_raw_video_id(self):
        assert extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_raw_id_with_hyphens_underscores(self):
        assert extract_video_id("a-b_c-d_e-f") == "a-b_c-d_e-f"

    # --- Whitespace handling ---

    def test_strips_whitespace(self):
        assert extract_video_id("  dQw4w9WgXcQ  ") == "dQw4w9WgXcQ"

    # --- Invalid inputs ---

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            extract_video_id("https://www.google.com")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            extract_video_id("")

    def test_too_short_id_raises(self):
        with pytest.raises(ValueError):
            extract_video_id("abc")

    def test_too_long_id_raises(self):
        with pytest.raises(ValueError):
            extract_video_id("abcdefghijkl")  # 12 chars

    def test_random_text_raises(self):
        with pytest.raises(ValueError):
            extract_video_id("not a video id at all")


class TestVideoIdRegex:
    """Test the VIDEO_ID_RE pattern directly."""

    def test_valid_11_char_alphanum(self):
        assert VIDEO_ID_RE.match("dQw4w9WgXcQ")

    def test_valid_with_hyphens(self):
        assert VIDEO_ID_RE.match("a-b-c-d-e-f")

    def test_valid_with_underscores(self):
        assert VIDEO_ID_RE.match("a_b_c_d_e_f")

    def test_rejects_10_chars(self):
        assert not VIDEO_ID_RE.match("abcdefghij")

    def test_rejects_12_chars(self):
        assert not VIDEO_ID_RE.match("abcdefghijkl")
