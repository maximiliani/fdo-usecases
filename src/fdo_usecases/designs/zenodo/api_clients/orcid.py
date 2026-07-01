# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Async HTTP client for ORCID public API.

This module provides an async HTTP client wrapper for interacting with the ORCID
public API v3.0 to fetch researcher profile data, employment history, and education records.
"""

import logging
from typing import Any

import aiohttp

from fdo_usecases.designs.zenodo.models.exceptions import RateLimitError, ZenodoAPIError

logger = logging.getLogger(__name__)


class OrcidApiClient:
    """Async HTTP client for ORCID public API with optional in-memory caching.

    This client provides access to public ORCID profile data without authentication.
    It should be used as an async context manager to ensure proper session cleanup.

    Example:
        ```python
        client = OrcidApiClient(cache_enabled=True)
        async with client:
            profile = await client.get_profile("0000-0000-0000-0000")
            employments = await client.get_employments("0000-0000-0000-0000")
        ```

    Attributes:
        base_url: ORCID API base URL (default: "https://pub.orcid.org/v3.0")
        timeout: Request timeout in seconds (default: 30.0)
        _cache: In-memory cache dict or None if disabled
        _session: Active aiohttp session or None if closed

    """

    def __init__(
        self,
        base_url: str = "https://pub.orcid.org/v3.0",
        cache_enabled: bool = True,
        timeout: float = 30.0,
    ):
        """Initialize the ORCID API client.

        Args:
            base_url: ORCID API base URL
            cache_enabled: Enable response caching (recommended for performance)
            timeout: Request timeout in seconds

        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._cache: dict[str, Any] | None = {} if cache_enabled else None
        self._session: aiohttp.ClientSession | None = None

    async def get_profile(self, orcid: str) -> dict[str, Any]:
        """Fetch complete ORCID profile data.

        Args:
            orcid: ORCID identifier (with or without dashes)

        Returns:
            Complete profile data dictionary

        Raises:
            ZenodoAPIError: If request fails

        """
        normalized_orcid = orcid.replace("-", "")
        logger.debug(f"Fetching ORCID profile for {orcid}")
        return await self.get(f"/{normalized_orcid}")

    async def get_employments(self, orcid: str) -> list[dict[str, Any]]:
        """Fetch employment affiliations from ORCID profile.

        Retrieves all employment records including organization information,
        dates, and department names.

        Args:
            orcid: ORCID identifier (with or without dashes)

        Returns:
            List of employment records with organization details

        Raises:
            ZenodoAPIError: If request fails

        """
        normalized_orcid = orcid.replace("-", "")
        logger.debug(f"Fetching employments for ORCID {orcid}")
        data = await self.get(f"/{normalized_orcid}/employments")
        result = data.get("employment-summary", [])
        logger.debug(f"Found {len(result)} employment records")
        return result

    async def get_educations(self, orcid: str) -> list[dict[str, Any]]:
        """Fetch education affiliations from ORCID profile.

        Retrieves all education records including organization information
        and dates.

        Args:
            orcid: ORCID identifier (with or without dashes)

        Returns:
            List of education records with organization details

        Raises:
            ZenodoAPIError: If request fails

        """
        normalized_orcid = orcid.replace("-", "")
        logger.debug(f"Fetching educations for ORCID {orcid}")
        data = await self.get(f"/{normalized_orcid}/educations")
        result = data.get("education-summary", [])
        logger.debug(f"Found {len(result)} education records")
        return result

    async def get(self, endpoint: str) -> dict[str, Any]:
        """Make GET request with optional caching.

        ORCID API requires Accept header for JSON-LD format.
        Handles HTTP status codes and converts them to appropriate exceptions.

        Args:
            endpoint: API endpoint path (e.g., "/0000000000000000/employments")

        Returns:
            Parsed JSON response as dictionary

        Raises:
            ZenodoAPIError: If session not initialized or HTTP error occurs
            RateLimitError: If rate limited (429)

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
            async with self._session.get(
                url, headers={"Accept": "application/json"}
            ) as resp:
                if resp.status == 404:
                    logger.debug(f"ORCID record not found: {url}")
                    return {}

                if resp.status == 429:
                    retry_after = resp.headers.get("Retry-After")
                    retry_after_float = float(retry_after) if retry_after else None
                    logger.warning(f"ORCID rate limit exceeded for {url}")
                    raise RateLimitError(
                        f"ORCID rate limit exceeded for {url}",
                        retry_after=retry_after_float,
                    )

                if resp.status >= 400:
                    error_text = await resp.text()
                    logger.error(
                        f"ORCID API error {resp.status} for {url}: {error_text}"
                    )
                    raise ZenodoAPIError(
                        f"ORCID API error {resp.status} for {url}: {error_text}"
                    )

                data = await resp.json()
                logger.debug(f"Successfully fetched {url}")

                if self._cache is not None:
                    self._cache[cache_key] = data

                return data

        except aiohttp.ClientError as e:
            logger.error(f"ORCID HTTP request failed for {url}: {e}")
            raise ZenodoAPIError(f"ORCID HTTP request failed for {url}: {e}") from e

    async def __aenter__(self) -> "OrcidApiClient":
        """Initialize aiohttp session on context manager entry."""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self._session = aiohttp.ClientSession(timeout=timeout)
        logger.debug("OrcidApiClient session initialized")
        return self

    async def __aexit__(
        self, exc_type: type, exc_val: Exception, exc_tb: object
    ) -> None:
        """Close aiohttp session on context manager exit."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("OrcidApiClient session closed")


__all__ = ["OrcidApiClient"]
