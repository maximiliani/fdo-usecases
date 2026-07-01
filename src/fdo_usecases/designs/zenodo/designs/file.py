# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""File FDO design for Zenodo records.

This module provides the ZenodoFileDesign class for creating File FDO records
compliant with Base + DataResource + Versionable profiles from the BAM creep-reference schema.
"""

import logging
from typing import TYPE_CHECKING

from fdo_usecases.designer_lib.executor import PidRecord, RecordDesign
from fdo_usecases.designs.zenodo.constants import (
    BACKLINK_DATASET_FILE,
    BACKLINK_FILE_VERSION_CHAIN,
    BASE_PROFILE,
    DATARESOURCE_PROFILE,
    INFOTYPES,
    PROFILE_KEY,
    VERSIONABLE_PROFILE,
)
from fdo_usecases.designs.zenodo.models.exchange import FileFDOData

if TYPE_CHECKING:
    from fdo_usecases.designs.zenodo.orchestrator import ZenodoFDODesign

logger = logging.getLogger(__name__)


class ZenodoFileDesign(RecordDesign):
    """Create File FDO records compliant with Base + DataResource + Versionable profiles.

    Each record represents one unique file identified by checksum. Files are
    deduplicated across all dataset versions - each unique checksum gets exactly
    one File FDO record.

    Example:
        ```python
        design = ZenodoFileDesign(orchestrator)
        data = FileFDOData(
            checksum="md5:abc123...",
            filename="data.csv",
            mimetype="text/csv",
            download_url="https://zenodo.org/api/records/123/files/data.csv",
            license_url="https://spdx.org/licenses/CC-BY-4.0"
        )
        record_id = await design.create_fdo(data)
        ```

    Attributes:
        orchestrator: Reference to parent ZenodoFDODesign for graph access

    """

    def __init__(self, orchestrator: "ZenodoFDODesign | None" = None):
        """Initialize the file design.

        Args:
            orchestrator: Parent ZenodoFDODesign instance (optional for standalone use)

        """
        super().__init__()
        self.orchestrator = orchestrator
        self._local_records: dict[str, PidRecord] = {}
        logger.debug("ZenodoFileDesign initialized")

    async def create_fdo(self, data: FileFDOData) -> str:
        """Create FDO record and add to executor graph.

        Args:
            data: Structured file data from exchange model

        Returns:
            Record ID (the checksum)

        """
        logger.debug(f"Creating File FDO for {data.checksum}")

        # Create PidRecord directly
        record = PidRecord()
        record.setId(data.checksum)
        record.setPid("")

        # Profiles - Base + DataResource + Versionable
        record.addAttribute(
            PROFILE_KEY, [BASE_PROFILE, DATARESOURCE_PROFILE, VERSIONABLE_PROFILE]
        )

        # Base profile
        record.addAttribute(INFOTYPES["name"], data.filename)

        # DataResource profile
        if data.mimetype:
            record.addAttribute(INFOTYPES["mimeType"], data.mimetype)

        record.addAttribute(INFOTYPES["dataObjectLocation"], data.download_url)
        record.addAttribute(INFOTYPES["checksum"], data.checksum)

        if data.license_url:
            record.addAttribute(INFOTYPES["spdxLicense"], data.license_url)

        # NEW: File version chain attributes (Option A: checksums as IDs)
        if data.previous_version_checksum:
            record.addAttribute(
                INFOTYPES["previousVersion"], data.previous_version_checksum
            )

        if data.next_version_checksum:
            record.addAttribute(INFOTYPES["nextVersion"], data.next_version_checksum)

        # Forward links: isPartOf - link this file to all dataset versions it belongs to
        if data.dataset_versions:
            for dataset_doi in data.dataset_versions:
                record.addAttribute(INFOTYPES["isPartOf"], dataset_doi)

        # Landing page location
        if data.landing_page_url:
            record.addAttribute(INFOTYPES["landingPageLocation"], data.landing_page_url)

        # Backlinks for inference
        self.addBacklink(*BACKLINK_DATASET_FILE)
        self.addBacklink(*BACKLINK_FILE_VERSION_CHAIN)

        # Store locally for testing, or in orchestrator's graph
        self._local_records[data.checksum] = record
        if self.orchestrator:
            self.orchestrator._record_graph[data.checksum] = record

        logger.debug(f"Created File FDO record for {data.checksum}")
        return data.checksum


__all__ = ["ZenodoFileDesign"]
