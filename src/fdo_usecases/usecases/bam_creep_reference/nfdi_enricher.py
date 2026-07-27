# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Add NFDI profile to existing FDO records.

This module provides post-processing enrichment to add NFDI consortium profile
to FDOs created in the BAM creep-reference usecase. It uses keyword-based filtering
to identify target FDO types (experiment, material, file, dataset).

Example:
    >>> enricher = NFDIEnricher()
    >>> count = enricher.enrich_graph(zenodo_graph)
    >>> print(f"Enriched {count} FDOs with NFDI profile")

"""

import logging

from fdo_usecases.designer_lib.executor import PidRecord

logger = logging.getLogger(__name__)

NFDI_PROFILE = "21.T11969/175a75397933f1b370af"
PROFILE_KEY = "21.T11148/076759916209e5d62bd5"
INFOTYPE_NFDI_CONSORTIA = "21.T11969/3b01aa9a09f0fab04265"
INFOTYPE_GRANT_NUMBER = "21.T11969/1c25f48eb6a47b22a9cc"


class NFDIEnricher:
    """Add NFDI consortium profile to existing FDO records.

    This class adds the NFDI profile and associated attributes (consortium name,
    grant number) to FDOs that match specific keywords. It's designed as a
    post-processing step to keep the core Zenodo and Creep designs reusable.

    Attributes:
        consortium_name: NFDI consortium name to add
        grant_number: Grant number to add
        target_keywords: Set of keywords identifying NFDI-relevant FDO types

    """

    def __init__(self):
        """Initialize NFDI enricher with consortium and grant information."""
        self.consortium_name = "NFDI-MatWerk IUC02"
        self.grant_number = "460247524"
        # Target keywords that indicate NFDI-relevant FDO types
        self.target_keywords = {"experiment", "material", "file", "dataset"}

    def enrich_record(self, record: PidRecord) -> None:
        """Add NFDI profile and attributes to a single record.

        Args:
            record: PidRecord to enrich (modified in-place)

        """
        record_id = record.getId()

        # Get existing profiles
        existing_profiles = None
        for attr in record._tuples:
            if attr[0] == PROFILE_KEY:
                existing_profiles = attr[1]
                break

        # Add NFDI profile to list
        if existing_profiles:
            if isinstance(existing_profiles, list):
                if NFDI_PROFILE not in existing_profiles:
                    existing_profiles.append(NFDI_PROFILE)
                    record.addAttribute(PROFILE_KEY, existing_profiles)
            else:
                record.addAttribute(PROFILE_KEY, [existing_profiles, NFDI_PROFILE])
        else:
            record.addAttribute(PROFILE_KEY, [NFDI_PROFILE])

        # Add NFDI attributes
        record.addAttribute(INFOTYPE_NFDI_CONSORTIA, self.consortium_name)
        record.addAttribute(INFOTYPE_GRANT_NUMBER, self.grant_number)

        logger.debug(f"Added NFDI profile to {record_id}")

    def enrich_graph(self, graph: dict[str, PidRecord]) -> int:
        """Enrich all matching records in a graph.

        Uses keyword-based filtering to identify target FDO types.

        Args:
            graph: Dictionary of record_id → PidRecord

        Returns:
            Number of records enriched

        """
        count = 0
        skipped = 0

        for record_id, record in graph.items():
            # Get all keyword attributes
            keyword_attrs = [
                attr[1]
                for attr in record._tuples
                if attr[0] == "21.T11969/793ff5c33c3aeb32907a"
            ]

            # Normalize keywords (handle both single strings and lists)
            normalized_keywords = set()
            for kw in keyword_attrs:
                if isinstance(kw, list):
                    normalized_keywords.update(kw)
                else:
                    normalized_keywords.add(str(kw).lower())

            # Check if any target keyword present
            if normalized_keywords & self.target_keywords:
                self.enrich_record(record)
                count += 1
            else:
                skipped += 1
                logger.debug(f"Skipped {record_id}: no matching keywords")

        logger.info(f"NFDI enrichment: {count} enriched, {skipped} skipped")
        return count


__all__ = ["NFDIEnricher"]
