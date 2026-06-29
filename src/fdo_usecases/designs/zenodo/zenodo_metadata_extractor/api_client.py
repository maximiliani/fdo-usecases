"""Async HTTP client for Zenodo API with in-memory caching.

This module provides a lightweight async HTTP client wrapper specifically designed
for interacting with the Zenodo REST API. It handles:
- Session management via async context manager
- Response caching to avoid redundant API calls
- Error handling and conversion to custom exceptions
- Rate limit detection with Retry-After header support
"""

from typing import Any

import aiohttp

from .exceptions import DOINotFoundError, RateLimitError, ZenodoAPIError


class ZenodoAPIClient:
    """Async HTTP client for Zenodo API with optional in-memory caching.

    This client manages the aiohttp session lifecycle and provides automatic
    caching of API responses. It should be used as an async context manager
    to ensure proper session cleanup.

    Design Decisions:
    - Cache keys are full URLs to avoid collisions
    - Cache is simple dict (not LRU) since typical usage fetches each DOI once
    - Session timeout applies to entire request lifecycle

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
        # Cache disabled if explicitly set to False
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
        # Cache key includes full URL to prevent any collision
        cache_key = f"{self.base_url}{endpoint}"

        # Return cached response if available
        if self._cache is not None and cache_key in self._cache:
            return self._cache[cache_key]

        # Validate session is active
        if self._session is None:
            raise ZenodoAPIError(
                "Client session not initialized. Use async context manager."
            )

        url = f"{self.base_url}{endpoint}"

        try:
            async with self._session.get(url) as resp:
                # Handle specific HTTP status codes
                if resp.status == 404:
                    raise DOINotFoundError(f"Resource not found: {url}")

                if resp.status == 429:
                    # Extract Retry-After header if present
                    retry_after = resp.headers.get("Retry-After")
                    retry_after_float = float(retry_after) if retry_after else None
                    raise RateLimitError(
                        f"Rate limit exceeded for {url}", retry_after=retry_after_float
                    )

                # Generic error for other 4xx/5xx responses
                if resp.status >= 400:
                    error_text = await resp.text()
                    raise ZenodoAPIError(
                        f"API error {resp.status} for {url}: {error_text}"
                    )

                # Parse successful response as JSON
                data = await resp.json()

                # Cache the response if caching is enabled
                if self._cache is not None:
                    self._cache[cache_key] = data

                return data

        except aiohttp.ClientError as e:
            # Network errors, connection failures, etc.
            raise ZenodoAPIError(f"HTTP request failed for {url}: {e}") from e

    async def __aenter__(self) -> "ZenodoAPIClient":
        """Initialize aiohttp session on context manager entry.

        Creates a new ClientSession with configured timeout. The session will
        be reused for all requests within the context manager block.

        Returns:
            Self for use in async with statement

        """
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self._session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(
        self, exc_type: type, exc_val: Exception, exc_tb: object
    ) -> None:
        """Close aiohttp session on context manager exit.

        Ensures the session is properly closed even if an exception occurred
        during the context. This prevents resource leaks and connection pooling issues.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised

        """
        if self._session:
            await self._session.close()
            self._session = None
