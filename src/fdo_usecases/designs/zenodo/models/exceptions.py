# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""Custom exceptions for Zenodo metadata extractor.

This module defines a hierarchy of exceptions for handling various error conditions
that may occur during API communication and data processing.


## Exception Hierarchy

```{.mermaid}
classDiagram
    class ZenodoAPIError {
        <<base>>
    }
    class DOINotFoundError {
        HTTP 404
    }
    class RateLimitError {
        HTTP 429
        +float retry_after
    }
    class ValidationError {
        data validation
    }

    ZenodoAPIError <|-- DOINotFoundError
    ZenodoAPIError <|-- RateLimitError
    ZenodoAPIError <|-- ValidationError
```


## Usage Example

```python
from zenodo_metadata_extractor import (
    ZenodoDatasetFetcher,
    ZenodoAPIError,
    DOINotFoundError,
    RateLimitError,
)

fetcher = ZenodoDatasetFetcher()

try:
    dataset = await fetcher.fetch_by_doi("10.5281/zenodo.123456")
except DOINotFoundError as e:
    print(f"DOI not found: {e}")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except ZenodoAPIError as e:
    print(f"API error: {e}")
```
"""


class ZenodoAPIError(Exception):
    """Base exception for all Zenodo API-related errors.

    This is the parent class for all custom exceptions in this package.
    Catching ZenodoAPIError will catch any API-related exception.

    Use Cases:
    - HTTP request failures
    - Unexpected API responses
    - Network errors
    """

    pass


class DOINotFoundError(ZenodoAPIError):
    """Exception raised when a DOI doesn't resolve to any record.

    This occurs when:
    - The DOI doesn't exist in Zenodo
    - The record ID extracted from DOI is invalid
    - The record has been removed or is private

    HTTP Status: Typically corresponds to 404 Not Found

    Example:
        ```python
        try:
            await fetcher.fetch_by_doi("10.5281/zenodo.999999999")
        except DOINotFoundError:
            print("This DOI does not exist")
        ```

    """

    pass


class RateLimitError(ZenodoAPIError):
    """Exception raised when API rate limit is exceeded (HTTP 429).

    Zenodo imposes rate limits on API requests. This exception includes
    an optional retry_after parameter if the server provides it in the
    Retry-After header.

    Attributes:
        retry_after: Suggested wait time in seconds before retrying (optional)

    Handling Strategy:
    - Implement exponential backoff
    - Respect Retry-After header if present
    - Consider caching to reduce API calls

    Example:
        ```python
        try:
            dataset = await fetcher.fetch_by_doi(doi)
        except RateLimitError as e:
            if e.retry_after:
                await asyncio.sleep(e.retry_after)
                # Retry...
        ```

    """

    def __init__(self, message: str, retry_after: float | None = None):
        """Initialize rate limit error.

        Args:
            message: Error message describing the rate limit issue
            retry_after: Seconds to wait before retrying (from Retry-After header)

        """
        super().__init__(message)
        self.retry_after = retry_after


class ValidationError(ZenodoAPIError):
    """Exception raised when API response data fails validation.

    This can occur when:
    - Required fields are missing from API response
    - Field values don't match expected format
    - Data type mismatches

    Note: Pydantic ValidationError is caught and wrapped in this exception
    for consistent error handling across the codebase.

    Example:
        ```python
        try:
            dataset = await fetcher.fetch_by_doi(doi)
        except ValidationError as e:
            print(f"Invalid data structure: {e}")
        ```

    """

    pass
