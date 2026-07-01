# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""Version fetching logic."""

from typing import Any

from fdo_usecases.designs.zenodo.api_clients import ZenodoAPIClient


class VersionFetcher:
    """Fetch all versions of a Zenodo record."""

    def __init__(self, api_client: ZenodoAPIClient):
        """Initialize version fetcher with API client.

        Args:
            api_client: Async HTTP client for Zenodo API

        """
        self.api_client = api_client

    async def fetch_all(self, recid: int) -> list[dict[str, Any]]:
        """Fetch all versions from /records/{recid}/versions endpoint.

        Uses the versions endpoint which returns all published versions
        of a dataset, ordered chronologically.

        Note: Some older records may not have a versions endpoint,
        in which case we return empty list and handle gracefully.

        Args:
            recid: Zenodo record ID

        Returns:
            List of version data dictionaries, empty list if none found

        """
        try:
            versions_data = await self.api_client.get(f"/records/{recid}/versions")
            return versions_data.get("hits", {}).get("hits", [])
        except Exception:
            # Versions endpoint doesn't exist for this record
            return []
