# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""File metadata models for Zenodo records.

This module contains the ZenodoFile model for representing individual files
within Zenodo datasets. Files are identified by checksum (MD5) to enable
deduplication across versions.
"""

import re
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator


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
        previous_version_checksum: Checksum of previous file version (for FDO creation)
        next_version_checksum: Checksum of next file version (for FDO creation)

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

    # NEW: Checksum references for FDO version chain creation
    previous_version_checksum: str | None = None
    next_version_checksum: str | None = None

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


__all__ = ["ZenodoFile"]
