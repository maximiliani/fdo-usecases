# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Async HTTP client for CrossRef Funder Registry API."""

import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class CrossrefFunderApiClient:
    """Async HTTP client for CrossRef Funder Registry API.

    This client provides access to the CrossRef Funder Registry, which contains
    persistent identifiers (DOIs) for funding organizations worldwide.

    Example:
        ```python
        client = CrossrefFunderApiClient()
        async with client:
            funder = await client.get_funder("10.13039/501100001659")
            results = await client.search_by_name("Deutsche Forschungsgemeinschaft")
        ```

    Attributes:
        base_url: CrossRef Funder Registry API base URL
        timeout: Request timeout in seconds
        _cache: In-memory cache dict or None if disabled
        _session: Active aiohttp session or None if closed

    """

    def __init__(
        self,
        base_url: str = "https://api.crossref.org/funders",
        cache_enabled: bool = True,
        timeout: float = 30.0,
    ):
        """Initialize the CrossRef Funder API client.

        Args:
            base_url: CrossRef Funder Registry API base URL
            cache_enabled: Enable response caching (recommended for performance)
            timeout: Request timeout in seconds

        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._cache: dict[str, Any] | None = {} if cache_enabled else None
        self._session: aiohttp.ClientSession | None = None

    async def get_funder(self, doi: str) -> dict[str, Any] | None:
        """Fetch funder by DOI.

        Args:
            doi: Funder DOI (e.g., "10.13039/501100001659" or full URL)

        Returns:
            Funder data dictionary or None if not found

        Raises:
            ZenodoAPIError: If request fails

        """
        # Normalize DOI - remove URL prefix if present
        doi_clean = doi.replace("https://doi.org/", "")
        logger.debug(f"Fetching funder data for DOI: {doi_clean}")

        try:
            data = await self.get(f"/{doi_clean}")
            return data.get("message", {})
        except Exception as e:
            logger.warning(f"Failed to fetch funder {doi_clean}: {e}")
            return None

    async def search_by_name(self, name: str) -> list[dict[str, Any]]:
        """Search funders by name.

        Args:
            name: Funder name or partial name to search for

        Returns:
            List of matching funder data dictionaries

        """
        import urllib.parse

        query = urllib.parse.quote(name)
        logger.debug(f"Searching funders by name: {name}")

        try:
            data = await self.get(f"?query={query}")
            items = data.get("message", {}).get("items", [])
            logger.debug(f"Found {len(items)} matching funders")
            return items
        except Exception as e:
            logger.warning(f"Funder search failed for '{name}': {e}")
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
            logger.debug(f"CrossRef cache hit for {endpoint}")
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
                    logger.debug(f"Funder not found: {url}")
                    return {"message": {}}

                if resp.status >= 400:
                    error_text = await resp.text()
                    logger.error(
                        f"CrossRef API error {resp.status} for {url}: {error_text}"
                    )
                    raise ZenodoAPIError(
                        f"CrossRef API error {resp.status} for {url}: {error_text}"
                    )

                data = await resp.json()
                logger.debug(f"Successfully fetched {url}")

                if self._cache is not None:
                    self._cache[cache_key] = data

                return data

        except aiohttp.ClientError as e:
            logger.error(f"CrossRef HTTP request failed for {url}: {e}")
            raise ZenodoAPIError(f"CrossRef HTTP request failed for {url}: {e}") from e

    async def __aenter__(self) -> "CrossrefFunderApiClient":
        """Initialize aiohttp session on context manager entry."""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self._session = aiohttp.ClientSession(timeout=timeout)
        logger.debug("CrossrefFunderApiClient session initialized")
        return self

    async def __aexit__(
        self, exc_type: type, exc_val: Exception, exc_tb: object
    ) -> None:
        """Close aiohttp session on context manager exit."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("CrossrefFunderApiClient session closed")


__all__ = ["CrossrefFunderApiClient"]
