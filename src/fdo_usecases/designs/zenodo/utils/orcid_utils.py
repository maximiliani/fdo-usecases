# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""ORCID utilities."""

import re


def normalize_orcid(orcid: str | None) -> str | None:
    """Normalize ORCID to standard format with dashes.

    Converts ORCID from various formats to standard XXXX-XXXX-XXXX-XXXX format.

    Args:
        orcid: ORCID string in any format (with/without dashes, with/without URL prefix)

    Returns:
        Normalized ORCID in XXXX-XXXX-XXXX-XXXX format, or None if input is None/invalid

    Example:
        >>> normalize_orcid("0000-0003-0012-2414")
        '0000-0003-0012-2414'
        >>> normalize_orcid("0000000300122414")
        '0000-0003-0012-2414'
        >>> normalize_orcid("https://orcid.org/0000-0003-0012-2414")
        '0000-0003-0012-2414'

    """
    if not orcid:
        return None

    # Remove URL prefix if present
    orcid = re.sub(r"^https?://orcid\.org/", "", orcid)

    # Remove all non-alphanumeric characters except X
    digits = re.sub(r"[^0-9X]", "", orcid)

    # Validate length (16 characters)
    if len(digits) != 16:
        return None

    # Add dashes in standard positions
    return f"{digits[0:4]}-{digits[4:8]}-{digits[8:12]}-{digits[12:16]}"


__all__ = ["normalize_orcid"]
