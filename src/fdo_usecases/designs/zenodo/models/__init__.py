# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""All Zenodo models."""

from fdo_usecases.designs.zenodo.models.base import (
    CommunityInfo,
    Creator,
    GrantInfo,
    LicenseInfo,
    RelatedIdentifier,
)
from fdo_usecases.designs.zenodo.models.dataset import Dataset, DatasetVersion
from fdo_usecases.designs.zenodo.models.exceptions import (
    DOINotFoundError,
    RateLimitError,
    ValidationError,
    ZenodoAPIError,
)
from fdo_usecases.designs.zenodo.models.exchange import (
    CreatorData,
    DatasetFDOData,
    FileFDOData,
    PublicationFDOData,
)
from fdo_usecases.designs.zenodo.models.file import ZenodoFile

__all__ = [
    # Metadata models
    "Creator",
    "LicenseInfo",
    "RelatedIdentifier",
    "GrantInfo",
    "CommunityInfo",
    "Dataset",
    "DatasetVersion",
    "ZenodoFile",
    # Exchange models
    "CreatorData",
    "DatasetFDOData",
    "FileFDOData",
    "PublicationFDOData",
    # Exceptions
    "ZenodoAPIError",
    "DOINotFoundError",
    "RateLimitError",
    "ValidationError",
]

# Rebuild all models to resolve forward references
Creator.model_rebuild()
LicenseInfo.model_rebuild()
RelatedIdentifier.model_rebuild()
GrantInfo.model_rebuild()
CommunityInfo.model_rebuild()
ZenodoFile.model_rebuild()
DatasetVersion.model_rebuild()
Dataset.model_rebuild()
