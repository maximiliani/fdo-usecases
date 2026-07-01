# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""Zenodo reference handler for nested dataset processing."""

import logging
from typing import TYPE_CHECKING

from fdo_usecases.designs.zenodo.models import RelatedIdentifier

if TYPE_CHECKING:
    from fdo_usecases.designs.zenodo.orchestrator import ZenodoFDODesign

logger = logging.getLogger(__name__)


class ZenodoReferenceHandler:
    """Handle references to other Zenodo datasets.

    This handler recursively processes Zenodo dataset references by creating
    a new ZenodoFDODesign instance and executing it. The orchestrator's
    _processed_datasets set prevents infinite loops.

    """

    def __init__(self, orchestrator: "ZenodoFDODesign"):
        """Initialize handler with reference to orchestrator.

        Args:
            orchestrator: Parent ZenodoFDODesign instance

        """
        self.orchestrator = orchestrator
        logger.debug("ZenodoReferenceHandler initialized")

    async def can_handle(self, identifier: RelatedIdentifier) -> bool:
        """Check if identifier points to a Zenodo dataset.

        Args:
            identifier: Related identifier to check

        Returns:
            True if identifier contains 'zenodo' (case-insensitive)

        """
        return "zenodo" in identifier.identifier.lower()

    async def process(self, identifier: RelatedIdentifier) -> None:
        """Recursively process nested Zenodo dataset.

        Creates a new ZenodoFDODesign instance and executes it. The orchestrator's
        _processed_datasets set prevents processing the same dataset twice.

        Args:
            identifier: Related identifier pointing to Zenodo dataset

        """
        doi = identifier.identifier
        logger.info(f"Processing nested Zenodo reference: {doi}")

        if doi not in self.orchestrator._processed_datasets:
            await self.orchestrator._process_zenodo_reference(doi)
        else:
            logger.debug(f"Skipping already processed Zenodo dataset: {doi}")


__all__ = ["ZenodoReferenceHandler"]
