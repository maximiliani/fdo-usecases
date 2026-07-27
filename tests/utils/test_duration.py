# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for duration conversion utilities."""

from datetime import timedelta

import pytest

from fdo_usecases.utils.duration import to_iso8601_duration, to_timedelta


class TestToTimedelta:
    """Tests for to_timedelta."""

    @pytest.mark.parametrize(
        "value,unit,expected",
        [
            (90, "min", timedelta(seconds=5400)),
            (5, "h", timedelta(hours=5)),
            (2, "d", timedelta(days=2)),
            (1, "s", timedelta(seconds=1)),
            (1000, "ms", timedelta(seconds=1)),
            (1_000_000, "us", timedelta(seconds=1)),
            (1.5, "h", timedelta(hours=1, minutes=30)),
            (0, "h", timedelta(0)),
        ],
    )
    def test_known_conversions(self, value, unit, expected):
        assert to_timedelta(value, unit) == expected

    def test_nanoseconds_rounded_to_microsecond(self):
        # 300 ns is below microsecond resolution and rounds to 0.
        assert to_timedelta(300, "ns") == timedelta(0)
        # 1300 ns rounds to 1 microsecond.
        assert to_timedelta(1300, "ns") == timedelta(microseconds=1)

    def test_year_uses_nominal_365_days(self, caplog):
        with caplog.at_level("WARNING", logger="fdo_usecases.utils.duration"):
            result = to_timedelta(1, "y")
        assert result == timedelta(days=365)
        assert "nominal" in caplog.text

    def test_month_uses_nominal_30_days(self, caplog):
        with caplog.at_level("WARNING", logger="fdo_usecases.utils.duration"):
            result = to_timedelta(2, "mo")
        assert result == timedelta(days=60)
        assert "nominal" in caplog.text

    @pytest.mark.parametrize(
        "unit,expected_seconds",
        [
            ("h", 3600),
            ("hr", 3600),
            ("hours", 3600),
            ("min", 60),
            ("minutes", 60),
            ("s", 1),
            ("sec", 1),
            ("seconds", 1),
            ("d", 86400),
            ("days", 86400),
            ("ms", 0.001),
            ("us", 1e-6),
            ("μs", 1e-6),
        ],
    )
    def test_unit_aliases(self, unit, expected_seconds):
        assert to_timedelta(1, unit) == timedelta(seconds=expected_seconds)

    def test_case_insensitive(self):
        assert to_timedelta(1, "H") == timedelta(hours=1)
        assert to_timedelta(1, "Min") == timedelta(minutes=1)

    def test_unsupported_unit_raises(self):
        with pytest.raises(ValueError, match="Unsupported duration unit"):
            to_timedelta(1, "fortnights")


class TestToIso8601Duration:
    """Tests for to_iso8601_duration."""

    @pytest.mark.parametrize(
        "value,unit,expected",
        [
            (5, "h", "PT5H"),
            (1, "d", "P1D"),
            (1, "s", "PT1S"),
            (0, "h", "PT0S"),
            (0, "min", "PT0S"),
            (2, "y", "P2Y"),
            (3, "mo", "P3M"),
            (2, "w", "P2W"),
            (1.5, "y", "P1.5Y"),
            (1.5, "w", "P1.5W"),
        ],
    )
    def test_direct_outputs(self, value, unit, expected):
        assert to_iso8601_duration(value, unit) == expected

    def test_normalizes_minutes_to_hours(self):
        # 90 min -> 1 hour 30 min (normalized, not PT90M)
        assert to_iso8601_duration(90, "min") == "PT1H30M"

    def test_normalizes_seconds_to_minutes(self):
        assert to_iso8601_duration(120, "s") == "PT2M"

    def test_normalizes_hours_to_days(self):
        assert to_iso8601_duration(48, "h") == "P2D"

    def test_combined_days_hours_minutes_seconds(self):
        # 1 day, 2 hours, 3 minutes, 4 seconds = 93784 seconds
        assert to_iso8601_duration(93784, "s") == "P1DT2H3M4S"

    def test_fractional_seconds_preserved(self):
        assert to_iso8601_duration(0.5, "s") == "PT0.5S"

    def test_milliseconds_become_fractional_seconds(self):
        assert to_iso8601_duration(500, "ms") == "PT0.5S"

    def test_microseconds_become_fractional_seconds(self):
        assert to_iso8601_duration(1, "us") == "PT0.000001S"

    def test_nanoseconds_preserved_below_microsecond(self):
        # Sub-microsecond precision is preserved in the string even though
        # timedelta cannot represent it.
        assert to_iso8601_duration(500, "ns") == "PT0.0000005S"

    def test_weeks_standalone_no_time_part(self):
        # ISO 8601 weeks form must stand alone (no T... part).
        result = to_iso8601_duration(3, "w")
        assert result == "P3W"
        assert "T" not in result

    def test_year_month_no_warning_logged(self, caplog):
        # Emitting P2Y / P3M does not require nominal conversion, so no
        # warning should be logged (unlike to_timedelta).
        with caplog.at_level("WARNING", logger="fdo_usecases.utils.duration"):
            to_iso8601_duration(2, "y")
            to_iso8601_duration(3, "mo")
        assert caplog.text == ""

    def test_case_insensitive(self):
        assert to_iso8601_duration(5, "H") == "PT5H"

    def test_unsupported_unit_raises(self):
        with pytest.raises(ValueError, match="Unsupported duration unit"):
            to_iso8601_duration(1, "fortnights")


class TestRoundTrip:
    """Sanity checks that both functions agree on representable values."""

    @pytest.mark.parametrize(
        "value,unit",
        [
            (90, "min"),
            (5, "h"),
            (2, "d"),
            (93784, "s"),
            (0.5, "s"),
        ],
    )
    def test_iso_matches_timedelta_decomposition(self, value, unit):
        td = to_timedelta(value, unit)
        # Reconstruct expected ISO from the timedelta itself.
        if td == timedelta(0):
            expected = "PT0S"
        else:
            days = td.days
            secs = td.seconds
            hours = secs // 3600
            minutes = (secs % 3600) // 60
            seconds = secs % 60 + td.microseconds / 1e6
            parts = ["P"]
            if days:
                parts.append(f"{days}D")
            time_parts = []
            if hours:
                time_parts.append(f"{hours}H")
            if minutes:
                time_parts.append(f"{minutes}M")
            if seconds:
                if seconds == int(seconds):
                    time_parts.append(f"{int(seconds)}S")
                else:
                    time_parts.append(f"{seconds}S")
            if time_parts:
                parts.append("T")
                parts.extend(time_parts)
            expected = "".join(parts)
        assert to_iso8601_duration(value, unit) == expected
