# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Publication reference handler for external publications."""

import logging
from typing import TYPE_CHECKING

from fdo_usecases.designs.zenodo.constants import INFOTYPES
from fdo_usecases.designs.zenodo.designs import PublicationDesign
from fdo_usecases.designs.zenodo.models import RelatedIdentifier
from fdo_usecases.designs.zenodo.models.exchange import PublicationFDOData

if TYPE_CHECKING:
    from fdo_usecases.designs.zenodo.orchestrator import ZenodoFDODesign

logger = logging.getLogger(__name__)


class PublicationReferenceHandler:
    """Handle references to external publications.

    This handler creates Publication FDO records for non-Zenodo references
    (DOIs, Handles, etc.). Only minimal metadata is available from the
    related_identifier field, so many fields will be None.

    Attributes:
        orchestrator: Reference to parent ZenodoFDODesign for graph access
        publication_design: PublicationDesign instance for creating FDOs

    """

    def __init__(self, orchestrator: "ZenodoFDODesign"):
        """Initialize publication handler with orchestrator reference.

        Args:
            orchestrator: Parent ZenodoFDODesign instance

        """
        self.orchestrator = orchestrator
        self.publication_design = PublicationDesign(orchestrator)
        logger.debug("PublicationReferenceHandler initialized")

    async def can_handle(self, identifier: RelatedIdentifier) -> bool:
        """Check if identifier is a non-Zenodo reference.

        Handles DOIs and other persistent identifiers that are NOT Zenodo.

        Args:
            identifier: Related identifier to check

        Returns:
            True if identifier has scheme 'doi' and is not Zenodo

        """
        # Handle DOIs that are NOT Zenodo
        if identifier.scheme == "doi":
            return "zenodo" not in identifier.identifier.lower()
        # Also handle other identifier schemes as publications
        return "zenodo" not in identifier.identifier.lower()

    async def process(
        self, identifier: RelatedIdentifier, referencing_dataset_doi: str
    ) -> None:
        """Create Publication FDO with available metadata.

        Creates a minimal PublicationFDOData with only the information
        available from the related_identifier field. Also creates forward
        link from dataset to publication (cites/references).

        Args:
            identifier: Related identifier to process
            referencing_dataset_doi: DOI of dataset that references this publication

        """
        try:
            pub_data = PublicationFDOData(
                identifier=identifier.identifier,
                resource_type=identifier.resource_type,
                publisher=None,
                publication_date=None,
                title=None,
                description=None,
                creator_orcids=[],
                referenced_by_datasets=[referencing_dataset_doi],
            )

            record_id = await self.publication_design.create_fdo(pub_data)
            logger.info(f"Created publication FDO for {record_id}")

            # Add forward link from dataset to publication
            if identifier.relation in ["cites", "references"]:
                record = self.orchestrator._record_graph.get(referencing_dataset_doi)
                if record:
                    if identifier.relation == "cites":
                        record.addAttribute(INFOTYPES["cites"], identifier.identifier)
                    else:
                        record.addAttribute(
                            INFOTYPES["references"], identifier.identifier
                        )
                    logger.debug(
                        f"Added {identifier.relation} link from {referencing_dataset_doi} to {identifier.identifier}"
                    )

        except Exception as e:
            logger.error(
                f"Failed to create publication FDO for {identifier.identifier}: {e}",
                exc_info=True,
            )


__all__ = ["PublicationReferenceHandler"]
