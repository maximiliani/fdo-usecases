# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Async HTTP client for ROR API."""

import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class RorApiClient:
    """Async HTTP client for ROR (Research Organization Registry) API.

    This client provides access to the ROR API for validating and fetching
    organization information by ROR ID or name search.

    Example:
        ```python
        client = RorApiClient()
        async with client:
            org = await client.get_organization("018mejw64")
            results = await client.search_by_name("KIT")
        ```

    Attributes:
        base_url: ROR API base URL
        timeout: Request timeout in seconds
        _cache: In-memory cache dict or None if disabled
        _session: Active aiohttp session or None if closed

    """

    def __init__(
        self,
        base_url: str = "https://api.ror.org",
        cache_enabled: bool = True,
        timeout: float = 30.0,
    ):
        """Initialize the ROR API client.

        Args:
            base_url: ROR API base URL
            cache_enabled: Enable response caching (recommended for performance)
            timeout: Request timeout in seconds

        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._cache: dict[str, Any] | None = {} if cache_enabled else None
        self._session: aiohttp.ClientSession | None = None

    async def get_organization(self, ror_id: str) -> dict[str, Any] | None:
        """Fetch organization by ROR ID.

        Args:
            ror_id: ROR ID (e.g., "018mejw64" without URL prefix)

        Returns:
            Organization data dictionary or None if not found

        Raises:
            ZenodoAPIError: If request fails

        """
        # Normalize ROR ID - remove URL prefix if present
        ror_clean = ror_id.replace("https://ror.org/", "")
        logger.debug(f"Fetching ROR organization data for: {ror_clean}")

        try:
            data = await self.get(f"/organizations/{ror_clean}")
            return data if data and not data.get("errors") else None
        except Exception as e:
            logger.warning(f"Failed to fetch ROR organization {ror_clean}: {e}")
            return None

    async def search_by_name(self, name: str) -> list[dict[str, Any]]:
        """Search organizations by name.

        Args:
            name: Organization name or partial name to search for

        Returns:
            List of matching organization data dictionaries

        """
        import urllib.parse

        query = urllib.parse.quote(name)
        logger.debug(f"Searching ROR organizations by name: {name}")

        try:
            data = await self.get(f"/organizations?query={query}")
            items = data.get("items", [])
            logger.debug(f"Found {len(items)} matching organizations")
            return items
        except Exception as e:
            logger.warning(f"ROR search failed for '{name}': {e}")
            return []

    async def get(self, endpoint: str) -> dict[str, Any]:
        """Make GET request with optional caching.

        Args:
            endpoint: API endpoint path

        Returns:
            Parsed JSON response as dictionary

        Raises:
            ZenodoAPIError: If session not initialized or HTTP error occurs

        """
        from fdo_usecases.designs.zenodo.models.exceptions import ZenodoAPIError

        cache_key = f"{self.base_url}{endpoint}"

        if self._cache is not None and cache_key in self._cache:
            logger.debug(f"ROR cache hit for {endpoint}")
            return self._cache[cache_key]

        if self._session is None:
            raise ZenodoAPIError(
                "Client session not initialized. Use async context manager."
            )

        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Fetching {url}")

        try:
            async with self._session.get(url) as resp:
                if resp.status == 404:
                    logger.debug(f"Organization not found: {url}")
                    return {"errors": ["Not found"]}

                if resp.status >= 400:
                    error_text = await resp.text()
                    logger.error(f"ROR API error {resp.status} for {url}: {error_text}")
                    raise ZenodoAPIError(
                        f"ROR API error {resp.status} for {url}: {error_text}"
                    )

                data = await resp.json()
                logger.debug(f"Successfully fetched {url}")

                if self._cache is not None:
                    self._cache[cache_key] = data

                return data

        except aiohttp.ClientError as e:
            logger.error(f"ROR HTTP request failed for {url}: {e}")
            raise ZenodoAPIError(f"ROR HTTP request failed for {url}: {e}") from e

    async def __aenter__(self) -> "RorApiClient":
        """Initialize aiohttp session on context manager entry."""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self._session = aiohttp.ClientSession(timeout=timeout)
        logger.debug("RorApiClient session initialized")
        return self

    async def __aexit__(
        self, exc_type: type, exc_val: Exception, exc_tb: object
    ) -> None:
        """Close aiohttp session on context manager exit."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("RorApiClient session closed")


__all__ = ["RorApiClient"]
