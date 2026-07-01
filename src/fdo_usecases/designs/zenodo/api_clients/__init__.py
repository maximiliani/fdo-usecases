# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""API clients for Zenodo and ORCID services.

This package provides async HTTP clients for:
- Zenodo REST API (standard endpoints)
- Zenodo Export API (structured metadata with ROR IDs)
- ORCID public API (researcher profiles and affiliations)
"""

from .orcid import OrcidApiClient
from .zenodo import ZenodoAPIClient, ZenodoExportApiClient

__all__ = ["ZenodoAPIClient", "ZenodoExportApiClient", "OrcidApiClient"]
