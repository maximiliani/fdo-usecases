# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""Dataset version models for Zenodo records.

This module contains the DatasetVersion model for representing individual versions
of Zenodo datasets. Versions are linked bidirectionally to enable navigation
through version history.
"""

import re
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .base import Creator, LicenseInfo
from .file import ZenodoFile


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
    license: Optional[LicenseInfo] = None
    keywords: list[str] = Field(default_factory=list)

    # Files in this version, keyed by checksum for O(1) lookup
    files: dict[str, ZenodoFile]

    # Bidirectional version navigation (excluded from serialization)
    previous_version: Optional["DatasetVersion"] = Field(default=None, exclude=True)
    next_version: Optional["DatasetVersion"] = Field(default=None, exclude=True)

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


__all__ = ["DatasetVersion"]
