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

Cross-Dataset References:
    For cross-dataset references (different concept DOIs), creates bidirectional links:
    1. Forward link (references): Created immediately during processing
    2. Backward link (isReferencedBy): Deferred until all processing completes

    This deferred approach solves race conditions where target datasets don't exist
    in the graph yet due to cycle detection or recursive processing timing.

    Workflow:
        Phase 1: Create Dataset FDOs
        Phase 2: Process references → Register pending backlinks
        Phase 3: Flush all backlinks → Both directions guaranteed to exist
"""

import logging
from typing import TYPE_CHECKING, Protocol

from fdo_usecases.designs.zenodo.constants import VERSIONING_RELATIONS
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
            # Handle Zenodo dataset references specially for cross-dataset linking
            # This applies to ALL relation types, not just "references"
            if "zenodo" in identifier.identifier.lower():
                # Check recursion depth limit
                if current_depth >= self.orchestrator._reference_recursion_depth:
                    logger.warning(
                        f"Skipping recursive fetch for {identifier.identifier}: "
                        f"max depth ({self.orchestrator._reference_recursion_depth}) reached"
                    )
                    continue

                # Process cross-dataset reference with appropriate relation type
                await self._process_cross_dataset_reference(
                    identifier,
                    referencing_dataset_doi,
                    referencing_concept_doi,
                    current_depth + 1,
                )
                continue

            # Standard handler processing for non-Zenodo relations
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

        This handles DataCite relation types between different datasets (not version chains).
        Versioning relations (IsPreviousVersionOf, IsNextVersionOf, etc.) are skipped as they
        are already handled by the Versionable profile.

        Creates two types of links:
        - Forward link (immediate): references attribute on source dataset
        - Backward link (deferred): isReferencedBy attribute on target dataset

        Backlinks are created AFTER all recursive processing completes to ensure both
        datasets exist in the graph. This prevents race conditions where the target
        hasn't been created yet due to cycle detection or timing issues.

        Args:
            identifier: Related identifier pointing to referenced dataset
            referencing_dataset_doi: DOI of dataset making the reference
            referencing_concept_doi: Concept DOI of referencing dataset
            depth: Current recursion depth

        """
        referenced_doi = identifier.identifier
        relation_type = identifier.relation
        logger.info(
            f"Processing cross-dataset {relation_type} link: {referencing_dataset_doi} -> {referenced_doi}"
        )

        # Skip versioning relations - these are already handled by Versionable profile
        if relation_type in VERSIONING_RELATIONS:
            logger.debug(
                f"Skipping cross-dataset reference for versioning relation {relation_type}: "
                f"already handled by Versionable profile"
            )
            return

        # Check if already processed (avoid cycles and redundant processing)
        cycle_detected = referenced_doi in self.orchestrator._processed_datasets

        # Fetch and process if needed
        if not cycle_detected:
            logger.info(f"Recursively fetching referenced dataset: {referenced_doi}")
            await self.orchestrator._process_zenodo_reference(referenced_doi)
        else:
            logger.warning(
                f"Cycle detected! Skipping recursive fetch for: {referenced_doi}"
            )

        # Get the dataset metadata for DOI resolution (needed for version DOI mapping)
        # Try to fetch even if cycle was detected - we need concept DOI for cross-dataset check
        referenced_dataset = None
        try:
            referenced_dataset = await self.orchestrator._fetch_metadata(referenced_doi)
        except Exception as e:
            logger.warning(f"Failed to fetch metadata for {referenced_doi}: {e}")
            # Don't return here - still create forward reference and register backlink
            # Use referenced_doi directly as target if metadata unavailable

        # Create forward reference link immediately
        # Resolve referencing DOI to version DOI if it's a concept DOI
        # Use the referencing dataset's OWN metadata, NOT the referenced dataset's
        actual_referencing_doi = referencing_dataset_doi
        try:
            referencing_metadata = await self.orchestrator._fetch_metadata(
                referencing_dataset_doi
            )
            if hasattr(referencing_metadata, "latest_version_doi"):
                actual_referencing_doi = referencing_metadata.latest_version_doi
                logger.debug(
                    f"Resolved referencing DOI {referencing_dataset_doi} to version {actual_referencing_doi}"
                )
        except Exception as e:
            logger.warning(
                f"Failed to resolve referencing DOI {referencing_dataset_doi}: {e}"
            )

        referencing_record = self.orchestrator._record_graph.get(actual_referencing_doi)

        # Resolve concept DOI to version DOI if needed
        # Zenodo related identifiers often use concept DOIs, but we create FDOs for version DOIs
        # This must happen BEFORE checking for self-references
        target_doi = referenced_doi
        if referenced_dataset and hasattr(referenced_dataset, "latest_version_doi"):
            target_doi = referenced_dataset.latest_version_doi
            logger.debug(
                f"Resolved concept DOI {referenced_doi} to version DOI {target_doi}"
            )

        # Skip self-references
        if actual_referencing_doi == target_doi:
            logger.debug(
                f"Skipping self-reference: {actual_referencing_doi} -> {target_doi} "
                f"(relation: {relation_type})"
            )
            return

        # Create forward reference link
        if referencing_record:
            from fdo_usecases.designs.zenodo.constants import INFOTYPES

            references_pid = INFOTYPES.get("references")
            if references_pid:
                referencing_record.addAttribute(references_pid, target_doi)
                logger.info(
                    f"Added references link: {actual_referencing_doi} -> {target_doi}"
                )
        else:
            logger.warning(
                f"Referencing record not found for {actual_referencing_doi}, cannot add references link"
            )

        # Get concept DOI of referenced dataset to confirm it's cross-dataset
        # If cycle was detected or metadata unavailable, use fallback logic
        referenced_concept_doi = None

        if referenced_dataset is None:
            # Cycle detected or fetch failed - still create backlink
            # For cycle-detected cases, assume it's cross-dataset (different from current)
            # since we wouldn't have a circular reference within same concept
            logger.info(
                f"Registering backlink despite cycle detection or missing metadata: "
                f"{target_doi} <- {actual_referencing_doi}"
            )
            # Use target_doi as-is (may be concept DOI if metadata unavailable)
            self.orchestrator._backlink_manager.add_pending_backlink(
                target_doi=target_doi,
                referencing_doi=actual_referencing_doi,
            )
            return

        referenced_concept_doi = referenced_dataset.concept_doi

        # Only establish cross-reference if different concept DOIs
        if referenced_concept_doi == referencing_concept_doi:
            logger.debug(
                f"Skipping version chain reference: same concept DOI ({referenced_concept_doi}) - handled by Versionable profile"
            )
            return

        # Register backlink for deferred creation
        # Both datasets will exist when backlinks are flushed after all processing completes
        self.orchestrator._backlink_manager.add_pending_backlink(
            target_doi=target_doi,
            referencing_doi=actual_referencing_doi,
        )
        logger.debug(
            f"Registered pending backlink: {target_doi} <- {actual_referencing_doi}"
        )

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
