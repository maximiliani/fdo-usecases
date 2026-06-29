"""Zenodo Metadata Extractor – fetch and parse Zenodo dataset metadata.

This package provides a high-level Python interface to the Zenodo REST API,
transforming raw API responses into structured, validated Pydantic models.
It handles version tracking, file deduplication, and relationship management
automatically.


## Key Features

- **Automatic version discovery and linking** – Navigate between dataset versions using previous/next pointers
- **File deduplication by MD5 checksum** – Each unique file appears once across all versions
- **File version chains** – Track evolution of files with same name but different content
- **Comprehensive validation** – DOIs, ORCIDs, checksums, and DataCite relation types
- **Async HTTP client with caching** – Efficient API access with optional response caching
- **Public dataset support** – Works with all publicly accessible Zenodo datasets


## Architecture

```{.mermaid}
flowchart TD
    User["User Code"] --> Fetcher["ZenodoDatasetFetcher"]
    Fetcher --> Client["ZenodoAPIClient<br/>(HTTP + Caching)"]
    Client --> ZenodoAPI["Zenodo REST API"]

    Fetcher --> Models["Pydantic Models"]

    Models --> Dataset["Dataset<br/>(Top-level container)"]
    Models --> Version["DatasetVersion<br/>(Single version)"]
    Models --> File["ZenodoFile<br/>(Unique by checksum)"]
    Models --> Support["Supporting Models<br/>Creator, License, etc."]

    Dataset --> Version
    Version --> File
```


## Example Usage

```python
import asyncio
from zenodo_metadata_extractor import ZenodoDatasetFetcher

async def main():
    # Initialize fetcher with caching enabled
    fetcher = ZenodoDatasetFetcher(cache_enabled=True)

    # Fetch complete dataset by DOI
    dataset = await fetcher.fetch_by_doi("10.5281/zenodo.20132712")

    # Access latest version
    latest = dataset.versions[dataset.latest_version_doi]
    print(f"Latest version: {latest.version_label}")
    print(f"Files in latest: {len(latest.files)}")

    # Navigate version history bidirectionally
    if latest.previous_version:
        prev = latest.previous_version
        print(f"Previous: v{prev.version_label}")

    # Find file by checksum
    file_obj = dataset.all_files.get("md5:abc123...")
    if file_obj:
        print(f"File: {file_obj.filename}")
        print(f"Size: {file_obj.size} bytes")
        print(f"Appears in: {file_obj.present_in_versions}")

        # Track file evolution across versions
        if file_obj.next_version:
            newer = file_obj.next_version
            print(f"Newer version exists:")
            print(f"  Checksum: {newer.checksum}")
            print(f"  First in: {newer.first_dataset_version}")

asyncio.run(main())
```


## Package Exports

### Main Classes

- `ZenodoDatasetFetcher` – Primary interface for fetching datasets
- `ZenodoAPIClient` – Low-level HTTP client (for advanced use)

### Core Data Models

- `Dataset` – Complete dataset spanning all versions
- `DatasetVersion` – Single published version
- `ZenodoFile` – Unique file identified by checksum

### Supporting Models

- `Creator` – Author/contributor information
- `LicenseInfo` – License details
- `RelatedIdentifier` – Related work references
- `GrantInfo` – Funding information
- `CommunityInfo` – Zenodo community membership

### Exceptions

- `ZenodoAPIError` – Base exception for API errors
- `DOINotFoundError` – DOI doesn't exist
- `RateLimitError` – API rate limit exceeded
- `ValidationError` – Data validation failure


## See Also

- [Zenodo REST API Documentation](https://developers.zenodo.org/)
- Example usage script: `zenodo_metadata_extractor/example_usage.py`
- [Pydantic Documentation](https://docs.pydantic.dev/) – Model validation framework
"""

# Import API client for internal use and advanced users
from .api_client import ZenodoAPIClient

# Import exceptions for error handling
from .exceptions import (
    DOINotFoundError,
    RateLimitError,
    ValidationError,
    ZenodoAPIError,
)

# Import main fetcher class - primary user-facing API
from .fetcher import ZenodoDatasetFetcher

# Import all Pydantic models for type annotations and inspection
from .models import (
    CommunityInfo,
    Creator,
    Dataset,
    DatasetVersion,
    GrantInfo,
    LicenseInfo,
    RelatedIdentifier,
    ZenodoFile,
)

__all__ = [
    # Main fetcher
    "ZenodoDatasetFetcher",
    # API client (for advanced use)
    "ZenodoAPIClient",
    # Core models
    "Dataset",
    "DatasetVersion",
    "ZenodoFile",
    # Supporting models
    "Creator",
    "LicenseInfo",
    "RelatedIdentifier",
    "GrantInfo",
    "CommunityInfo",
    # Exceptions
    "ZenodoAPIError",
    "DOINotFoundError",
    "RateLimitError",
    "ValidationError",
]

__version__ = "0.0.1"
