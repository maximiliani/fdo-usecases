# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""Centralized constants for Zenodo FDO creation.

This module contains all profile identifiers, InfoType PIDs, and backlink type
constants used throughout the Zenodo FDO generation process.

Profile Compliance:
- All Dataset FDOs comply with Base + Versionable profiles
- All File FDOs comply with Base + DataResource profiles
- All Publication FDOs comply with Base + Publication profiles
"""


# =============================================================================
# Profile Identifiers
# =============================================================================

#: Key used to store profile PIDs in FDO records
PROFILE_KEY = "21.T11148/076759916209e5d62bd5"

#: Base profile - required for all FDOs
BASE_PROFILE = "21.T11969/077fe9c54ed5ed26fa54"

#: Versionable profile - for dataset versions with version tracking
VERSIONABLE_PROFILE = "21.T11969/6c663a0695a411803d70"

#: DataResource profile - for file/bitstream metadata
DATARESOURCE_PROFILE = "21.T11969/0738c2ef35faef0fb552"

#: Publication profile - for scholarly publications
PUBLICATION_PROFILE = "21.T11969/e00441c49bf6cb62a4a5"


# =============================================================================
# InfoType PID Mappings
# =============================================================================

INFOTYPES = {
    #: Creator ORCID identifier
    "creator": "21.T11969/7c67083a5d218e544063",
    #: Creator institutional affiliation (ROR ID)
    "creatorAffiliation": "21.T11969/ea9f6b3d78c6608fe801",
    #: Resource creation date (ISO 8601)
    "dateCreated": "21.T11969/29f92bd203dd3eaa5a1f",
    #: Resource modification date (ISO 8601)
    "dateModified": "21.T11969/397d831aa3a9d18eb52c",
    #: Subject keywords
    "keyword": "21.T11969/793ff5c33c3aeb32907a",
    #: Resource name/title
    "name": "21.T11969/bd3e9fb9b606d2198c9e",
    #: Resource description/abstract
    "description": "21.T11969/880724416f5857987e70",
    #: Media/MIME type
    "mimeType": "21.T11969/3313b863118ed5eb0ded",
    #: Download URL for data object
    "dataObjectLocation": "21.T11969/479febb2bbe8400da547",
    #: SPDX license URL
    "spdxLicense": "21.T11969/623654b1072ae7b88202",
    #: Cryptographic checksum
    "checksum": "21.T11969/a80ed2ef79e22f1d8af8",
    #: Semantic version string
    "version": "21.T11969/be1ae3492b235faad933",
    #: Next version DOI/Handle
    "nextVersion": "21.T11969/7f1a6afddcfeefbf195b",
    #: Previous version DOI/Handle
    "previousVersion": "21.T11969/7c97f00a2a95826c1a8f",
    #: Latest version DOI/Handle
    "latestVersion": "21.T11969/2b4d6ceda80ddd63f7a9",
    #: Digital Object Identifier
    "doi": "21.T11969/48e563f148dc04d8b31c",
    #: DataCite publication type
    "dataCitePublicationType": "21.T11969/48dbf6a89f9748ae4ead",
    #: Publisher name
    "publisher": "21.T11969/cdd96207a7dfbcc0db93",
    #: Publication date (ISO 8601)
    "datePublished": "21.T11969/0c9b86e828976a85d4f2",
}


# =============================================================================
# Backlink Type Constants
# =============================================================================

#: Dataset → File relationship (forward: hasData, backward: isPartOf)
BACKLINK_DATASET_FILE = ("hasData", "isPartOf")

#: Version chain relationship (forward: isNewVersionOf, backward: isPreviousVersionOf)
BACKLINK_VERSION_CHAIN = ("isNewVersionOf", "isPreviousVersionOf")

#: Publication citation relationship (forward: cites, backward: isCitedBy)
BACKLINK_PUBLICATION_CITATION = ("cites", "isCitedBy")

#: Publication reference relationship (forward: references, backward: isReferencedBy)
BACKLINK_PUBLICATION_REFERENCE = ("references", "isReferencedBy")

#: File version chain relationship (forward: isNewVersionOf, backward: isPreviousVersionOf)
BACKLINK_FILE_VERSION_CHAIN = ("isNewVersionOf", "isPreviousVersionOf")


__all__ = [
    # Profile identifiers
    "PROFILE_KEY",
    "BASE_PROFILE",
    "VERSIONABLE_PROFILE",
    "DATARESOURCE_PROFILE",
    "PUBLICATION_PROFILE",
    # InfoTypes
    "INFOTYPES",
    # Backlink types
    "BACKLINK_DATASET_FILE",
    "BACKLINK_VERSION_CHAIN",
    "BACKLINK_PUBLICATION_CITATION",
    "BACKLINK_PUBLICATION_REFERENCE",
    "BACKLINK_FILE_VERSION_CHAIN",
]
