"""Tests for CLI utility functions — pure logic, no mocks needed."""
import pytest

from yt_scribe.cli import parse_selection, _format_duration_short


class TestParseSelection:
    """Test parse_selection() input parsing."""

    def test_single_number(self):
        assert parse_selection("3", 10) == [3]

    def test_comma_separated(self):
        assert parse_selection("1,3,5", 10) == [1, 3, 5]

    def test_range(self):
        assert parse_selection("1-5", 10) == [1, 2, 3, 4, 5]

    def test_mixed_ranges_and_numbers(self):
        assert parse_selection("1-3,7,9-10", 10) == [1, 2, 3, 7, 9, 10]

    def test_all(self):
        assert parse_selection("all", 5) == [1, 2, 3, 4, 5]

    def test_all_case_insensitive(self):
        assert parse_selection("ALL", 3) == [1, 2, 3]

    def test_deduplication(self):
        assert parse_selection("1,1,2,2", 5) == [1, 2]

    def test_preserves_order(self):
        assert parse_selection("5,3,1", 5) == [5, 3, 1]

    def test_strips_whitespace(self):
        assert parse_selection("  1 , 3 , 5  ", 10) == [1, 3, 5]

    # --- Error cases ---

    def test_out_of_bounds_high_raises(self):
        with pytest.raises(ValueError):
            parse_selection("11", 10)

    def test_out_of_bounds_zero_raises(self):
        with pytest.raises(ValueError):
            parse_selection("0", 10)

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_selection("", 10)

    def test_invalid_range_reversed_raises(self):
        with pytest.raises(ValueError):
            parse_selection("5-3", 10)

    def test_range_out_of_bounds_raises(self):
        with pytest.raises(ValueError):
            parse_selection("8-12", 10)


class TestFormatDurationShort:
    """Test _format_duration_short() formatting."""

    def test_seconds_only(self):
        assert _format_duration_short(45) == " 0:45"

    def test_minutes_seconds(self):
        assert _format_duration_short(125) == " 2:05"

    def test_exact_minute(self):
        assert _format_duration_short(60) == " 1:00"

    def test_hours(self):
        assert _format_duration_short(3661) == "1:01:01"

    def test_zero(self):
        assert _format_duration_short(0) == " 0:00"

    def test_none(self):
        assert _format_duration_short(None) == "  ???"

    def test_float_input(self):
        # Should truncate to int
        assert _format_duration_short(65.9) == " 1:05"


