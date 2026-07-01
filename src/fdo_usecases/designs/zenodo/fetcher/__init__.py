# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""Zenodo dataset fetcher - main entry point."""

from fdo_usecases.designs.zenodo.api_clients import (
    OrcidApiClient,
    ZenodoAPIClient,
    ZenodoExportApiClient,
)
from fdo_usecases.designs.zenodo.enrichment import ROREnricher
from fdo_usecases.designs.zenodo.fetcher.doi_resolver import DOIResolver
from fdo_usecases.designs.zenodo.fetcher.file_chain_builder import FileChainBuilder
from fdo_usecases.designs.zenodo.fetcher.model_builder import ModelBuilder
from fdo_usecases.designs.zenodo.fetcher.version_fetcher import VersionFetcher
from fdo_usecases.designs.zenodo.models import Dataset


class ZenodoDatasetFetcher:
    """High-level fetcher for Zenodo dataset metadata.

    This is the main entry point for users. It handles the complete workflow
    of fetching a dataset by DOI and returning a fully-populated Dataset object
    with all versions, files, and relationships properly linked.

    The fetcher uses an async HTTP client with optional caching to efficiently
    retrieve data from the Zenodo REST API. All public data is accessible without
    authentication.

    Design Principles:
    - Single File object per unique checksum across all versions
    - Bidirectional navigation between consecutive versions
    - File version chains track same filename with different checksums
    - Graceful handling of missing versions or records
    - Always enrich creators with ROR IDs (priority: Zenodo export > ORCID)

    Example:
        ```python
        fetcher = ZenodoDatasetFetcher(cache_enabled=True)
        dataset = await fetcher.fetch_by_doi("10.5281/zenodo.20132712")

        # Access latest version
        latest = dataset.versions[dataset.latest_version_doi]

        # Navigate to previous version
        if latest.previous_version:
            prev = latest.previous_version

        # Find file and track across versions
        file = dataset.all_files.get("md5:abc123...")
        if file.next_version:
            print(f"Newer version exists: {file.next_version.checksum}")
        ```

    """

    def __init__(self, cache_enabled: bool = True, timeout: float = 30.0):
        """Initialize the dataset fetcher.

        Args:
            cache_enabled: Enable response caching (default: True)
                          Recommended to avoid redundant API calls
            timeout: Request timeout in seconds (default: 30.0)

        """
        self.api_client = ZenodoAPIClient(cache_enabled=cache_enabled, timeout=timeout)
        self.export_client = ZenodoExportApiClient(
            cache_enabled=cache_enabled, timeout=timeout
        )
        self.orcid_client = OrcidApiClient(cache_enabled=cache_enabled, timeout=timeout)

        # Delegate components
        self.doi_resolver = DOIResolver(self.api_client)
        self.version_fetcher = VersionFetcher(self.api_client)
        self.model_builder = ModelBuilder()
        self.file_chain_builder = FileChainBuilder()
        self.ror_enricher = ROREnricher(self.export_client, self.orcid_client)

    async def fetch_by_doi(self, doi: str) -> Dataset:
        """Fetch complete dataset by DOI.

        This is the main entry point. It retrieves the specified dataset record,
        fetches all its versions, and builds a complete object graph with proper
        relationships between versions and files.

        The method handles both version-specific DOIs (e.g., 10.5281/zenodo.20132712)
        and concept DOIs (e.g., 10.5281/zenodo.13937986), always returning all versions.

        Workflow:
        1. Resolve DOI to record ID (direct lookup or search)
        2. Fetch all versions via /records/{id}/versions endpoint
        3. Build DatasetVersion objects for each version
        4. Deduplicate files by checksum into unified registry
        5. Establish bidirectional version links
        6. Build file version chains
        7. Enrich creators with ROR IDs (always runs)
        8. Return complete Dataset object

        Args:
            doi: DOI of the dataset (version-specific or concept DOI)
                 Examples: "10.5281/zenodo.20132712" or "10.5281/zenodo.13937986"

        Returns:
            Dataset object containing all versions, files, and relationships

        Raises:
            DOINotFoundError: If DOI doesn't resolve to any record
            ZenodoAPIError: If API request fails

        """
        async with self.api_client:
            # Step 1: Resolve DOI
            record_data = await self.doi_resolver.resolve(doi)

            # Step 2: Fetch all versions
            versions_data = await self.version_fetcher.fetch_all(record_data["id"])

            # Fallback: if no separate versions found, use current record
            if not versions_data:
                versions_data = [record_data]

            # Step 3: Build model
            dataset = self.model_builder.build_dataset(record_data, versions_data)

            # Step 4: Build file version chains
            version_sequence = sorted(
                list(dataset.versions.values()),
                key=lambda v: v.version_label,
            )
            self.file_chain_builder.build_chains(dataset.all_files, version_sequence)

            # Step 5: Enrich creators with ROR IDs (Option A: always runs)
            await self.ror_enricher.enrich(record_data, dataset)

            return dataset


__all__ = ["ZenodoDatasetFetcher"]
