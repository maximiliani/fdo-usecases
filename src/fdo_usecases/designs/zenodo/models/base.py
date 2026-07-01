# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""Base metadata models for Zenodo records.

This module contains foundational models used across multiple Zenodo record types:
- Creator (author/contributor with ORCID/ROR validation)
- LicenseInfo (license metadata)
- GrantInfo (funding information)
- CommunityInfo (Zenodo community membership)
- RelatedIdentifier (related work with DataCite relation types)
"""

import re

from pydantic import BaseModel, HttpUrl, field_validator


class Creator(BaseModel):
    """Creator/author of a dataset.

    Represents a single author or contributor to a dataset. ORCID identifiers
    are validated against the standard ISO 27729 format. ROR IDs are validated
    against the standard ROR identifier format.

    Attributes:
        name: Full name in "Family name, Given names" format
        affiliation: Institutional affiliation (optional)
        orcid: ORCID identifier in XXXX-XXXX-XXXX-XXXX format (optional)
        ror_id: ROR identifier URL for institutional affiliation (optional)

    """

    name: str
    affiliation: str | None = None
    orcid: str | None = None
    ror_id: str | None = None

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

    @field_validator("ror_id")
    @classmethod
    def validate_ror_id(cls, v: str | None) -> str | None:
        """Validate ROR ID format."""
        if v is None:
            return v
        ror_pattern = r"^https://ror\.org/0[a-h0-9]{6}[0-9a-z]$"
        if not re.match(ror_pattern, v):
            raise ValueError(f"Invalid ROR ID format: {v}")
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


__all__ = [
    "Creator",
    "LicenseInfo",
    "RelatedIdentifier",
    "GrantInfo",
    "CommunityInfo",
]
