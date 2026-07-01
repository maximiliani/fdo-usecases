# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Dataset container models for Zenodo records.

This module contains the Dataset model which serves as the top-level container
for all versions of a Zenodo dataset. It provides unified access to files
(deduplicated by checksum) and enables navigation through version history.
"""

import re

from pydantic import BaseModel, Field, field_validator, model_validator

from fdo_usecases.designs.zenodo.models.base import (
    CommunityInfo,
    GrantInfo,
    RelatedIdentifier,
)
from fdo_usecases.designs.zenodo.models.file import ZenodoFile
from fdo_usecases.designs.zenodo.models.version import DatasetVersion

# Re-export for convenience
__all__ = ["Dataset", "DatasetVersion"]


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


__all__ = ["Dataset"]
