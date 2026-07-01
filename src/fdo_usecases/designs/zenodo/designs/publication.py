# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Publication FDO design for Zenodo records.

This module provides the PublicationDesign class for creating Publication FDO records
compliant with Base + Publication profiles from the BAM creep-reference schema.
"""

import logging
from typing import TYPE_CHECKING

from fdo_usecases.designer_lib.executor import PidRecord, RecordDesign
from fdo_usecases.designs.zenodo.constants import (
    BACKLINK_PUBLICATION_CITATION,
    BACKLINK_PUBLICATION_REFERENCE,
    BASE_PROFILE,
    INFOTYPES,
    PROFILE_KEY,
    PUBLICATION_PROFILE,
)
from fdo_usecases.designs.zenodo.models.exchange import PublicationFDOData
from fdo_usecases.designs.zenodo.utils.text_utils import strip_html_and_truncate

if TYPE_CHECKING:
    from fdo_usecases.designs.zenodo.orchestrator import ZenodoFDODesign

logger = logging.getLogger(__name__)


class PublicationDesign(RecordDesign):
    """Create Publication FDO records compliant with Base + Publication profiles.

    Each record represents one related publication (non-Zenodo). For related
    identifiers, only minimal metadata is typically available from the Zenodo API,
    so many fields may be None or empty.

    Example:
        ```python
        design = PublicationDesign(orchestrator)
        data = PublicationFDOData(
            identifier="10.1016/j.actamat.2025.120735",
            resource_type="publication-article",
            publisher="Elsevier",
            publication_date="2025-01-15",
            title="Creep reference data...",
            description="Abstract text",
            creator_orcids=["0000-0000-0000-0000"]
        )
        record_id = await design.create_fdo(data)
        ```

    Attributes:
        orchestrator: Reference to parent ZenodoFDODesign for graph access

    """

    def __init__(self, orchestrator: "ZenodoFDODesign | None" = None):
        """Initialize the publication design.

        Args:
            orchestrator: Parent ZenodoFDODesign instance (optional for standalone use)

        """
        super().__init__()
        self.orchestrator = orchestrator
        self._local_records: dict[str, PidRecord] = {}
        logger.debug("PublicationDesign initialized")

    async def create_fdo(self, data: PublicationFDOData) -> str:
        """Create FDO record and add to executor graph.

        Args:
            data: Structured publication data from exchange model

        Returns:
            Record ID (the identifier/DOI)

        """
        logger.info(f"Creating Publication FDO for {data.identifier}")

        # Create PidRecord directly
        record = PidRecord()
        record.setId(data.identifier)
        record.setPid("")

        # Profiles - Base + Publication
        record.addAttribute(PROFILE_KEY, [BASE_PROFILE, PUBLICATION_PROFILE])

        # Publication profile
        record.addAttribute(INFOTYPES["doi"], data.identifier)

        if data.resource_type:
            record.addAttribute(
                INFOTYPES["dataCitePublicationType"], data.resource_type
            )

        if data.publisher:
            record.addAttribute(INFOTYPES["publisher"], data.publisher)

        if data.publication_date:
            record.addAttribute(INFOTYPES["datePublished"], data.publication_date)

        if data.title:
            record.addAttribute(INFOTYPES["name"], data.title)

        if data.description:
            desc = strip_html_and_truncate(data.description)
            record.addAttribute(INFOTYPES["description"], desc)

        if data.creator_orcids:
            record.addAttribute(INFOTYPES["creator"], data.creator_orcids)  # type: ignore[arg-type]

        # Backlinks for inference
        self.addBacklink(*BACKLINK_PUBLICATION_CITATION)
        self.addBacklink(*BACKLINK_PUBLICATION_REFERENCE)

        # Store locally for testing, or in orchestrator's graph
        self._local_records[data.identifier] = record
        if self.orchestrator:
            self.orchestrator._record_graph[data.identifier] = record

        logger.debug(f"Created Publication FDO record for {data.identifier}")
        return data.identifier


__all__ = ["PublicationDesign"]
