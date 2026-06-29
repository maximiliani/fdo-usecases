# Zenodo Metadata Extractor

Fetch and parse Zenodo dataset metadata into structured Python objects using Pydantic models.

## Features

- **Version Tracking**: Automatically track all versions of a dataset and establish previous/next relationships
- **File Deduplication**: Files are uniquely identified by checksum (MD5 hash)
- **File Versioning**: Track files across versions when the same filename has different checksums
- **Async Support**: Built with aiohttp for efficient concurrent API requests
- **In-Memory Caching**: Avoid redundant API calls within a session
- **Validation**: Pydantic models validate DOIs, checksums, and other fields

## Installation

```bash
pip install -e .
```

Or with development dependencies:

```bash
pip install -e ".[dev]"
```

## Quick Start

```python
import asyncio
from zenodo_metadata_extractor import ZenodoDatasetFetcher


async def main():
    fetcher = ZenodoDatasetFetcher(cache_enabled=True)

    # Fetch dataset by DOI
    dataset = await fetcher.fetch_by_doi("10.5281/zenodo.20132712")

    # Access latest version
    latest = dataset.versions[dataset.latest_version_doi]
    print(f"Latest version: {latest.version_label}")
    print(f"Files: {len(latest.files)}")

    # Navigate version history
    if latest.previous_version:
        print(f"Previous version: {latest.previous_version.version_label}")

    # Find file by checksum
    target_checksum = "md5:28573899cc09a145ac2c69fc1370c0bf"
    file_obj = dataset.all_files.get(target_checksum)

    if file_obj:
        print(f"File: {file_obj.filename}")
        print(f"Size: {file_obj.size} bytes")
        print(f"First appeared: {file_obj.first_dataset_version}")
        print(f"Present in versions: {file_obj.present_in_versions}")

        # Track file across versions (same name, different checksum)
        if file_obj.next_version:
            print(f"Newer version exists:")
            print(f"  Checksum: {file_obj.next_version.checksum}")
            print(f"  First in: {file_obj.next_version.first_dataset_version}")


asyncio.run(main())
```

## Command Line Example

Run the included example script:

```bash
python zenodo_metadata_extractor/example_usage.py 10.5281/zenodo.20132712
```

Or use the default example dataset:

```bash
python zenodo_metadata_extractor/example_usage.py
```

## Data Model Overview

### `Dataset`

Represents a complete dataset spanning all versions:

- `concept_doi`: Main identifier grouping all versions
- `versions`: Dict mapping version DOI → `DatasetVersion`
- `all_files`: Unified file registry across all versions
- `related_identifiers`: Relationship metadata to other works

### `DatasetVersion`

Single published version of a dataset:

- `doi`: Version-specific DOI
- `version_label`: Human-readable version (e.g., "2.1")
- `files`: Files in this version (checksum → `ZenodoFile`)
- `previous_version` / `next_version`: Links to adjacent versions

### `ZenodoFile`

Unique file identified by checksum:

- `checksum`: MD5 hash (e.g., `"md5:abc123..."`)
- `filename`: Name from first appearance
- `first_dataset_version`: DOI where this checksum first appeared
- `present_in_versions`: All version DOIs containing this file
- `previous_version` / `next_version`: Links to same filename with different checksum

## API Reference

### `ZenodoDatasetFetcher`

#### `__init__(cache_enabled=True, timeout=30.0)`

Initialize the fetcher with optional caching and timeout settings.

#### `async fetch_by_doi(doi: str) -> Dataset`

Fetch complete dataset metadata by DOI.

**Parameters:**

- `doi`: DOI string (e.g., `"10.5281/zenodo.20132712"`)

**Returns:**

- `Dataset`: Complete dataset object with all versions and files

**Raises:**

- `DOINotFoundError`: DOI doesn't resolve to any record
- `RateLimitError`: API rate limit exceeded
- `ZenodoAPIError`: Other API errors

## Error Handling

```python
from zenodo_metadata_extractor import (
    ZenodoDatasetFetcher,
    ZenodoAPIError,
    DOINotFoundError,
    RateLimitError,
)

fetcher = ZenodoDatasetFetcher()

try:
    dataset = await fetcher.fetch_by_doi("10.5281/zenodo.20132712")
except DOINotFoundError as e:
    print(f"DOI not found: {e}")
except RateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after}s")
except ZenodoAPIError as e:
    print(f"API error: {e}")
```

## Limitations

- **Public data only**: Currently supports only publicly accessible datasets
- **No draft support**: Does not fetch unpublished drafts (requires authentication)
- **Relationship metadata only**: Related works are stored as metadata, not fetched recursively

## Development

### Running Tests

```bash
pytest tests/
```

### Type Checking

```bash
mypy zenodo_metadata_extractor/
```

### Linting

```bash
ruff check zenodo_metadata_extractor/
```

## License

MIT
