# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Reference handler service for processing related identifiers.

This module provides a pluggable service architecture for processing different types
of related identifiers (Zenodo datasets, external publications, etc.). Each handler
type implements a common interface and can be easily extended for new reference types.

Handlers:
    ZenodoReferenceHandler - Recursive processing for nested Zenodo datasets
    PublicationReferenceHandler - External publications (DOI, etc.)

Architecture:
    ReferenceProcessor orchestrates all handlers using strategy pattern.
    First matching handler wins for each identifier.
"""

import logging
from typing import TYPE_CHECKING, Protocol

from fdo_usecases.designs.zenodo.handlers.publication_handler import (
    PublicationReferenceHandler,
)
from fdo_usecases.designs.zenodo.handlers.zenodo_handler import ZenodoReferenceHandler
from fdo_usecases.designs.zenodo.models import RelatedIdentifier

if TYPE_CHECKING:
    from fdo_usecases.designs.zenodo.orchestrator import ZenodoFDODesign

logger = logging.getLogger(__name__)


class ReferenceHandler(Protocol):
    """Interface for reference handlers using Python Protocol (structural typing).

    This Protocol defined the required interface that all handler implementations
    must provide. It's not meant to be instantiated directly - instead, any class
    that implements these two methods will automatically be considered a ReferenceHandler.

    Example implementation:
        ```python
        class CustomHandler:
            async def can_handle(self, identifier: RelatedIdentifier) -> bool:
                return identifier.scheme == "custom"

            async def process(self, identifier: RelatedIdentifier, referencing_dataset_doi: str) -> None:
                # Process custom identifier
                pass
        ```

    """

    async def can_handle(self, identifier: RelatedIdentifier) -> bool:
        """Check if this handler can process the identifier.

        Args:
            identifier: Related identifier to check

        Returns:
            True if this handler should process the identifier

        Note:
            This method should be fast and non-blocking as it's called for every
            identifier until a match is found.

        """
        ...  # Protocol placeholder - implement in concrete classes

    async def process(
        self, identifier: RelatedIdentifier, referencing_dataset_doi: str
    ) -> None:
        """Process the reference and create appropriate FDOs.

        Args:
            identifier: Related identifier to process
            referencing_dataset_doi: DOI of the dataset that references this identifier

        Raises:
            Exception: Any error during processing (logged by caller)

        Note:
            Errors should be caught and logged internally to prevent one failed
            handler from stopping processing of other identifiers.

        """
        ...  # Protocol placeholder - implement in concrete classes


class ReferenceProcessor:
    """Orchestrate reference handling via strategy pattern.

    Maintains a list of handlers and processes each identifier with the
    first matching handler. Easy to extend with new handler types.

    Example:
        ```python
        processor = ReferenceProcessor(orchestrator)
        await processor.process_all(dataset.related_identifiers)
        ```

    Attributes:
        handlers: List of ReferenceHandler instances

    """

    def __init__(self, orchestrator: "ZenodoFDODesign"):
        """Initialize processor with handlers.

        Args:
            orchestrator: Parent ZenodoFDODesign instance

        """
        self.orchestrator = orchestrator
        self.handlers: list[ReferenceHandler] = [
            ZenodoReferenceHandler(orchestrator),
            PublicationReferenceHandler(orchestrator),
            # Future: Add more handlers here
            # GitHubReferenceHandler(),
            # DataCiteReferenceHandler(),
        ]
        logger.debug(
            f"ReferenceProcessor initialized with {len(self.handlers)} handlers"
        )

    async def process_all(
        self,
        identifiers: list[RelatedIdentifier],
        referencing_dataset_doi: str,
        referencing_concept_doi: str,
        current_depth: int = 0,
    ) -> None:
        """Process all related identifiers using appropriate handlers.

        For each identifier, finds the first matching handler and delegates
        processing. Errors in one handler don't stop processing of others.

        Special handling for "references" relations pointing to Zenodo datasets:
        - Checks if it's a cross-dataset reference (different concept DOI)
        - Recursively fetches referenced datasets (up to max depth)
        - Establishes bidirectional links via backlink inference

        Args:
            identifiers: List of related identifiers to process
            referencing_dataset_doi: DOI of the dataset that references these identifiers
            referencing_concept_doi: Concept DOI of the referencing dataset
            current_depth: Current recursion depth (for limiting nested fetches)

        """
        logger.info(
            f"Processing {len(identifiers)} related identifiers at depth {current_depth}"
        )

        for identifier in identifiers:
            # Handle "references" relation specially for cross-dataset linking
            if identifier.relation == "references":
                if "zenodo" in identifier.identifier.lower():
                    # Check recursion depth limit
                    if current_depth >= self.orchestrator._reference_recursion_depth:
                        logger.warning(
                            f"Skipping recursive fetch for {identifier.identifier}: "
                            f"max depth ({self.orchestrator._reference_recursion_depth}) reached"
                        )
                        continue

                    # Process cross-dataset reference
                    await self._process_cross_dataset_reference(
                        identifier,
                        referencing_dataset_doi,
                        referencing_concept_doi,
                        current_depth + 1,
                    )
                    continue

            # Standard handler processing for other relations
            for handler in self.handlers:
                if await handler.can_handle(identifier):
                    logger.debug(
                        f"Handler {handler.__class__.__name__} processing {identifier.identifier}"
                    )
                    try:
                        await handler.process(identifier, referencing_dataset_doi)
                    except Exception as e:
                        logger.error(
                            f"Handler {handler.__class__.__name__} failed for "
                            f"{identifier.identifier}: {e}",
                            exc_info=True,
                        )
                    break  # First matching handler wins
            else:
                logger.warning(
                    f"No handler found for identifier: {identifier.identifier}"
                )

    async def _process_cross_dataset_reference(
        self,
        identifier: RelatedIdentifier,
        referencing_dataset_doi: str,
        referencing_concept_doi: str,
        depth: int,
    ) -> None:
        """Process cross-dataset reference and establish bidirectional links.

        This handles "references" relations between different datasets (not version chains).
        Uses existing backlink inference mechanism for isReferencedBy.

        Args:
            identifier: Related identifier pointing to referenced dataset
            referencing_dataset_doi: DOI of dataset making the reference
            referencing_concept_doi: Concept DOI of referencing dataset
            depth: Current recursion depth

        """
        referenced_doi = identifier.identifier
        logger.info(
            f"Processing cross-dataset reference: {referencing_dataset_doi} -> {referenced_doi}"
        )

        # Check if already processed (avoid cycles)
        if referenced_doi in self.orchestrator._processed_datasets:
            logger.debug(f"Referenced dataset already processed: {referenced_doi}")
        else:
            # Recursively fetch and process referenced dataset
            logger.info(f"Recursively fetching referenced dataset: {referenced_doi}")
            await self.orchestrator._process_zenodo_reference(referenced_doi)

        # Get concept DOI of referenced dataset to confirm it's cross-dataset
        referenced_dataset = await self.orchestrator._fetch_metadata(referenced_doi)
        referenced_concept_doi = referenced_dataset.concept_doi

        # Only establish cross-reference if different concept DOIs
        if referenced_concept_doi == referencing_concept_doi:
            logger.debug(
                f"Skipping cross-reference: same concept DOI ({referenced_concept_doi})"
            )
            return

        # Register cross-reference for later processing
        if referenced_doi not in self.orchestrator._cross_reference_registry:
            self.orchestrator._cross_reference_registry[referenced_doi] = set()
        self.orchestrator._cross_reference_registry[referenced_doi].add(
            referencing_dataset_doi
        )

        # Add forward link: referencing dataset → references → referenced dataset
        referencing_record = self.orchestrator._record_graph.get(
            referencing_dataset_doi
        )
        if referencing_record:
            from fdo_usecases.designs.zenodo.constants import INFOTYPES

            referencing_record.addAttribute(INFOTYPES["references"], referenced_doi)
            logger.debug(
                f"Added references link: {referencing_dataset_doi} -> {referenced_doi}"
            )

        # Backward link (isReferencedBy) will be inferred by Executor from backlink rules
        # No need to explicitly add it

        # Recursively process referenced dataset's references
        if referenced_dataset.related_identifiers:
            await self.process_all(
                referenced_dataset.related_identifiers,
                referenced_doi,
                referenced_concept_doi,
                depth,
            )


__all__ = [
    "ReferenceHandler",
    "ReferenceProcessor",
    "ZenodoReferenceHandler",
    "PublicationReferenceHandler",
]
