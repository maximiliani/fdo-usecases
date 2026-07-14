# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Utility functions for Zenodo FDO generation.

This module re-exports utilities from the central fdo_usecases.utils package
to maintain backward compatibility for existing imports.

"""

from fdo_usecases.utils import normalize_orcid, strip_html_and_truncate

__all__ = [
    "strip_html_and_truncate",
    "normalize_orcid",
]
