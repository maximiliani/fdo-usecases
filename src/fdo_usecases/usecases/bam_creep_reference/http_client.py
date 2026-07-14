# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Async HTTP client with caching and retry logic.

This module provides a robust HTTP client for fetching LIS files from Zenodo
with the following features:

- File-based caching to avoid repeated downloads (7 day TTL)
- Exponential backoff on rate limiting (HTTP 429)
- Configurable retry attempts
- Graceful error handling with logging
- Async context manager support

Cache Structure:
    .cache/
        ├── https%3A%2F%2Fzenodo.org%2Fapi%2Frecords%2F12345
        └── ...

Files are named by URL-encoded URL path to ensure uniqueness and filesystem safety.

Example:
    >>> async with HTTPClient() as client:
    ...     client._file_urls["checksum123"] = "https://example.com/file.lis"
    ...     content = await client._fetch_file_content("checksum123")
    ...     print(f"Fetched {len(content)} bytes")

"""

import asyncio
import logging
from typing import Optional

import aiohttp

from fdo_usecases.utils.http_cache import get_cache as get_file_cache

logger = logging.getLogger(__name__)


class HTTPClient:
    """Fetch LIS files from Zenodo with caching and retry logic.

    This class handles all HTTP communication for downloading LIS file content
    from Zenodo. It implements intelligent caching to minimize API calls and
    respects rate limits with exponential backoff.

    Attributes:
        _session: aiohttp ClientSession for async HTTP requests
        _file_urls: Mapping of checksums to download URLs
        DEFAULT_MAX_RETRIES: Default number of retry attempts (3)
        DEFAULT_INITIAL_DELAY: Initial delay before first retry in seconds (1.0)
        CACHE_TTL_SECONDS: Cache time-to-live in seconds (604800 = 7 days)

    Example:
        >>> async with HTTPClient() as client:
        ...     content = await client._fetch_file_content("checksum123")
        ...     if content:
        ...         print("Successfully fetched file")

    """

    DEFAULT_MAX_RETRIES = 3
    DEFAULT_INITIAL_DELAY = 1.0
    CACHE_TTL_SECONDS = 604800  # 7 days

    def __init__(self):
        """Initialize HTTP client."""
        self._session: Optional[aiohttp.ClientSession] = None
        self._file_urls: dict[str, str] = {}

    async def __aenter__(self):
        """Async context manager entry - create aiohttp session."""
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close aiohttp session."""
        if self._session:
            await self._session.close()

    def set_file_urls(self, urls: dict[str, str]) -> None:
        """Set mapping of checksums to download URLs.

        Args:
            urls: Dictionary mapping file checksums to download URLs

        """
        self._file_urls = urls

    async def _fetch_file_content(
        self,
        checksum: str,
        max_retries: int = DEFAULT_MAX_RETRIES,
        initial_delay: float = DEFAULT_INITIAL_DELAY,
    ) -> Optional[str]:
        """Fetch LIS file content from Zenodo with retry logic and caching.

        Downloads file content with intelligent retry behavior:
        - Checks file cache first (avoids repeated downloads)
        - Retries on network errors with exponential backoff
        - Handles HTTP 429 rate limits with Retry-After header respect
        - Caches successful downloads for future use

        Args:
            checksum: File checksum (used to lookup URL)
            max_retries: Maximum number of retry attempts (default: 3)
            initial_delay: Initial delay before first retry in seconds (default: 1.0)

        Returns:
            File content as string if successful, None if fetch fails after all retries

        Raises:
            No exceptions raised - all errors are logged and None returned

        Example:
            >>> client = HTTPClient()
            >>> client._file_urls["md5:abc123"] = "https://zenodo.org/api/records/123/files/file.lis"
            >>> content = await client._fetch_file_content("md5:abc123")
            >>> if content:
            ...     print(f"Downloaded {len(content)} bytes")

        """
        if not self._session:
            self._session = aiohttp.ClientSession()

        url = self._file_urls.get(checksum)
        if not url:
            logger.error(
                f"No URL found for checksum {checksum}. Available URLs: {len(self._file_urls)}"
            )
            return None

        # Check file cache first
        file_cache = get_file_cache(ttl_seconds=self.CACHE_TTL_SECONDS)
        cached_content = file_cache.get(url)
        if cached_content:
            logger.info(f"File cache hit for {checksum}")
            return cached_content

        logger.debug(f"Fetching {checksum} from {url[:80]}...")

        attempt = 0
        delay = initial_delay

        while attempt <= max_retries:
            try:
                async with self._session.get(url) as response:
                    logger.debug(
                        f"Attempt {attempt + 1}/{max_retries + 1}: Response status: {response.status}"
                    )

                    # Check status BEFORE reading content
                    if response.status == 429:
                        # Rate limited - retry with exponential backoff
                        retry_after = response.headers.get("Retry-After", str(delay))
                        try:
                            wait_time = float(retry_after)
                        except ValueError:
                            wait_time = delay

                        logger.warning(
                            f"Rate limited (HTTP 429). Waiting {wait_time}s before retry..."
                        )
                        await asyncio.sleep(wait_time)
                        attempt += 1
                        delay *= 2  # Exponential backoff

                    elif response.status == 200:
                        # Fetch as bytes first, then decode with error handling
                        content_bytes = await response.read()
                        try:
                            content = content_bytes.decode("utf-8", errors="replace")
                            logger.debug(f"Successfully fetched {len(content)} bytes")

                            # Cache the content
                            try:
                                file_cache.set(url, content)
                            except Exception as e:
                                logger.warning(f"Failed to cache {checksum}: {e}")

                            return content

                        except Exception as e:
                            logger.error(
                                f"Failed to decode content for {checksum}: {e}"
                            )
                            return None

                    else:
                        logger.error(f"Failed to fetch {url}: HTTP {response.status}")
                        return None

            except Exception as e:
                logger.error(f"Error fetching {url}: {type(e).__name__}: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    attempt += 1
                    delay *= 2
                else:
                    return None

        logger.error(f"Failed to fetch {checksum} after {max_retries + 1} attempts")
        return None


__all__ = ["HTTPClient"]
