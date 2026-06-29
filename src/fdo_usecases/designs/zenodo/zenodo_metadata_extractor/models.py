"""Pydantic models for Zenodo metadata representation.

This module defines the core data structures used to represent Zenodo datasets,
versions, and files as validated Python objects. All models use Pydantic v2 for
runtime validation and type checking.


## Design Principles

1. **Checksum-based file identity** – Each unique MD5 hash creates one `ZenodoFile` object
2. **Bidirectional version linking** – Navigate dataset versions forward and backward
3. **File version chains** – Track same filename with different content across versions
4. **Strict validation** – DOIs, ORCIDs, and checksums validated against standard formats


## Model Hierarchy

```{.mermaid}
classDiagram
    class Dataset {
        +str concept_doi
        +dict versions
        +dict all_files
        +str latest_version_doi
    }

    class DatasetVersion {
        +str doi
        +str version_label
        +dict files
        +date publication_date
    }

    class ZenodoFile {
        +UUID id
        +str checksum
        +str filename
        +int size
        +list present_in_versions
    }

    class Creator {
        +str name
        +str affiliation
        +str orcid
    }

    class LicenseInfo {
        +str id
        +str name
        +HttpUrl url
    }

    Dataset "1" *-- "many" DatasetVersion
    DatasetVersion "1" *-- "many" ZenodoFile
    DatasetVersion "many" *-- "many" Creator
    DatasetVersion "0..1" *-- "1" LicenseInfo
```


## File Tracking Strategy

Checksum deduplicates files globally.
When the same filename appears with different checksums across versions, they're linked into a chain:

```{.mermaid}
flowchart LR
    A["data.csv<br/>md5:aaa<br/>v1.0"] -->|updated| B["data.csv<br/>md5:bbb<br/>v2.0"]
    B -->|updated| C["data.csv<br/>md5:ccc<br/>v2.1"]
```
"""

import re
from datetime import date
from typing import Optional
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)


class Creator(BaseModel):
    """Creator/author of a dataset.

    Represents a single author or contributor to a dataset. ORCID identifiers
    are validated against the standard ISO 27729 format.

    Attributes:
        name: Full name in "Family name, Given names" format
        affiliation: Institutional affiliation (optional)
        orcid: ORCID identifier in XXXX-XXXX-XXXX-XXXX format (optional)

    """

    name: str
    affiliation: str | None = None
    orcid: str | None = None

    @field_validator("orcid")
    @classmethod
    def validate_orcid(cls, v: str | None) -> str | None:
        """Validate ORCID format (16 digits with dashes)."""
        if v is None:
            return v
        orcid_pattern = r"^\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$"
        if not re.match(orcid_pattern, v):
            raise ValueError(f"Invalid ORCID format: {v}")
        return v


class LicenseInfo(BaseModel):
    """License information for a dataset.

    Contains licensing details, typically Creative Commons or other open licenses.

    Attributes:
        id: License identifier (e.g., "cc-by-4.0")
        name: Human-readable license name (optional)
        url: URL to full license text (optional)

    """

    id: str
    name: str | None = None
    url: HttpUrl | None = None


class RelatedIdentifier(BaseModel):
    """Related work identifier with relationship type.

    Represents a connection to another scholarly work using DataCite relation types.
    Used to track citations, supplements, versions, and other relationships.

    Attributes:
        identifier: Persistent identifier (DOI, Handle, etc.)
        relation: Relationship type from DataCite vocabulary
        resource_type: Type of related resource (optional)
        scheme: Identifier scheme (e.g., "doi", "handle") (optional)

    Valid Relations (DataCite):
        - cites/isCitedBy: Citation relationships
        - isSupplementTo/isSupplementedBy: Supplementary material
        - isNewVersionOf/isPreviousVersionOf: Version relationships
        - references/isReferencedBy: Reference relationships
        - And many more...

    """

    identifier: str
    relation: str
    resource_type: str | None = None
    scheme: str | None = None

    @field_validator("relation")
    @classmethod
    def validate_relation(cls, v: str) -> str:
        """Validate relation type against DataCite controlled vocabulary."""
        valid_relations = {
            "isCitedBy",
            "cites",
            "isSupplementTo",
            "isSupplementedBy",
            "isContinuedBy",
            "continues",
            "isDescribedBy",
            "describes",
            "hasMetadata",
            "isMetadataFor",
            "isNewVersionOf",
            "isPreviousVersionOf",
            "isPartOf",
            "hasPart",
            "isReferencedBy",
            "references",
            "isDocumentedBy",
            "documents",
            "isCompiledBy",
            "compiles",
            "isVariantFormOf",
            "isOriginalFormOf",
            "isIdenticalTo",
            "isAlternateIdentifier",
            "isReviewedBy",
            "reviews",
            "isDerivedFrom",
            "isSourceOf",
            "requires",
            "isRequiredBy",
            "isObsoletedBy",
            "obsoletes",
        }
        if v not in valid_relations:
            raise ValueError(f"Invalid relation type: {v}")
        return v


class GrantInfo(BaseModel):
    """Funding grant information.

    Captures details about research funding that supported the dataset creation.

    Attributes:
        code: Grant number/code from funding agency
        title: Grant title (optional)
        funder_name: Name of funding organization (optional)
        internal_id: Internal grant identifier (optional)

    """

    code: str
    title: str | None = None
    funder_name: str | None = None
    internal_id: str | None = None


class CommunityInfo(BaseModel):
    """Zenodo community information.

    Communities are curated collections of records on Zenodo.

    Attributes:
        id: Community identifier
        slug: URL-friendly community slug (optional)
        name: Human-readable community name (optional)

    """

    id: str
    slug: str | None = None
    name: str | None = None


class ZenodoFile(BaseModel):
    """Unique file identified by MD5 checksum.

    This is the core model for file tracking across dataset versions. Each unique
    checksum gets exactly one ZenodoFile object, regardless of how many versions
    contain it. Files with the same name but different checksums across versions
    are linked via previous_version/next_version pointers to form a version chain.

    Example:
        If "data.csv" appears in v1.0 (checksum A) and v2.0 (checksum B), two
        ZenodoFile objects are created and linked:
            File_A.next_version → File_B
            File_B.previous_version → File_A

    Attributes:
        id: Unique internal identifier (UUID v4)
        checksum: MD5 hash in format "md5:<32 hex chars>"
        filename: Filename from first appearance
        size: File size in bytes
        mimetype: MIME type if available (optional)
        first_dataset_version: DOI of dataset version where this checksum first appeared
        first_dataset_recid: Record ID where this checksum first appeared
        previous_version: Older file with same name but different checksum (excluded from JSON serialization)
        next_version: Newer file with same name but different checksum (excluded from JSON serialization)
        present_in_versions: List of DOIs where this file appears
        download_url: Direct download URL for this file

    """

    id: UUID = Field(default_factory=uuid4)
    checksum: str
    filename: str
    size: int
    mimetype: str | None = None

    # Version identification - tracks origin of this specific file content
    first_dataset_version: str
    first_dataset_recid: int

    # Bidirectional links to same-named files with different checksums
    # These are excluded from serialization to prevent infinite loops
    previous_version: Optional["ZenodoFile"] = Field(  # type: ignore[assignment]
        default=None, exclude=True
    )
    next_version: Optional["ZenodoFile"] = Field(  # type: ignore[assignment]
        default=None, exclude=True
    )

    # Tracks all dataset versions containing this exact file (by checksum)
    present_in_versions: list[str] = Field(default_factory=list)

    download_url: HttpUrl

    @field_validator("checksum")
    @classmethod
    def validate_checksum(cls, v: str) -> str:
        """Validate MD5 checksum format.

        Expected format: "md5:" followed by exactly 32 hexadecimal characters.
        Example: "md5:28573899cc09a145ac2c69fc1370c0bf"
        """
        if not re.match(r"^md5:[a-f0-9]{32}$", v):
            raise ValueError("Checksum must be MD5 format: md5:<32 hex chars>")
        return v

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: int) -> int:
        """Ensure file size is a positive integer."""
        if v <= 0:
            raise ValueError("File size must be positive")
        return v


class DatasetVersion(BaseModel):
    """Single published version of a dataset.

    Represents one specific version of a dataset as it appears on Zenodo.
    Versions are linked bidirectionally to enable navigation through version history.

    The files dict maps checksums to ZenodoFile objects. This allows efficient
    lookup and deduplication when the same file appears in multiple versions.

    Attributes:
        doi: Version-specific DOI (e.g., "10.5281/zenodo.20132712")
        concept_doi: Concept DOI grouping all versions (e.g., "10.5281/zenodo.13937986")
        recid: Zenodo record ID for this version
        version_label: Human-readable version string (e.g., "2.1")

        title: Dataset title
        description: Abstract/description (may contain HTML)
        creators: List of authors/contributors
        publication_date: Publication date in ISO 8601 format
        license: License information (optional)
        keywords: List of keywords/tags

        files: Dict mapping checksum → ZenodoFile for this version
        previous_version: Previous DatasetVersion in chronological order (excluded from serialization)
        next_version: Next DatasetVersion in chronological order (excluded from serialization)
        metadata_raw: Complete raw API response for reference/debugging

    """

    doi: str
    concept_doi: str
    recid: int
    version_label: str

    # Metadata fields
    title: str
    description: str | None = None
    creators: list[Creator]
    publication_date: date
    license: LicenseInfo | None = None
    keywords: list[str] = Field(default_factory=list)

    # Files in this version, keyed by checksum for O(1) lookup
    files: dict[str, ZenodoFile]

    # Bidirectional version navigation (excluded from serialization)
    previous_version: Optional["DatasetVersion"] = Field(  # type: ignore[assignment]
        default=None, exclude=True
    )
    next_version: Optional["DatasetVersion"] = Field(  # type: ignore[assignment]
        default=None, exclude=True
    )

    # Raw API response preserved for debugging or advanced use cases
    metadata_raw: dict

    @field_validator("doi", "concept_doi")
    @classmethod
    def validate_doi(cls, v: str) -> str:
        """Validate DOI format according to DataCite specification.

        Pattern: 10.XXXX/YYYYY where XXXX is registrant code and YYYYY is suffix.
        Example: "10.5281/zenodo.20132712"
        """
        doi_pattern = r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$"
        if not re.match(doi_pattern, v, re.IGNORECASE):
            raise ValueError(f"Invalid DOI format: {v}")
        return v


class Dataset(BaseModel):
    """Complete dataset spanning all versions.

    Top-level container representing a dataset concept across all its versions.
    Provides unified access to files (deduplicated by checksum) and enables
    navigation through version history.

    The all_files registry contains every unique file (by checksum) that appears
    in any version of this dataset. This enables tracking file evolution across
    versions without duplication.

    Attributes:
        concept_doi: Master DOI identifying the dataset concept (all versions)
        concept_recid: Master record ID for the dataset concept
        title: Title from latest version
        description: Description from latest version (optional)

        versions: Dict mapping version DOI → DatasetVersion
        latest_version_doi: DOI of most recent version

        all_files: Unified file registry across ALL versions (checksum → ZenodoFile)

        related_identifiers: Links to related works (citations, supplements, etc.)
        grants: Funding information
        communities: Zenodo communities containing this dataset

    """

    concept_doi: str
    concept_recid: int
    title: str
    description: str | None = None

    # All versions indexed by DOI for O(1) lookup
    versions: dict[str, DatasetVersion]

    # Reference to most recent version
    latest_version_doi: str

    # Global file registry - one ZenodoFile per unique checksum across all versions
    all_files: dict[str, ZenodoFile]

    # Relationship metadata
    related_identifiers: list[RelatedIdentifier] = Field(default_factory=list)
    grants: list[GrantInfo] = Field(default_factory=list)
    communities: list[CommunityInfo] = Field(default_factory=list)

    @field_validator("concept_doi")
    @classmethod
    def validate_concept_doi(cls, v: str) -> str:
        """Validate concept DOI format (same as regular DOI)."""
        doi_pattern = r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$"
        if not re.match(doi_pattern, v, re.IGNORECASE):
            raise ValueError(f"Invalid concept DOI format: {v}")
        return v

    @model_validator(mode="after")
    def validate_versions_not_empty(self) -> "Dataset":
        """Ensure dataset has at least one version."""
        if not self.versions:
            raise ValueError("Dataset must have at least one version")
        return self
