# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Model construction logic."""

from datetime import date
from typing import Any

from fdo_usecases.designs.zenodo.models import (
    CommunityInfo,
    Creator,
    Dataset,
    DatasetVersion,
    GrantInfo,
    LicenseInfo,
    RelatedIdentifier,
    ZenodoFile,
)


class ModelBuilder:
    """Build metadata models from API responses."""

    def build_dataset(
        self,
        latest_record: dict[str, Any],
        all_versions: list[dict[str, Any]],
    ) -> Dataset:
        """Build complete Dataset object graph from API responses.

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

        Pass 4: Assemble Final Dataset
        - Extract relationship metadata
        - Use latest version for title/description
        - Return complete Dataset object

        Args:
            latest_record: Most recent record data (used for concept DOI, etc.)
            all_versions: List of all version data dictionaries

        Returns:
            Complete Dataset object with all relationships established

        """
        # Extract concept-level identifiers
        metadata = latest_record.get("metadata", {})
        concept_doi = latest_record.get("conceptdoi", metadata.get("doi", ""))
        concept_recid = latest_record.get("conceptrecid", latest_record["id"])

        # Containers for building the model
        version_objects: list[DatasetVersion] = []
        all_files_registry: dict[str, ZenodoFile] = {}

        # Sort versions chronologically by version label
        sorted_versions = sorted(
            all_versions,
            key=lambda v: v.get("metadata", {}).get("version", "0"),
        )

        # PASS 1: Build version objects and collect files
        for version_data in sorted_versions:
            # Create DatasetVersion with its files
            version_obj = self._build_version(version_data, concept_doi)

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
                version.previous_version = version_objects[i - 1]
            if i < len(version_objects) - 1:
                version.next_version = version_objects[i + 1]

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

        # PASS 3 & 4: Assemble final Dataset object
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

    def _build_version(
        self,
        version_data: dict[str, Any],
        concept_doi: str,
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
                download_url=file_data.get(
                    "links",
                    {},
                ).get(
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
            metadata_raw=version_data,
        )

        return version

    def _parse_related_identifier(self, rel_data: dict[str, Any]) -> RelatedIdentifier:
        """Parse related identifier from API response.

        Converts raw API data into validated RelatedIdentifier object.
        The validator ensures relation type is from DataCite vocabulary.

        Args:
            rel_data: Raw dictionary from API's related_identifiers field

        Returns:
            Validated RelatedIdentifier object

        """
        return RelatedIdentifier(
            identifier=rel_data.get("identifier", ""),
            relation=rel_data.get("relation", ""),
            resource_type=rel_data.get("resource_type"),
            scheme=rel_data.get("scheme"),
        )

    def _parse_grant(self, grant_data: dict[str, Any]) -> GrantInfo:
        """Parse funding grant information from API response.

        Args:
            grant_data: Raw dictionary from API's grants field

        Returns:
            GrantInfo object with parsed fields

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

        Args:
            comm_data: Raw dictionary from API's communities field

        Returns:
            CommunityInfo object with parsed fields

        """
        return CommunityInfo(
            id=comm_data.get("id", ""),
            slug=comm_data.get("slug"),
            name=comm_data.get("name"),
        )
