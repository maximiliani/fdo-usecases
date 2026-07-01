# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

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

    This Protocol defines the required interface that all handler implementations
    must provide. It's not meant to be instantiated directly - instead, any class
    that implements these two methods will automatically be considered a ReferenceHandler.

    Example implementation:
        ```python
        class CustomHandler:
            async def can_handle(self, identifier: RelatedIdentifier) -> bool:
                return identifier.scheme == "custom"

            async def process(self, identifier: RelatedIdentifier) -> None:
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

    async def process(self, identifier: RelatedIdentifier) -> None:
        """Process the reference and create appropriate FDOs.

        Args:
            identifier: Related identifier to process

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

    async def process_all(self, identifiers: list[RelatedIdentifier]) -> None:
        """Process all related identifiers using appropriate handlers.

        For each identifier, finds the first matching handler and delegates
        processing. Errors in one handler don't stop processing of others.

        Args:
            identifiers: List of related identifiers to process

        """
        logger.info(f"Processing {len(identifiers)} related identifiers")

        for identifier in identifiers:
            for handler in self.handlers:
                if await handler.can_handle(identifier):
                    logger.debug(
                        f"Handler {handler.__class__.__name__} processing {identifier.identifier}"
                    )
                    try:
                        await handler.process(identifier)
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


__all__ = [
    "ReferenceHandler",
    "ReferenceProcessor",
    "ZenodoReferenceHandler",
    "PublicationReferenceHandler",
]
