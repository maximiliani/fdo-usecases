# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Exchange models for Zenodo FDO creation.

This module contains Pydantic models used as data contracts between metadata
extraction and FDO record creation. These models provide a clean interface
that decouples FDO creation from the metadata source.

Models:
    DatasetFDOData - Complete data needed to create a Dataset FDO record
    CreatorData - Simplified creator data for FDO creation
    FileFDOData - Complete data needed to create a File FDO record
    PublicationFDOData - Complete data needed to create a Publication FDO record
"""

from datetime import date

from pydantic import BaseModel, Field, field_validator

from fdo_usecases.designs.zenodo.constants import VALID_RESOURCE_TYPES


class CreatorData(BaseModel):
    """Simplified creator data for FDO creation.

    Contains only the fields needed for FDO record creation (ORCID and ROR ID).
    Full creator information with names and affiliations is in the metadata models.

    Attributes:
        orcid: ORCID identifier as FULL URL (https://orcid.org/XXXX-XXXX-XXXX-XXXX)
        ror_id: ROR identifier URL for institutional affiliation (optional)

    """

    orcid: str | None = None
    ror_id: str | None = None


class DatasetFDOData(BaseModel):
    """Complete data needed to create a Dataset FDO record.

    This model represents all information required to create a Dataset FDO
    compliant with Base + Versionable profiles. It's transformed from the
    metadata models during the orchestration phase.

    Attributes:
        doi: Version-specific DOI (e.g., "10.5281/zenodo.20132712")
        title: Dataset title
        description: Abstract/description (HTML stripped, truncated to 500 words)
        publication_date: Publication date in ISO 8601 format
        version_label: Human-readable version string (e.g., "2.1")
        creators: List of creator data (ORCID URLs and ROR IDs)
        keywords: List of subject keywords/tags
        previous_version_doi: Previous version DOI or None if first version
        next_version_doi: Next version DOI or None if latest version
        latest_version_doi: Latest version DOI (for non-latest versions)
        files: List of file checksums in this dataset version
        landing_page_url: URL to the Zenodo landing page for this version
        preview_images: List of up to 10 preview image download URLs (PNG, JPEG, GIF, WebP)

    """

    doi: str
    title: str
    description: str | None = None
    publication_date: date
    version_label: str
    creators: list[CreatorData] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    previous_version_doi: str | None = None
    next_version_doi: str | None = None
    latest_version_doi: str | None = None
    files: list[str] = Field(default_factory=list)
    landing_page_url: str | None = None
    preview_images: list[str] = Field(default_factory=list)


class FileFDOData(BaseModel):
    """Complete data needed to create a File FDO record.

    This model represents all information required to create a File FDO
    compliant with Base + DataResource profiles. Each unique checksum gets
    one FileFDOData object, regardless of how many versions contain it.

    Attributes:
        checksum: MD5 hash in format "md5:<32 hex chars>"
        filename: Filename from first appearance
        mimetype: MIME type if available (optional)
        download_url: Direct download URL for this file
        license_url: SPDX license URL from parent dataset (optional)
        previous_version_checksum: Checksum of previous file version (optional)
        next_version_checksum: Checksum of next file version (optional)
        dataset_versions: List of dataset version DOIs containing this file
        landing_page_url: URL to the Zenodo landing page for the file's dataset

    """

    checksum: str
    filename: str
    mimetype: str | None = None
    download_url: str
    license_url: str | None = None
    previous_version_checksum: str | None = None
    next_version_checksum: str | None = None
    dataset_versions: list[str] = Field(default_factory=list)
    landing_page_url: str | None = None


class PublicationFDOData(BaseModel):
    """Complete data needed to create a Publication FDO record.

    This model represents all information required to create a Publication FDO
    compliant with Base + Publication profiles. For related identifiers, only
    minimal metadata is typically available from the Zenodo API.

    Attributes:
        identifier: Persistent identifier (DOI or other)
        resource_type: DataCite resourceTypeGeneral (controlled vocabulary)
        publisher: Publisher name (optional)
        publication_date: Publication date in ISO 8601 format (optional)
        title: Publication title (optional)
        description: Publication description (optional)
        creator_orcids: List of creator ORCID URLs (optional)
        referenced_by_datasets: List of dataset DOIs that reference this publication
        landing_page_url: URL to the publication landing page (DOI URL)

    """

    identifier: str
    resource_type: str | None = Field(
        default=None,
        description="DataCite resourceTypeGeneral from controlled vocabulary",
    )
    publisher: str | None = None
    publication_date: str | None = None
    title: str | None = None
    description: str | None = None
    creator_orcids: list[str] = Field(default_factory=list)
    referenced_by_datasets: list[str] = Field(default_factory=list)
    landing_page_url: str | None = None

    @field_validator("resource_type")
    @classmethod
    def validate_resource_type(cls, v: str | None) -> str | None:
        """Validate resource_type is in DataCite controlled vocabulary."""
        if v is None:
            return v
        if v not in VALID_RESOURCE_TYPES:
            raise ValueError(
                f"Invalid resource_type '{v}'. Must be one of: {sorted(VALID_RESOURCE_TYPES)}"
            )
        return v


__all__ = [
    "CreatorData",
    "DatasetFDOData",
    "FileFDOData",
    "PublicationFDOData",
]
