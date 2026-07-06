# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Text processing utilities."""

import re


def strip_html_and_truncate(text: str | None, max_words: int = 500) -> str | None:
    """Remove HTML tags and truncate text to maximum word count.

    Args:
        text: Input text potentially containing HTML tags
        max_words: Maximum number of words before truncation (default: 500)

    Returns:
        Cleaned text with HTML removed and truncated if necessary,
        or None if input was None or empty

    Example:
        >>> strip_html_and_truncate("<p>Hello <b>World</b></p>", max_words=2)
        'Hello World'
        >>> strip_html_and_truncate(None)
        None

    """
    if not text:
        return None

    # Remove HTML tags
    clean = re.sub(r"<[^>]+>", "", text)

    # Normalize whitespace
    clean = re.sub(r"\s+", " ", clean).strip()

    # Truncate if necessary
    words = clean.split()
    if len(words) > max_words:
        return " ".join(words[:max_words]) + "..."

    return clean


__all__ = ["strip_html_and_truncate"]
