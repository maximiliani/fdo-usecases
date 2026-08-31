# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Deferred backlink manager for cross-dataset references.

Problem Solved:
    During recursive reference processing, target datasets may not exist in the
    graph yet when we try to create backlinks. This causes missing isReferencedBy
    links in circular or complex reference chains.

    Example failure scenario:
        Dataset A (20132712) cites Dataset B (11668375)
        Dataset B cites Dataset C (20132382)
        Dataset C cites Dataset D (11667673)
        Dataset D cites Dataset B (cycle detected!)

    When trying to create backlink from B to A at line 400, dataset B's FDOs might
    not exist in _record_graph yet because cycle detection skipped the recursive fetch.

Solution:
    Collect all backlink requests during processing, then apply them AFTER all
    datasets have been fully created. This guarantees both source and target
    nodes exist in the graph.

Workflow:
    Phase 1: Create Dataset FDOs (orchestrator._process_doi)
    Phase 2: Process references recursively (ReferenceProcessor.process_all)
             → Backlinks registered but NOT created yet
    Phase 3: Flush all pending backlinks (BacklinkManager.flush_backlinks)
             → Both directions guaranteed to exist

Design Principles:
    KISS: Simple dict-of-sets data structure, minimal logic
    SRP: Only manages backlinks, nothing else
    DRY: Centralizes backlink creation logic used in multiple places
"""

import logging
from typing import TYPE_CHECKING

from fdo_usecases.designer_lib.executor import placeholder_pid

if TYPE_CHECKING:
    from fdo_usecases.designer_lib.executor import PidRecord

logger = logging.getLogger(__name__)


class BacklinkManager:
    """Manages deferred creation of bidirectional cross-dataset reference links.

    This class solves the race condition where backlinks are created before both
    source and target datasets exist in the graph. By deferring backlink creation
    until after all processing completes, we ensure bidirectional links are never
    missed due to timing issues or cycle detection.

    Attributes:
        _record_graph: Reference to orchestrator's record graph
        _pending_backlinks: Maps target_doi → set of referencing_dois

    Example:
        ```python
        manager = BacklinkManager(record_graph)

        # During reference processing
        manager.add_pending_backlink(
            target_doi="10.5281/zenodo.123",
            referencing_doi="10.5281/zenodo.456"
        )

        # After all processing completes
        success, skipped = manager.flush_backlinks()
        # Logs: "Created 1 cross-dataset backlinks, skipped 0"
        ```

    """

    def __init__(self, record_graph: dict[str, "PidRecord"]):
        """Initialize backlink manager with reference to record graph.

        Args:
            record_graph: Orchestrator's record graph dictionary mapping DOIs to PidRecords

        """
        self._record_graph = record_graph
        self._pending_backlinks: dict[str, set[str]] = {}
        logger.debug("BacklinkManager initialized")

    def add_pending_backlink(self, target_doi: str, referencing_doi: str) -> None:
        """Register a backlink to be created later.

        Called during reference processing when a cross-dataset reference is found.
        The actual backlink is NOT created immediately - it's queued for later creation
        after all datasets exist in the graph.

        Idempotent: Adding the same backlink multiple times has no effect (uses set).

        Args:
            target_doi: DOI of the dataset being referenced (will receive isReferencedBy)
            referencing_doi: DOI of the dataset making the reference (has references link)

        Example:
            If A cites B:
            - Forward link: A.references = B (created immediately)
            - Backlink: B.isReferencedBy = A (registered here, created in flush)

            add_pending_backlink(target_doi="B", referencing_doi="A")

        """
        if target_doi not in self._pending_backlinks:
            self._pending_backlinks[target_doi] = set()

        self._pending_backlinks[target_doi].add(referencing_doi)
        logger.debug(f"Registered pending backlink: {target_doi} <- {referencing_doi}")

    def flush_backlinks(self) -> tuple[int, int]:
        """Apply all pending backlinks to the record graph.

        Called once after all DOI processing and reference resolution completes.
        At this point, both source and target datasets are guaranteed to exist
        in the graph (or will be skipped gracefully).

        For each pending backlink:
        - Checks if target exists in graph
        - Checks if backlink already exists (avoid duplicates)
        - Creates isReferencedBy attribute on target
        - Logs at INFO level

        Returns:
            Tuple of (success_count, skipped_count)
            - success_count: Number of backlinks successfully created
            - skipped_count: Number skipped (target not found or duplicate)

        Raises:
            No exceptions - errors are logged and processing continues

        Example:
            success, skipped = manager.flush_backlinks()
            logger.info(f"Created {success} backlinks, skipped {skipped}")

        """
        success_count = 0
        skipped_count = 0

        from fdo_usecases.designs.zenodo.constants import INFOTYPES

        is_referenced_by_pid = INFOTYPES.get("isReferencedBy")
        if not is_referenced_by_pid:
            logger.error("isReferencedBy InfoType not found in INFOTYPES")
            return 0, len(self._pending_backlinks)

        for target_doi, referencing_dois in self._pending_backlinks.items():
            target_record = self._record_graph.get(placeholder_pid(target_doi))

            if not target_record:
                logger.warning(
                    f"Target dataset {target_doi} not found in graph - "
                    f"skipping {len(referencing_dois)} backlink(s)"
                )
                skipped_count += len(referencing_dois)
                continue

            for referencing_doi in referencing_dois:
                # Check if backlink already exists to avoid duplicates
                existing_backlinks = [
                    attr[1]
                    for attr in target_record._tuples
                    if attr[0] == is_referenced_by_pid
                ]

                if referencing_doi in existing_backlinks:
                    logger.debug(
                        f"Backlink already exists: {target_doi} <- {referencing_doi}"
                    )
                    skipped_count += 1
                    continue

                # Create the backlink
                target_record.addAttribute(
                    is_referenced_by_pid, placeholder_pid(referencing_doi)
                )
                logger.info(
                    f"Added isReferencedBy backlink: {target_doi} <- {referencing_doi}"
                )
                success_count += 1

        return success_count, skipped_count

    def clear(self) -> None:
        """Clear all pending backlinks.

        Called after flush to free memory, or when resetting state.
        This does NOT remove backlinks from the graph - only clears the pending queue.

        """
        self._pending_backlinks.clear()
        logger.debug("BacklinkManager cleared all pending backlinks")


__all__ = ["BacklinkManager"]
