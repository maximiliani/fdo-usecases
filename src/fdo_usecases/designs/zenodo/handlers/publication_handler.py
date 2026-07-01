# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""Publication reference handler for external publications."""

import logging
from typing import TYPE_CHECKING

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

    """

    def __init__(self, orchestrator: "ZenodoFDODesign"):
        """Initialize publication handler with orchestrator reference.

        Args:
            orchestrator: Parent ZenodoFDODesign instance

        """
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

    async def process(self, identifier: RelatedIdentifier) -> None:
        """Create Publication FDO with available metadata.

        Creates a minimal PublicationFDOData with only the information
        available from the related_identifier field.

        Args:
            identifier: Related identifier to process

        """
        try:
            pub_data = PublicationFDOData(
                identifier=identifier.identifier,
                resource_type=identifier.resource_type,
                publisher=None,  # Not available from related_identifier
                publication_date=None,  # Not available
                title=None,  # Not available
                description=None,  # Not available
                creator_orcids=[],  # Not available
            )

            record_id = await self.publication_design.create_fdo(pub_data)
            logger.info(f"Created publication FDO for {record_id}")

        except Exception as e:
            logger.error(
                f"Failed to create publication FDO for {identifier.identifier}: {e}",
                exc_info=True,
            )
            # Continue processing other references (Option A)


__all__ = ["PublicationReferenceHandler"]
