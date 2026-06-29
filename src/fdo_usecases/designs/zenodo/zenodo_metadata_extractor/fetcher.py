"""Main fetcher class for Zenodo datasets.

This module provides the high-level interface for fetching Zenodo dataset metadata
and transforming it into structured Pydantic models. It orchestrates the entire
data retrieval and model building process.


## Key Responsibilities

- **DOI Resolution** – Convert DOIs to Zenodo record IDs
- **Version Discovery** – Fetch all published versions of a dataset
- **Model Construction** – Build interconnected Pydantic objects
- **Relationship Management** – Establish previous/next navigation links
- **File Tracking** – Deduplicate files by checksum across versions
- **Version Chains** – Link same-named files with different content


## Architecture

The fetcher follows a multi-pass approach:

```{.mermaid}
flowchart LR
    A["1. Fetch Record<br/>+ Versions"] --> B["2. Build<br/>Version Objects"]
    B --> C["3. Deduplicate<br/>Files by Checksum"]
    C --> D["4. Link<br/>Versions"]
    D --> E["5. Build File<br/>Version Chains"]
    E --> F["6. Assemble<br/>Final Dataset"]
```


## Workflow Steps

1. **Fetch latest record and all historical versions** via REST API
2. **Build DatasetVersion objects** for each version with metadata
3. **Deduplicate files by checksum** into unified global registry
4. **Link consecutive dataset versions** bidirectionally (previous ↔ next)
5. **Build file version chains** based on filename matching
6. **Assemble final Dataset object** with all relationships established
"""

import re
from datetime import date
from typing import Any

from .api_client import ZenodoAPIClient
from .exceptions import DOINotFoundError
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

    Attributes:
        api_client: Async HTTP client for Zenodo API communication

    """

    def __init__(self, cache_enabled: bool = True, timeout: float = 30.0):
        """Initialize the dataset fetcher.

        Args:
            cache_enabled: Enable response caching (default: True)
                          Recommended to avoid redundant API calls
            timeout: Request timeout in seconds (default: 30.0)

        """
        self.api_client = ZenodoAPIClient(cache_enabled=cache_enabled, timeout=timeout)

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
        7. Return complete Dataset object

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
            # Step 1: Resolve DOI to record data
            record_data = await self._resolve_doi(doi)
            recid = record_data["id"]
            concept_recid = record_data.get("conceptrecid", recid)

            # Step 2: Fetch all versions of this record
            versions_data = await self._fetch_all_versions(recid)

            # Fallback: if no separate versions found, use current record
            if not versions_data:
                versions_data = [record_data]

            # Step 3: Build complete model with relationships
            dataset = self._build_dataset_model(
                record_data, versions_data, concept_recid
            )

            return dataset

    async def _resolve_doi(self, doi: str) -> dict[str, Any]:
        """Resolve DOI to Zenodo record data.

        Attempts two strategies:
        1. Direct lookup: Extract record ID from DOI pattern (e.g., zenodo.20132712)
        2. Search fallback: Query API by DOI if direct lookup fails

        This two-tier approach optimizes for common case while handling edge cases.

        Args:
            doi: DOI string to resolve

        Returns:
            Record data dictionary from Zenodo API

        Raises:
            DOINotFoundError: If DOI doesn't match any record

        """
        # Strategy 1: Try direct record ID extraction
        # Pattern: "10.5281/zenodo.123456" → record ID 123456
        match = re.search(r"zenodo\.(\d+)", doi)
        if match:
            recid = int(match.group(1))
            try:
                return await self.api_client.get(f"/records/{recid}")
            except DOINotFoundError:
                # Direct lookup failed, fall through to search
                pass

        # Strategy 2: Search by DOI
        search_result = await self.api_client.get(f"/records?doi={doi}")
        hits = search_result.get("hits", {})
        if hits.get("total", 0) == 0:
            raise DOINotFoundError(f"DOI not found: {doi}")
        return hits["hits"][0]

    async def _fetch_all_versions(self, recid: int) -> list[dict[str, Any]]:
        """Fetch all versions of a record from Zenodo API.

        Uses the /records/{recid}/versions endpoint which returns all published
        versions of a dataset, ordered chronologically.

        Note: Some older records may not have a versions endpoint, in which case
        we return empty list and handle gracefully in build step.

        Args:
            recid: Zenodo record ID

        Returns:
            List of version data dictionaries, empty list if none found

        """
        try:
            versions_data = await self.api_client.get(f"/records/{recid}/versions")
            return versions_data.get("hits", {}).get("hits", [])
        except DOINotFoundError:
            # Versions endpoint doesn't exist for this record
            return []

    def _build_dataset_model(
        self,
        latest_record: dict[str, Any],
        all_versions: list[dict[str, Any]],
        concept_recid: int,
    ) -> Dataset:
        """Build complete Dataset object graph from API responses.

        This is the core assembly method that orchestrates the model building process.
        It processes all versions, deduplicates files, establishes relationships,
        and returns a fully-connected Dataset object.

        Algorithm (Multi-Pass Approach):

        Pass 1: Build Version Objects
        - Iterate through all versions chronologically
        - Create DatasetVersion for each with its files
        - Track files in global registry by checksum

        Pass 2: Link Dataset Versions
        - Establish bidirectional previous/next links
        - Enables navigation: v1.0 ↔ v1.1 ↔ v2.0 ↔ v2.1

        Pass 3: Build File Version Chains
        - Group files by filename across versions
        - Link same-named files with different checksums
        - Example: data_v1.csv → data_v2.csv (different content)

        Pass 4: Assemble Final Dataset
        - Extract relationship metadata
        - Use latest version for title/description
        - Return complete Dataset object

        Args:
            latest_record: Most recent record data (used for concept DOI, etc.)
            all_versions: List of all version data dictionaries
            concept_recid: Master record ID grouping all versions

        Returns:
            Complete Dataset object with all relationships established

        """
        # Extract concept-level identifiers
        metadata = latest_record.get("metadata", {})
        concept_doi = latest_record.get("conceptdoi", metadata.get("doi", ""))

        # Containers for building the model
        version_objects: list[DatasetVersion] = []
        all_files_registry: dict[str, ZenodoFile] = {}

        # Sort versions chronologically by version label
        # This ensures correct ordering for previous/next links
        sorted_versions = sorted(
            all_versions,
            key=lambda v: v.get("metadata", {}).get("version", "0"),
        )

        # PASS 1: Build version objects and collect files
        for _idx, version_data in enumerate(sorted_versions):
            # Create DatasetVersion with its files
            version_obj = self._build_version_model(version_data, concept_doi)

            # Register files in global deduplicated registry
            for checksum, file_obj in version_obj.files.items():
                if checksum not in all_files_registry:
                    # First appearance - add to registry
                    all_files_registry[checksum] = file_obj
                else:
                    # File already exists - track this version too
                    existing_file = all_files_registry[checksum]
                    if (
                        version_data["metadata"]["doi"]
                        not in existing_file.present_in_versions
                    ):
                        existing_file.present_in_versions.append(
                            version_data["metadata"]["doi"]
                        )

            version_objects.append(version_obj)

        # PASS 2: Link consecutive dataset versions bidirectionally
        for i, version in enumerate(version_objects):
            if i > 0:
                # Link backward
                version.previous_version = version_objects[i - 1]
            if i < len(version_objects) - 1:
                # Link forward
                version.next_version = version_objects[i + 1]

        # PASS 3: Build file version chains (same name, different checksum)
        self._build_file_version_chains(all_files_registry, version_objects)

        # Get latest version for top-level metadata
        latest_version = version_objects[-1]

        # Parse relationship metadata from latest version
        related_ids = [
            self._parse_related_identifier(rel)
            for rel in metadata.get("related_identifiers", [])
        ]

        # Parse funding information
        grants = [self._parse_grant(grant) for grant in metadata.get("grants", [])]

        # Parse community memberships
        communities = [
            self._parse_community(comm) for comm in metadata.get("communities", [])
        ]

        # PASS 4: Assemble final Dataset object
        dataset = Dataset(
            concept_doi=concept_doi,
            concept_recid=concept_recid,
            title=latest_version.title,
            description=latest_version.description,
            versions={v.doi: v for v in version_objects},
            latest_version_doi=latest_version.doi,
            all_files=all_files_registry,
            related_identifiers=related_ids,
            grants=grants,
            communities=communities,
        )

        return dataset

    def _build_version_model(
        self, version_data: dict[str, Any], concept_doi: str
    ) -> DatasetVersion:
        """Build DatasetVersion from a single API response.

        Transforms raw API data into a structured DatasetVersion object with
        validated fields and proper type conversions.

        Processing Steps:
        1. Extract metadata from response
        2. Parse creators with ORCID validation
        3. Convert publication date to ISO format
        4. Transform files list into checksum-keyed dict
        5. Normalize checksum format (ensure "md5:" prefix)
        6. Create ZenodoFile objects with version tracking

        Args:
            version_data: Raw API response for one version
            concept_doi: Parent concept DOI for this version

        Returns:
            DatasetVersion object with all fields populated

        Note:
            Files are created with present_in_versions initialized to current version.
            The global registry will update this if file appears in multiple versions.

        """
        metadata = version_data.get("metadata", {})

        # Parse creators list with optional fields
        creators = [
            Creator(
                name=c.get("name", ""),
                affiliation=c.get("affiliation"),
                orcid=c.get("orcid"),
            )
            for c in metadata.get("creators", [])
        ]

        # Parse publication date with fallback
        pub_date_str = metadata.get("publication_date", "")
        try:
            pub_date = date.fromisoformat(pub_date_str)
        except ValueError:
            # Fallback for invalid dates - use today's date
            pub_date = date.today()

        # Parse license information if present
        license_info = None
        license_data = metadata.get("license")
        if license_data:
            license_info = LicenseInfo(
                id=license_data.get("id", ""),
                name=license_data.get("title"),
                url=license_data.get("url"),
            )

        # Build files dictionary keyed by checksum for O(1) lookup
        files_dict = {}
        for file_data in version_data.get("files", []):
            # Normalize checksum format - ensure "md5:" prefix
            checksum = file_data.get("checksum", "")
            if not checksum.startswith("md5:"):
                checksum = f"md5:{checksum}"

            # Create ZenodoFile with version origin tracking
            file_obj = ZenodoFile(
                checksum=checksum,
                filename=file_data.get("key", ""),
                size=file_data.get("size", 0),
                mimetype=file_data.get("mimetype"),
                first_dataset_version=version_data["metadata"]["doi"],
                first_dataset_recid=version_data["id"],
                present_in_versions=[version_data["metadata"]["doi"]],
                download_url=file_data.get("links", {}).get(
                    "self",
                    f"https://zenodo.org/api/records/{version_data['id']}/files/{file_data.get('key', '')}",
                ),
            )
            files_dict[checksum] = file_obj

        # Extract version label with default
        version_label = metadata.get("version", "1.0")

        # Construct and return DatasetVersion
        version = DatasetVersion(
            doi=version_data["metadata"]["doi"],
            concept_doi=concept_doi,
            recid=version_data["id"],
            version_label=version_label,
            title=metadata.get("title", ""),
            description=metadata.get("description"),
            creators=creators,
            publication_date=pub_date,
            license=license_info,
            keywords=metadata.get("keywords", []),
            files=files_dict,
            metadata_raw=version_data,  # Preserve raw data for debugging
        )

        return version

    def _build_file_version_chains(
        self,
        all_files: dict[str, ZenodoFile],
        version_sequence: list[DatasetVersion],
    ) -> None:
        """Link files with same name but different checksums across versions.

        This method establishes version chains for files that share the same filename
        but have different content (different checksums) across dataset versions.

        Motivation:
        When a file is updated between versions (e.g., "data.csv" changes content),
        it gets a new checksum. We want to track this evolution and enable navigation
        between versions of the same logical file.

        Algorithm:

        Step 1: Build Filename History
        - Group all files by filename
        - Track (version_index, checksum) pairs for each filename
        - Example: {"data.csv": [(0, "md5:aaa"), (1, "md5:bbb")] }

        Step 2: Create Bidirectional Links
        - For filenames appearing with multiple checksums
        - Sort by version index (chronological order)
        - Link consecutive versions: File_A ↔ File_B ↔ File_C

        Result:
        Files can be navigated like: v1 → v2 → v3 via next_version pointers
        And backward: v3 → v2 → v1 via previous_version pointers

        Args:
            all_files: Global registry of unique files (modified in-place)
            version_sequence: Chronologically ordered DatasetVersion list

        Example Chain:
            data.csv (v1.0, checksum A)
                ↓ next_version
            data.csv (v2.0, checksum B)
                ↓ next_version
            data.csv (v2.1, checksum C)

            With backward links:
            data.csv (v2.1, checksum C)
                ↑ previous_version
            data.csv (v2.0, checksum B)

        """
        # Step 1: Build filename → [(version_index, checksum)] mapping
        filename_history: dict[str, list[tuple[int, str]]] = {}

        for version_idx, version in enumerate(version_sequence):
            for checksum, file_obj in version.files.items():
                if file_obj.filename not in filename_history:
                    filename_history[file_obj.filename] = []
                filename_history[file_obj.filename].append((version_idx, checksum))

        # Step 2: Create bidirectional links for each filename chain
        for occurrences in filename_history.values():
            # Skip files that only appear once (no versioning needed)
            if len(occurrences) <= 1:
                continue

            # Sort by version index to ensure chronological ordering
            sorted_occurrences = sorted(occurrences, key=lambda x: x[0])

            # Link consecutive versions
            for i in range(len(sorted_occurrences) - 1):
                _, checksum_current = sorted_occurrences[i]
                _, checksum_next = sorted_occurrences[i + 1]

                # Skip if checksums are identical (same file, no change)
                if checksum_current == checksum_next:
                    continue

                # Get file objects and establish bidirectional link
                file_current = all_files[checksum_current]
                file_next = all_files[checksum_next]

                file_current.next_version = file_next
                file_next.previous_version = file_current

    def _parse_related_identifier(self, rel_data: dict[str, Any]) -> RelatedIdentifier:
        """Parse related identifier from API response.

        Converts raw API data into validated RelatedIdentifier object.
        The validator ensures relation type is from DataCite vocabulary.

        Args:
            rel_data: Raw dictionary from API's related_identifiers field

        Returns:
            Validated RelatedIdentifier object

        Example Input:
            {
                "identifier": "10.5281/zenodo.123456",
                "relation": "isSupplementTo",
                "resource_type": "dataset",
                "scheme": "doi"
            }

        """
        return RelatedIdentifier(
            identifier=rel_data.get("identifier", ""),
            relation=rel_data.get("relation", ""),
            resource_type=rel_data.get("resource_type"),
            scheme=rel_data.get("scheme"),
        )

    def _parse_grant(self, grant_data: dict[str, Any]) -> GrantInfo:
        """Parse funding grant information from API response.

        Extracts grant details including funder information from nested structure.

        Args:
            grant_data: Raw dictionary from API's grants field

        Returns:
            GrantInfo object with parsed fields

        Example Input:
            {
                "code": "460247524",
                "title": "NFDI-MatWerk",
                "funder": {"name": "Deutsche Forschungsgemeinschaft"},
                "internal_id": "..."
            }

        """
        funder = grant_data.get("funder", {})
        return GrantInfo(
            code=grant_data.get("code", ""),
            title=grant_data.get("title"),
            funder_name=funder.get("name") if funder else None,
            internal_id=grant_data.get("internal_id"),
        )

    def _parse_community(self, comm_data: dict[str, Any]) -> CommunityInfo:
        """Parse Zenodo community information from API response.

        Communities are curated collections on Zenodo that datasets can belong to.

        Args:
            comm_data: Raw dictionary from API's communities field

        Returns:
            CommunityInfo object with parsed fields

        Example Input:
            {"id": "bam", "slug": "bam-community", "name": "BAM Research"}

        """
        return CommunityInfo(
            id=comm_data.get("id", ""),
            slug=comm_data.get("slug"),
            name=comm_data.get("name"),
        )
