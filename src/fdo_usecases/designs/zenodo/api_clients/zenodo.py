# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""Async HTTP clients for Zenodo API endpoints.

This module provides async HTTP client wrappers for interacting with Zenodo:
- ZenodoAPIClient: Standard REST API (records, versions, search)
- ZenodoExportApiClient: Export endpoint with structured affiliation data (ROR IDs)

Both clients support response caching and proper error handling.
"""

import logging
from typing import Any

import aiohttp

from fdo_usecases.designs.zenodo.models.exceptions import (
    DOINotFoundError,
    RateLimitError,
    ZenodoAPIError,
)

logger = logging.getLogger(__name__)


class ZenodoAPIClient:
    """Async HTTP client for Zenodo REST API with optional in-memory caching.

    This client manages the aiohttp session lifecycle and provides automatic
    caching of API responses. It should be used as an async context manager
    to ensure proper session cleanup.

    Example:
        ```python
        client = ZenodoAPIClient(cache_enabled=True, timeout=30.0)
        async with client:
            data = await client.get("/records/20132712")
            # Second call returns cached result
            data2 = await client.get("/records/20132712")
        ```

    Attributes:
        base_url: Zenodo API base URL (default: "https://zenodo.org/api")
        timeout: Request timeout in seconds (default: 30.0)
        _cache: In-memory cache dict or None if disabled
        _session: Active aiohttp session or None if closed

    """

    def __init__(
        self,
        base_url: str = "https://zenodo.org/api",
        cache_enabled: bool = True,
        timeout: float = 30.0,
    ):
        """Initialize the API client.

        Args:
            base_url: Zenodo API base URL
            cache_enabled: Enable response caching (recommended for performance)
            timeout: Request timeout in seconds

        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._cache: dict[str, Any] | None = {} if cache_enabled else None
        self._session: aiohttp.ClientSession | None = None

    async def get(self, endpoint: str) -> dict[str, Any]:
        """Make GET request with optional caching.

        Handles HTTP status codes and converts them to appropriate exceptions:
        - 404 → DOINotFoundError
        - 429 → RateLimitError (with Retry-After if provided)
        - 4xx/5xx → ZenodoAPIError

        Args:
            endpoint: API endpoint path (e.g., "/records/20132712")

        Returns:
            Parsed JSON response as dictionary

        Raises:
            ZenodoAPIError: If session not initialized or HTTP error occurs
            DOINotFoundError: If resource doesn't exist (404)
            RateLimitError: If rate limited (429)

        """
        cache_key = f"{self.base_url}{endpoint}"

        # Return cached response if available
        if self._cache is not None and cache_key in self._cache:
            logger.debug(f"Cache hit for {endpoint}")
            return self._cache[cache_key]

        # Validate session is active
        if self._session is None:
            raise ZenodoAPIError(
                "Client session not initialized. Use async context manager."
            )

        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Fetching {url}")

        try:
            async with self._session.get(url) as resp:
                # Handle specific HTTP status codes
                if resp.status == 404:
                    logger.warning(f"Resource not found: {url}")
                    raise DOINotFoundError(f"Resource not found: {url}")

                if resp.status == 429:
                    retry_after = resp.headers.get("Retry-After")
                    retry_after_float = float(retry_after) if retry_after else None
                    logger.warning(f"Rate limit exceeded for {url}")
                    raise RateLimitError(
                        f"Rate limit exceeded for {url}", retry_after=retry_after_float
                    )

                # Generic error for other 4xx/5xx responses
                if resp.status >= 400:
                    error_text = await resp.text()
                    logger.error(f"API error {resp.status} for {url}: {error_text}")
                    raise ZenodoAPIError(
                        f"API error {resp.status} for {url}: {error_text}"
                    )

                # Parse successful response as JSON
                data = await resp.json()
                logger.debug(f"Successfully fetched {url}")

                # Cache the response if caching is enabled
                if self._cache is not None:
                    self._cache[cache_key] = data

                return data

        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed for {url}: {e}")
            raise ZenodoAPIError(f"HTTP request failed for {url}: {e}") from e

    async def __aenter__(self) -> "ZenodoAPIClient":
        """Initialize aiohttp session on context manager entry."""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self._session = aiohttp.ClientSession(timeout=timeout)
        logger.debug("ZenodoAPIClient session initialized")
        return self

    async def __aexit__(
        self, exc_type: type, exc_val: Exception, exc_tb: object
    ) -> None:
        """Close aiohttp session on context manager exit."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("ZenodoAPIClient session closed")


class ZenodoExportApiClient:
    """Async HTTP client for Zenodo export endpoints with structured metadata.

    This client fetches Zenodo records via export endpoints that provide
    structured affiliation data with ROR identifiers.

    Example:
        ```python
        client = ZenodoExportApiClient()
        async with client:
            record = await client.get_record_export(20132712)
            creators = record["metadata"]["creators"]
            # creators[0]["affiliations"][0]["identifiers"][0]["scheme"] == "ror"
        ```

    Attributes:
        base_url: Zenodo export base URL
        timeout: Request timeout in seconds
        _cache: In-memory cache dict or None if disabled
        _session: Active aiohttp session or None if closed

    """

    def __init__(
        self,
        base_url: str = "https://zenodo.org/records",
        cache_enabled: bool = True,
        timeout: float = 30.0,
    ):
        """Initialize the Zenodo export API client.

        Args:
            base_url: Zenodo records base URL
            cache_enabled: Enable response caching
            timeout: Request timeout in seconds

        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._cache: dict[str, Any] | None = {} if cache_enabled else None
        self._session: aiohttp.ClientSession | None = None

    async def get_record_export(self, recid: int) -> dict[str, Any]:
        """Fetch record via Zenodo export JSON endpoint.

        This endpoint provides structured creator affiliations with ROR identifiers.

        Args:
            recid: Zenodo record ID

        Returns:
            Complete record export data dictionary

        Raises:
            ZenodoAPIError: If request fails

        """
        logger.info(f"Fetching export data for record {recid}")
        return await self.get(f"/{recid}/export/json")

    async def get(self, endpoint: str) -> dict[str, Any]:
        """Make GET request with optional caching.

        Args:
            endpoint: API endpoint path

        Returns:
            Parsed JSON response as dictionary

        Raises:
            ZenodoAPIError: If session not initialized or HTTP error occurs

        """
        cache_key = f"{self.base_url}{endpoint}"

        if self._cache is not None and cache_key in self._cache:
            logger.debug(f"Cache hit for {endpoint}")
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
                    logger.warning(f"Resource not found: {url}")
                    raise DOINotFoundError(f"Resource not found: {url}")

                if resp.status == 429:
                    retry_after = resp.headers.get("Retry-After")
                    retry_after_float = float(retry_after) if retry_after else None
                    logger.warning(f"Rate limit exceeded for {url}")
                    raise RateLimitError(
                        f"Rate limit exceeded for {url}",
                        retry_after=retry_after_float,
                    )

                if resp.status >= 400:
                    error_text = await resp.text()
                    logger.error(f"API error {resp.status} for {url}: {error_text}")
                    raise ZenodoAPIError(
                        f"API error {resp.status} for {url}: {error_text}"
                    )

                data = await resp.json()
                logger.debug(f"Successfully fetched {url}")

                if self._cache is not None:
                    self._cache[cache_key] = data

                return data

        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed for {url}: {e}")
            raise ZenodoAPIError(f"HTTP request failed for {url}: {e}") from e

    async def __aenter__(self) -> "ZenodoExportApiClient":
        """Initialize aiohttp session on context manager entry."""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self._session = aiohttp.ClientSession(timeout=timeout)
        logger.debug("ZenodoExportApiClient session initialized")
        return self

    async def __aexit__(
        self, exc_type: type, exc_val: Exception, exc_tb: object
    ) -> None:
        """Close aiohttp session on context manager exit."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("ZenodoExportApiClient session closed")


__all__ = ["ZenodoAPIClient", "ZenodoExportApiClient"]
