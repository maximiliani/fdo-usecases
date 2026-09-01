# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Extract dataset-level metadata (creators, keywords, affiliations).

This module extracts metadata from Dataset FDOs in the Zenodo graph using
specific attribute keys defined by the FDO ontology:

Creator ORCIDs:
    Key: 21.T11969/7c67083a5d218e544063
    Format: Full ORCID URL (https://orcid.org/XXXX-XXXX-XXXX-XXXX)

Affiliations (ROR IDs):
    Key: 21.T11969/ea9f6b3d78c6608fe801
    Format: Full ROR URL (https://ror.org/XXXXX)

Keywords:
    Key: 21.T11969/793ff5c33c3aeb32907a
    Format: Free-text domain-specific terms

The extracted metadata is used to enrich both Material and CreepExperiment FDOs
with proper attribution and discoverability information.

Example:
    >>> extractor = DatasetMetadataExtractor()
    >>> creators = extractor.get_creators_from_dataset(graph)
    >>> len(creators) > 0
    True

"""

import logging

from .models import ParsedTestMetadata

logger = logging.getLogger(__name__)


class DatasetMetadataExtractor:
    """Extract metadata from Dataset FDO.

    This class scans a Zenodo FDO graph to extract creator, affiliation,
    and keyword information from Dataset records. It deduplicates values
    and returns clean lists suitable for use in FDO creation.

    Attributes:
        CREATOR_KEY: Attribute key for creator ORCIDs
        AFFILIATION_KEY: Attribute key for ROR affiliations
        KEYWORD_KEY: Attribute key for keywords

    Example:
        >>> extractor = DatasetMetadataExtractor()
        >>> creators = extractor.get_creators_from_dataset(graph)
        >>> print(f"Found {len(creators)} creators")
        Found 5 creators

    """

    # Attribute keys for Zenodo FDO graph
    CREATOR_KEY = "21.T11969/7c67083a5d218e544063"
    AFFILIATION_KEY = "21.T11969/ea9f6b3d78c6608fe801"
    KEYWORD_KEY = "21.T11969/793ff5c33c3aeb32907a"
    FUNDED_BY_KEY = "21.T11969/28ca0d5c50678433e5a8"

    def get_creators_from_dataset(self, zenodo_graph: dict) -> list[str]:
        """Extract creator ORCIDs from Dataset FDO.

        Scans all records in the graph for creator attributes and returns
        a deduplicated list of ORCID URLs.

        Args:
            zenodo_graph: Pre-populated graph from ZenodoFDODesign
                Keys are checksums, values are PidRecord objects

        Returns:
            List of unique creator ORCID URLs
            Format: ["https://orcid.org/XXXX-XXXX-XXXX-XXXX", ...]

        Example:
            >>> extractor = DatasetMetadataExtractor()
            >>> creators = extractor.get_creators_from_dataset(graph)
            >>> "https://orcid.org/0000-0003-0012-2414" in creators
            True

        """
        creators: list[str] = []
        for _record_id, record in zenodo_graph.items():
            # Convert PidRecord to dict
            record_dict = record.toSimpleJSON()
            # Look for creator attributes
            creator_attrs = [
                attr["value"]
                for attr in record_dict["record"]
                if attr["key"] == self.CREATOR_KEY
            ]
            creators.extend(creator_attrs)

        return list(set(creators))  # Deduplicate

    def get_creator_affiliations_from_dataset(self, zenodo_graph: dict) -> list[str]:
        """Extract ROR IDs from Dataset FDO.

        Scans all records in the graph for creator affiliation attributes
        and returns a deduplicated list of ROR URLs.

        Args:
            zenodo_graph: Pre-populated graph from ZenodoFDODesign
                Keys are checksums, values are PidRecord objects

        Returns:
            List of unique ROR affiliation URLs
            Format: ["https://ror.org/XXXXX", ...]

        Example:
            >>> extractor = DatasetMetadataExtractor()
            >>> affiliations = extractor.get_creator_affiliations_from_dataset(graph)
            >>> len(affiliations) > 0
            True

        """
        affiliations: list[str] = []
        for _record_id, record in zenodo_graph.items():
            # Convert PidRecord to dict
            record_dict = record.toSimpleJSON()
            # Look for creatorAffiliation attributes
            aff_attrs = [
                attr["value"]
                for attr in record_dict["record"]
                if attr["key"] == self.AFFILIATION_KEY
            ]
            affiliations.extend(aff_attrs)

        return list(set(affiliations))  # Deduplicate

    def get_keywords_from_dataset(self, zenodo_graph: dict) -> list[str]:
        """Extract keywords from Dataset FDO.

        Scans all records in the graph for keyword attributes and returns
        a deduplicated list of domain-specific terms.

        Args:
            zenodo_graph: Pre-populated graph from ZenodoFDODesign
                Keys are checksums, values are PidRecord objects

        Returns:
            List of unique keywords

        Example:
            >>> extractor = DatasetMetadataExtractor()
            >>> keywords = extractor.get_keywords_from_dataset(graph)
            >>> "creep test" in keywords
            True

        """
        keywords: list[str] = []
        for _record_id, record in zenodo_graph.items():
            # Convert PidRecord to dict
            record_dict = record.toSimpleJSON()
            # Look for keyword attributes
            kw_attrs = [
                attr["value"]
                for attr in record_dict["record"]
                if attr["key"] == self.KEYWORD_KEY
            ]
            keywords.extend(kw_attrs)

        return list(set(keywords))  # Deduplicate

    def get_funders_from_dataset(
        self,
        zenodo_graph: dict,
        dataset_dois: list[str] | None = None,
    ) -> list[str]:
        """Extract fundedBy grant PIDs from Dataset FDOs.

        Reads the ``fundedBy`` attributes off the Dataset FDO records so that
        dependent research outputs (e.g. creep experiments) can inherit the
        funding information already provided in the dataset FDOs.

        Args:
            zenodo_graph: Pre-populated graph from ZenodoFDODesign.
                Keys are record IDs, values are PidRecord objects.
            dataset_dois: Optional list of record IDs to restrict the scan to.
                When omitted, all dataset records (IDs containing "zenodo")
                in the graph are scanned.

        Returns:
            List of unique grant PIDs (placeholder IDs like
            ``PID_grant:<funder>::<code>``) that fund the datasets.

        Example:
            >>> extractor = DatasetMetadataExtractor()
            >>> funders = extractor.get_funders_from_dataset(graph)
            >>> "PID_grant:https://ror.org/018mejw64::460247524" in funders
            True

        """
        funders: list[str] = []
        for record_id, record in zenodo_graph.items():
            if dataset_dois is not None:
                if record_id not in dataset_dois:
                    continue
            elif "zenodo" not in record_id:
                continue

            # Convert PidRecord to dict
            record_dict = record.toSimpleJSON()
            # Look for fundedBy attributes
            funded_by_attrs = [
                attr["value"]
                for attr in record_dict["record"]
                if attr["key"] == self.FUNDED_BY_KEY
            ]
            funders.extend(funded_by_attrs)

        return list(set(funders))  # Deduplicate

    def extract_keywords(self, metadata: ParsedTestMetadata) -> list[str]:
        """Extract domain keywords from parsed test metadata.

        Generates domain-specific keywords based on material ID, test standard,
        and other metadata fields. These keywords complement the dataset-level
        keywords with test-specific terms.

        Args:
            metadata: Parsed test metadata containing material and standard info

        Returns:
            List of domain-specific keywords derived from metadata

        Example:
            >>> extractor = DatasetMetadataExtractor()
            >>> metadata = ParsedTestMetadata(
            ...     test_id="Vh5205_C-78",
            ...     material_id="CMSX-6",
            ...     applicable_standard="DIN EN ISO 204:2019-4",
            ...     project="Vh 5205",
            ...     date_test_start=datetime.now(),
            ...     date_test_end=datetime.now(),
            ...     specified_temperature=980.0,
            ...     initial_stress=230.0,
            ...     single_crystal_orientation=6.9
            ... )
            >>> keywords = extractor.extract_keywords(metadata)
            >>> "CMSX-6" in keywords
            True

        """
        keywords: list[str] = []

        # From material ID
        if metadata.material_id:
            keywords.append(metadata.material_id)

        # From test standard
        if metadata.applicable_standard:
            # Extract just the standard number (before colon if present)
            std_part = metadata.applicable_standard.split(":")[0]
            keywords.append(std_part)

        # From test type (if available)
        # Could add more extraction logic here based on other fields

        return list(set(keywords))  # Deduplicate


__all__ = ["DatasetMetadataExtractor"]
