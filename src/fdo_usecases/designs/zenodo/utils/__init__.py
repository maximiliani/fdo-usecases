# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""Utility functions for Zenodo FDO generation."""

from fdo_usecases.designs.zenodo.utils.orcid_utils import normalize_orcid
from fdo_usecases.designs.zenodo.utils.text_utils import strip_html_and_truncate

__all__ = [
    "strip_html_and_truncate",
    "normalize_orcid",
]
