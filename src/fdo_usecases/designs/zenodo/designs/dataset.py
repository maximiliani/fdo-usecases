# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Dataset FDO design for Zenodo records.

This module provides the ZenodoDatasetDesign class for creating Dataset FDO records
compliant with Base + Versionable profiles from the BAM creep-reference schema.
"""

import logging
from typing import TYPE_CHECKING

from fdo_usecases.designer_lib.executor import PidRecord, RecordDesign
from fdo_usecases.designs.zenodo.constants import (
    BACKLINK_DATASET_FILE,
    BACKLINK_NAMED_REFERENCE,
    BACKLINK_VERSION_CHAIN,
    BASE_PROFILE,
    INFOTYPES,
    PROFILE_KEY,
    VERSIONABLE_PROFILE,
)
from fdo_usecases.designs.zenodo.models.exchange import DatasetFDOData
from fdo_usecases.utils.text_utils import strip_html_and_truncate

if TYPE_CHECKING:
    from fdo_usecases.designs.zenodo.orchestrator import ZenodoFDODesign

logger = logging.getLogger(__name__)


class ZenodoDatasetDesign(RecordDesign):
    """Create Dataset FDO records compliant with Base + Versionable profiles.

    Each record represents one version of a Zenodo dataset. The design adds
    attributes using InfoType PIDs as keys and profile PIDs to indicate
    compliance with Base and Versionable profiles.

    Example:
        ```python
        design = ZenodoDatasetDesign(orchestrator)
        data = DatasetFDOData(
            doi="10.5281/zenodo.123456",
            title="My Dataset",
            description="Dataset description",
            publication_date=date(2024, 1, 1),
            version_label="1.0",
            creators=[CreatorData(orcid="0000-0000-0000-0000")],
            keywords=["keyword1", "keyword2"],
            previous_version_doi=None,
            next_version_doi="10.5281/zenodo.789012",
            latest_version_doi="10.5281/zenodo.999999"
        )
        record_id = await design.create_fdo(data)
        ```

    Attributes:
        orchestrator: Reference to parent ZenodoFDODesign for graph access

    """

    def __init__(self, orchestrator: "ZenodoFDODesign | None" = None):
        """Initialize the dataset design.

        Args:
            orchestrator: Parent ZenodoFDODesign instance (optional for standalone use)

        """
        super().__init__()
        self.orchestrator = orchestrator
        self._local_records: dict[str, PidRecord] = {}
        logger.debug("ZenodoDatasetDesign initialized")

    async def create_fdo(self, data: DatasetFDOData) -> str:
        """Create FDO record and add to executor graph.

        Args:
            data: Structured dataset data from exchange model

        Returns:
            Record ID (the version DOI)

        """
        logger.info(f"Creating Dataset FDO for {data.doi}")

        # Create PidRecord directly
        record = PidRecord()
        record.setId(data.doi)
        record.setPid("")

        # Profiles - Base + Versionable
        profiles = [BASE_PROFILE, VERSIONABLE_PROFILE]
        record.addAttribute(PROFILE_KEY, profiles)  # type: ignore[arg-type]

        # Base profile attributes
        record.addAttribute(INFOTYPES["name"], data.title)

        if data.description:
            desc = strip_html_and_truncate(data.description)
            record.addAttribute(INFOTYPES["description"], desc)

        record.addAttribute(INFOTYPES["dateCreated"], data.publication_date.isoformat())

        # Creators (ORCIDs)
        creator_orcids = [c.orcid for c in data.creators if c.orcid]
        if creator_orcids:
            logger.debug(f"Adding {len(creator_orcids)} creator ORCIDs")
            record.addAttribute(INFOTYPES["creator"], creator_orcids)  # type: ignore[arg-type]

        # Creator affiliations (ROR IDs)
        creator_ror_ids = [c.ror_id for c in data.creators if c.ror_id]
        if creator_ror_ids:
            logger.debug(f"Adding {len(creator_ror_ids)} ROR IDs")
            record.addAttribute(INFOTYPES["creatorAffiliation"], creator_ror_ids)  # type: ignore[arg-type]

        # Keywords
        if data.keywords:
            record.addAttribute(INFOTYPES["keyword"], data.keywords)  # type: ignore[arg-type]

        # Versionable profile attributes
        record.addAttribute(INFOTYPES["version"], data.version_label)

        if data.previous_version_doi:
            record.addAttribute(INFOTYPES["previousVersion"], data.previous_version_doi)

        if data.next_version_doi:
            record.addAttribute(INFOTYPES["nextVersion"], data.next_version_doi)

        if data.latest_version_doi and data.latest_version_doi != data.doi:
            record.addAttribute(INFOTYPES["latestVersion"], data.latest_version_doi)

        # Forward links: hasPart - link this dataset version to its files
        if data.files:
            for checksum in data.files:
                record.addAttribute(INFOTYPES["hasPart"], checksum)

        # Landing page location
        if data.landing_page_url:
            record.addAttribute(INFOTYPES["landingPageLocation"], data.landing_page_url)

        # Preview images
        if data.preview_images:
            for img_url in data.preview_images:
                record.addAttribute(INFOTYPES["previewImage"], img_url)
            logger.debug(f"Added {len(data.preview_images)} preview images")

        # Backlinks for inference
        self.addBacklink(*BACKLINK_DATASET_FILE)
        self.addBacklink(*BACKLINK_VERSION_CHAIN)

        #: Cross-dataset relationships using composite namedReference type
        #: Enables bidirectional navigation for any DataCite relation type
        self.addBacklink(*BACKLINK_NAMED_REFERENCE)

        # Store locally for testing, or in orchestrator's graph
        self._local_records[data.doi] = record
        if self.orchestrator:
            self.orchestrator._record_graph[data.doi] = record

        logger.debug(f"Created Dataset FDO record for {data.doi}")
        return data.doi


__all__ = ["ZenodoDatasetDesign"]
