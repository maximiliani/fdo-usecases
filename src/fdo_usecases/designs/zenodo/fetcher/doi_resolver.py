# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""DOI resolution logic."""

import re
from typing import Any

from fdo_usecases.designs.zenodo.api_clients import ZenodoAPIClient
from fdo_usecases.designs.zenodo.models.exceptions import DOINotFoundError


class DOIResolver:
    """Resolve DOI to Zenodo record data."""

    def __init__(self, api_client: ZenodoAPIClient):
        """Initialize DOI resolver with API client.

        Args:
            api_client: Async HTTP client for Zenodo API

        """
        self.api_client = api_client

    async def resolve(self, doi: str) -> dict[str, Any]:
        """Resolve DOI using two strategies: direct lookup then search.

        Strategy 1: Direct record ID extraction from DOI pattern
        Strategy 2: Search API by DOI if direct lookup fails

        Args:
            doi: DOI string to resolve (e.g., "10.5281/zenodo.123456")

        Returns:
            Record data dictionary from Zenodo API

        Raises:
            DOINotFoundError: If DOI doesn't match any record

        """
        # Strategy 1: Direct record ID extraction
        # Pattern: "10.5281/zenodo.123456" → record ID 123456
        match = re.search(r"zenodo\.(\d+)", doi)
        if match:
            recid = int(match.group(1))
            try:
                return await self.api_client.get(f"/records/{recid}")
            except DOINotFoundError:
                # Direct lookup failed, fall through to search
                pass

        # Strategy 2: Search by DOI
        search_result = await self.api_client.get(f"/records?doi={doi}")
        hits = search_result.get("hits", {})
        if hits.get("total", 0) == 0:
            raise DOINotFoundError(f"DOI not found: {doi}")
        return hits["hits"][0]
