# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Shared utilities for FDO use cases package."""

from .duration import to_iso8601_duration, to_timedelta
from .logging_config import ColoredFormatter, setup_logging
from .orcid_utils import normalize_orcid
from .text_utils import strip_html_and_truncate

__all__ = [
    "setup_logging",
    "ColoredFormatter",
    "normalize_orcid",
    "strip_html_and_truncate",
    "to_iso8601_duration",
    "to_timedelta",
]
