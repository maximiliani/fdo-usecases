# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Duration conversion utilities.

Convert a numeric value paired with a unit into either a Python
``timedelta`` or an ISO 8601 duration string.

Supported units (case-insensitive, with common aliases):

    ns, us, μs, ms, s, sec, min, h, hr, d, day, w, week, mo, month, y, yr

ISO 8601 durations have the form ``P[n]Y[n]M[n]DT[n]H[n]M[n]S`` (or
``P[n]W`` for weeks, which must stand alone).  ISO 8601 has no dedicated
unit for sub-second values; these are expressed as fractional seconds
(e.g. ``PT0.5S``).

Python ``timedelta`` only stores days, seconds and microseconds, so it
cannot represent calendar years or months.  For ``y`` and ``mo`` a
nominal conversion is used (1 year = 365 days, 1 month = 30 days) and a
warning is logged.  Values finer than one microsecond are rounded to the
nearest microsecond when building a ``timedelta``; the ISO 8601 string
preserves the original precision via fractional seconds.

Example:
    >>> to_iso8601_duration(5, "h")
    'PT5H'
    >>> to_iso8601_duration(90, "min")
    'PT1H30M'
    >>> to_iso8601_duration(2, "y")
    'P2Y'
    >>> to_timedelta(90, "min")
    datetime.timedelta(seconds=5400)

"""

import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

# Canonical unit -> multiplier in seconds.
# Years and months use nominal lengths (365 d / 30 d) and emit a warning
# when converted to a timedelta, since they cannot be represented exactly.
_UNIT_TO_SECONDS: dict[str, float] = {
    "ns": 1e-9,
    "us": 1e-6,
    "μs": 1e-6,
    "ms": 1e-3,
    "s": 1.0,
    "min": 60.0,
    "h": 3600.0,
    "d": 86400.0,
    "w": 604800.0,
    "mo": 30 * 86400.0,
    "y": 365 * 86400.0,
}

# Alias -> canonical unit key.
_ALIASES: dict[str, str] = {
    "ns": "ns",
    "nanosecond": "ns",
    "nanoseconds": "ns",
    "us": "us",
    "μs": "us",
    "microsecond": "us",
    "microseconds": "us",
    "ms": "ms",
    "millisecond": "ms",
    "milliseconds": "ms",
    "s": "s",
    "sec": "s",
    "second": "s",
    "seconds": "s",
    "min": "min",
    "minute": "min",
    "minutes": "min",
    "h": "h",
    "hr": "h",
    "hour": "h",
    "hours": "h",
    "d": "d",
    "day": "d",
    "days": "d",
    "w": "w",
    "week": "w",
    "weeks": "w",
    "mo": "mo",
    "month": "mo",
    "months": "mo",
    "y": "y",
    "yr": "y",
    "year": "y",
    "years": "y",
}

# Units that ISO 8601 represents in the date part (before the "T") and
# that cannot round-trip through a timedelta without a nominal conversion.
_CALENDAR_UNITS = {"y", "mo"}
# Units that ISO 8601 represents with the standalone weeks designator.
_WEEK_UNITS = {"w"}


def _canonical_unit(unit: str) -> str:
    """Return the canonical unit key for ``unit`` or raise ``ValueError``."""
    key = _ALIASES.get(unit.lower())
    if key is None:
        raise ValueError(f"Unsupported duration unit: {unit!r}")
    return key


def _format_number(n: float) -> str:
    """Format a number for inclusion in an ISO 8601 duration component.

    Uses fixed-point notation (never scientific) with up to nine decimal
    places, stripping trailing zeros and a trailing decimal point.  This
    keeps sub-second values readable (``0.000001`` rather than ``1e-06``)
    while rendering integral values without a decimal point (``5`` not
    ``5.0``).
    """
    s = f"{n:.9f}".rstrip("0").rstrip(".")
    return s if s else "0"


def to_timedelta(value: float, unit: str) -> timedelta:
    """Convert ``value`` in ``unit`` to a ``timedelta``.

    Years and months are converted using nominal lengths (1 y = 365 d,
    1 mo = 30 d) and a warning is logged, since ``timedelta`` cannot
    represent calendar units exactly.  Sub-microsecond precision is
    rounded to the nearest microsecond.

    Args:
        value: Numeric duration value.
        unit: Unit of the value (e.g. "h", "min", "ms", "y").

    Returns:
        A ``timedelta`` approximating the requested duration.

    Raises:
        ValueError: If ``unit`` is not supported.

    Example:
        >>> to_timedelta(90, "min")
        datetime.timedelta(seconds=5400)

    """
    key = _canonical_unit(unit)
    if key in _CALENDAR_UNITS:
        logger.warning(
            "Converting %r %s to timedelta using a nominal %s; "
            "calendar units cannot be represented exactly.",
            value,
            unit,
            "year (365 d)" if key == "y" else "month (30 d)",
        )
    seconds = value * _UNIT_TO_SECONDS[key]
    return timedelta(seconds=seconds)


def to_iso8601_duration(value: float, unit: str) -> str:
    """Convert ``value`` in ``unit`` to an ISO 8601 duration string.

    The string is normalized: durations are decomposed into the largest
    applicable ISO 8601 units.  For example ``90 min`` becomes
    ``"PT1H30M"`` rather than ``"PT90M"``.

    Years and months are emitted directly as ``P[n]Y`` / ``P[n]M`` (date
    part), since they are nominal calendar units.  Weeks are emitted as
    the standalone ``P[n]W`` form.  All other units are decomposed into
    days, hours, minutes and (possibly fractional) seconds.

    Args:
        value: Numeric duration value.
        unit: Unit of the value (e.g. "h", "min", "ms", "y").

    Returns:
        An ISO 8601 duration string such as ``"PT5H"``, ``"PT1H30M"``,
        ``"P2Y"`` or ``"P3W"``.

    Raises:
        ValueError: If ``unit`` is not supported.

    Example:
        >>> to_iso8601_duration(5, "h")
        'PT5H'
        >>> to_iso8601_duration(90, "min")
        'PT1H30M'
        >>> to_iso8601_duration(500, "ns")
        'PT0.0000005S'
        >>> to_iso8601_duration(2, "y")
        'P2Y'

    """
    key = _canonical_unit(unit)

    if key in _WEEK_UNITS:
        return f"P{_format_number(value)}W"

    if key in _CALENDAR_UNITS:
        designator = "Y" if key == "y" else "M"
        return f"P{_format_number(value)}{designator}"

    # Sub-second and time-of-day units: preserve sub-microsecond precision
    # in the string by decomposing from the raw total seconds rather than
    # from a rounded timedelta.
    total_seconds = value * _UNIT_TO_SECONDS[key]
    if total_seconds == 0:
        return "PT0S"

    days = int(total_seconds // 86400)
    remaining = total_seconds - days * 86400

    hours = int(remaining // 3600)
    remaining -= hours * 3600

    minutes = int(remaining // 60)
    remaining -= minutes * 60

    seconds = remaining

    parts: list[str] = ["P"]
    if days:
        parts.append(f"{days}D")

    time_parts: list[str] = []
    if hours:
        time_parts.append(f"{hours}H")
    if minutes:
        time_parts.append(f"{minutes}M")
    if seconds:
        time_parts.append(f"{_format_number(seconds)}S")

    if time_parts:
        parts.append("T")
        parts.extend(time_parts)

    return "".join(parts)


__all__ = ["to_iso8601_duration", "to_timedelta"]
