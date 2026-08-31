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

from fdo_usecases.designer_lib.executor import placeholder_pid
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
        - Forward link (immediate): references attribute on the specific version DOI
        - Backward link (deferred): isReferencedBy attribute on target dataset

        The forward link is created on the specific version DOI that contains the
        related identifier in its metadata (referencing_dataset_doi), NOT on the
        resolved latest version. This preserves version-specific relationship info.

        Backlinks are created AFTER all recursive processing completes to ensure both
        datasets exist in the graph. This prevents race conditions where the target
        hasn't been created yet due to cycle detection or timing issues.

        Args:
            identifier: Related identifier pointing to referenced dataset
            referencing_dataset_doi: DOI of dataset making the reference (version-specific)
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

        # Get the dataset metadata for DOI resolution (from cache - no re-fetching)
        referenced_dataset = None
        try:
            referenced_dataset = await self.orchestrator._fetch_metadata(referenced_doi)
        except Exception as e:
            logger.warning(f"Failed to fetch metadata for {referenced_doi}: {e}")

        # Use the specific version DOI as the source of the forward link.
        # This is the version that contains the related identifier in its metadata.
        actual_referencing_doi = referencing_dataset_doi

        # Resolve target DOI: prefer the specific version DOI from the related
        # identifier. If it's a concept DOI (not in graph), resolve to latest version.
        target_doi = referenced_doi
        if referenced_dataset and hasattr(referenced_dataset, "latest_version_doi"):
            if referenced_doi not in self.orchestrator._record_graph:
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

        # Create forward reference link on the specific version DOI
        referencing_record = self.orchestrator._record_graph.get(
            placeholder_pid(actual_referencing_doi)
        )

        if referencing_record:
            from fdo_usecases.designs.zenodo.constants import INFOTYPES

            references_pid = INFOTYPES.get("references")
            if references_pid:
                # Check for duplicate forward link before adding
                existing_refs = [
                    attr[1]
                    for attr in referencing_record._tuples
                    if attr[0] == references_pid
                ]
                target_placeholder = placeholder_pid(target_doi)
                if target_placeholder not in existing_refs:
                    referencing_record.addAttribute(references_pid, target_placeholder)
                    logger.info(
                        f"Added references link: {actual_referencing_doi} -> {target_doi}"
                    )
                else:
                    logger.debug(
                        f"References link already exists: {actual_referencing_doi} -> {target_doi}"
                    )
        else:
            logger.warning(
                f"Referencing record not found for {actual_referencing_doi}, cannot add references link"
            )

        # Get concept DOI of referenced dataset to confirm it's cross-dataset
        referenced_concept_doi = None

        if referenced_dataset is None:
            # Cycle detected or fetch failed - still create backlink
            logger.info(
                f"Registering backlink despite cycle detection or missing metadata: "
                f"{target_doi} <- {actual_referencing_doi}"
            )
            self.orchestrator._backlink_manager.add_pending_backlink(
                target_doi=placeholder_pid(target_doi),
                referencing_doi=placeholder_pid(actual_referencing_doi),
            )
            return

        referenced_concept_doi = referenced_dataset.concept_doi

        # Only establish cross-reference backlink if different concept DOIs
        if referenced_concept_doi == referencing_concept_doi:
            logger.debug(
                f"Skipping backlink for version chain reference: same concept DOI ({referenced_concept_doi}) - handled by Versionable profile"
            )
            return

        # Register backlink for deferred creation
        self.orchestrator._backlink_manager.add_pending_backlink(
            target_doi=placeholder_pid(target_doi),
            referencing_doi=placeholder_pid(actual_referencing_doi),
        )
        logger.debug(
            f"Registered pending backlink: {target_doi} <- {actual_referencing_doi}"
        )


__all__ = [
    "ReferenceHandler",
    "ReferenceProcessor",
    "ZenodoReferenceHandler",
    "PublicationReferenceHandler",
]
