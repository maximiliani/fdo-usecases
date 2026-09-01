# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Facade for LIS file parsing - coordinates all components.

This is the main entry point for LIS parsing in the BAM creep-reference usecase.
It composes specialized components and provides a unified API for consumers.

Architecture:
    LISParser (facade)
    ├── FileLoader (discovers and groups files)
    ├── HTTPClient (fetches content with caching)
    ├── LISContentParser (parses tab-separated content)
    ├── ImageExtractor (finds SEM and preview images)
    └── DatasetMetadataExtractor (extracts creators/keywords)

Example:
    >>> async with LISParser() as parser:
    ...     parser.load_from_zenodo_graph(graph)
    ...     metadata = await parser.parse_md_tr_file(checksum)
    ...     print(f"Material: {metadata.material_id}")

"""

import logging
from typing import Optional

from .dataset_metadata import DatasetMetadataExtractor
from .file_loader import FileLoader
from .http_client import HTTPClient
from .image_extractor import ImageExtractor
from .models import (
    CommonMetadata,
    ComplementaryFiles,
    LISFileCollection,
    ParsedTestMetadata,
    ParsingError,
)
from .parser import LISContentParser

logger = logging.getLogger(__name__)


class LISParser:
    """Orchestrate LIS file parsing through component composition.

    This facade class provides a unified interface for parsing LIS files
    from the BAM creep-reference dataset. It delegates to specialized
    components for each aspect of the parsing pipeline.

    The parser works in two phases:
    1. Load file information from Zenodo FDO graph (checksums, URLs)
    2. Fetch and parse LIS file content via HTTP

    Attributes:
        _file_loader: Component for discovering and grouping files
        _http_client: Component for fetching file content
        _content_parser: Component for parsing LIS content
        _image_extractor: Component for finding images
        _metadata_extractor: Component for extracting dataset metadata
        _common_metadata: Cached common metadata from MD-TR_Common-to-all.LIS

    Example:
        >>> async with LISParser() as parser:
        ...     parser.load_from_zenodo_graph(zenodo_graph)
        ...     collections = parser.group_files_by_test_id()
        ...     for test_id, collection in collections.items():
        ...         metadata = await parser.parse_md_tr_file(collection.md_tr_checksum)
        ...         print(f"{test_id}: {metadata.material_id}")

    """

    def __init__(self):
        """Initialize LIS parser with all component instances."""
        self._file_loader = FileLoader()
        self._http_client = HTTPClient()
        self._content_parser = LISContentParser()
        self._image_extractor = ImageExtractor()
        self._metadata_extractor = DatasetMetadataExtractor()
        self._common_metadata: Optional[CommonMetadata] = None

    async def __aenter__(self):
        """Async context manager entry - initialize HTTP client."""
        await self._http_client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close HTTP client session."""
        await self._http_client.__aexit__(exc_type, exc_val, exc_tb)

    def load_from_zenodo_graph(self, zenodo_graph: dict) -> None:
        """Extract file checksums and URLs from existing Zenodo FDO graph.

        Delegates to FileLoader component to process the graph and identify
        all LIS files, grouping them by test ID.

        Args:
            zenodo_graph: Pre-populated graph from ZenodoFDODesign
                Keys are checksums, values are PidRecord objects

        Example:
            >>> parser = LISParser()
            >>> parser.load_from_zenodo_graph(graph)
            >>> len(parser.group_files_by_test_id())
            42

        """
        self._file_loader.load_from_zenodo_graph(zenodo_graph)
        # Pass file URLs to HTTP client for fetching
        self._http_client.set_file_urls(self._file_loader.file_urls)

    async def _parse_common_metadata(self) -> Optional[CommonMetadata]:
        """Parse MD-TR_Common-to-all.LIS for shared metadata.

        Fetches and parses the special common-to-all file that contains
        material and standard information applicable to all tests.

        Returns:
            CommonMetadata object if successful, None if file not found or parse fails

        """
        md_tr_common_checksum = self._file_loader.md_tr_common_checksum
        if not md_tr_common_checksum:
            return None

        content = await self._http_client._fetch_file_content(md_tr_common_checksum)
        if not content:
            logger.warning("Failed to fetch MD-TR_Common-to-all.LIS")
            return None

        # Parse with latin-1 encoding (handles special characters in this file)
        metadata = CommonMetadata()

        lines = content.split("\n")
        for line in lines:
            cols = line.split("\t")
            if len(cols) >= 7:
                entry = cols[1].strip().lower()
                information = cols[6].strip().rstrip("\r\n")

                if "material identifier" in entry and information:
                    metadata.material_id = information
                elif (
                    "test standard" in entry and "applied" not in entry and information
                ):
                    metadata.applicable_standard = information
                elif "form of as-manufactured material" in entry and information:
                    metadata.form_of_as_manufactured_material = information
                elif "geometry/size as-manufactured material" in entry and information:
                    metadata.geometry_size_as_manufactured = information
                elif "geometry/size as-tested material" in entry and information:
                    metadata.geometry_size_as_tested = information

        if metadata.material_id:
            logger.info(
                f"Parsed common metadata: Material={metadata.material_id}, Standard={metadata.applicable_standard}"
            )

        return metadata

    def group_files_by_test_id(self) -> dict[str, LISFileCollection]:
        """Return grouped file collections by test ID.

        Returns:
            Dictionary mapping test IDs to LISFileCollection objects

        Example:
            >>> parser = LISParser()
            >>> parser.load_from_zenodo_graph(graph)
            >>> collections = parser.group_files_by_test_id()
            >>> "Vh5205_C-78" in collections
            True

        """
        return self._file_loader.group_files_by_test_id()

    def find_complementary_files(self) -> ComplementaryFiles:
        """Identify complementary files by filename matching.

        Returns:
            ComplementaryFiles object containing all shared file checksums

        Raises:
            ValueError: If load_from_zenodo_graph hasn't been called yet

        """
        return self._file_loader.find_complementary_files()

    async def get_common_metadata(self) -> Optional[CommonMetadata]:
        """Get parsed common metadata from MD-TR_Common-to-all.LIS.

        Returns:
            CommonMetadata object if available, None otherwise

        """
        if self._common_metadata is None:
            self._common_metadata = await self._parse_common_metadata()
        return self._common_metadata

    async def parse_md_tr_file(self, checksum: str) -> Optional[ParsedTestMetadata]:
        """Parse MD-TR.lis file content.

        Fetches file from Zenodo and parses tab-separated content to extract
        structured test metadata.

        Args:
            checksum: File checksum to fetch

        Returns:
            ParsedTestMetadata if successful, None on failure

        Example:
            >>> async with LISParser() as parser:
            ...     parser.load_from_zenodo_graph(graph)
            ...     collection = parser.group_files_by_test_id()["Vh5205_C-78"]
            ...     metadata = await parser.parse_md_tr_file(collection.md_tr_checksum)
            ...     print(f"Temperature: {metadata.specified_temperature}°C")

        """
        try:
            # Extract test ID from checksum by searching collections
            test_id = "unknown"
            for tid, collection in self._file_loader._file_collections.items():
                if collection.md_tr_checksum == checksum:
                    test_id = tid
                    break

            logger.info(f"Parsing MD-TR file for {test_id} (checksum: {checksum})")

            # Fetch file content
            content = await self._http_client._fetch_file_content(checksum)
            if not content:
                logger.error(
                    f"Failed to fetch content for {test_id}: checksum={checksum}"
                )
                self._file_loader._errors.append(
                    ParsingError(
                        test_id=test_id,
                        filename=checksum,
                        error_type="FETCH_ERROR",
                        message="Failed to download file from Zenodo (URL lookup failed)",
                    )
                )
                return None

            # Parse content
            logger.debug(f"Parsing {len(content)} bytes for {test_id}")
            metadata = self._content_parser._parse_lis_content(content, test_id)
            if not metadata:
                logger.error(f"Failed to parse LIS content for {test_id}")
                self._file_loader._errors.append(
                    ParsingError(
                        test_id=test_id,
                        filename=checksum,
                        error_type="PARSE_ERROR",
                        message="Failed to parse LIS content",
                    )
                )
                return None

            logger.info(
                f"Successfully parsed {test_id}: material={metadata.material_id}, temp={metadata.specified_temperature}°C, stress={metadata.initial_stress}MPa"
            )
            return metadata

        except Exception as e:
            logger.exception(
                f"Failed to parse MD-TR file {checksum}: {type(e).__name__}: {e}"
            )
            self._file_loader._errors.append(
                ParsingError(
                    test_id="unknown",
                    filename=checksum,
                    error_type="EXCEPTION",
                    message=f"{type(e).__name__}: {str(e)}",
                )
            )
            return None

    def extract_images_from_graph(
        self, zenodo_graph: dict
    ) -> tuple[list[str], list[str]]:
        """Extract SEM and preview image information from Zenodo graph.

        Delegates to ImageExtractor component to identify image files.

        Args:
            zenodo_graph: Pre-populated graph from ZenodoFDODesign

        Returns:
            Tuple of (sem_checksums, preview_urls)

        """
        return self._image_extractor.extract_images_from_graph(zenodo_graph)

    def get_creators_from_dataset(self, zenodo_graph: dict) -> list[str]:
        """Extract creator ORCIDs from Dataset FDO.

        Delegates to DatasetMetadataExtractor component.

        Args:
            zenodo_graph: Pre-populated graph

        Returns:
            List of creator ORCID URLs

        """
        return self._metadata_extractor.get_creators_from_dataset(zenodo_graph)

    def get_creator_affiliations_from_dataset(self, zenodo_graph: dict) -> list[str]:
        """Extract ROR IDs from Dataset FDO.

        Delegates to DatasetMetadataExtractor component.

        Args:
            zenodo_graph: Pre-populated graph

        Returns:
            List of ROR ID URLs

        """
        return self._metadata_extractor.get_creator_affiliations_from_dataset(
            zenodo_graph
        )

    def get_keywords_from_dataset(self, zenodo_graph: dict) -> list[str]:
        """Extract keywords from Dataset FDO.

        Delegates to DatasetMetadataExtractor component.

        Args:
            zenodo_graph: Pre-populated graph

        Returns:
            List of keywords

        """
        return self._metadata_extractor.get_keywords_from_dataset(zenodo_graph)

    def get_funders_from_dataset(
        self,
        zenodo_graph: dict,
        dataset_dois: list[str] | None = None,
    ) -> list[str]:
        """Extract fundedBy grant PIDs from Dataset FDOs.

        Delegates to DatasetMetadataExtractor component so experiments can
        inherit the funding relationship provided in the dataset FDOs.

        Args:
            zenodo_graph: Pre-populated graph
            dataset_dois: Optional list of record IDs to restrict the scan to

        Returns:
            List of unique grant PIDs that fund the datasets

        """
        return self._metadata_extractor.get_funders_from_dataset(
            zenodo_graph, dataset_dois
        )

    def extract_keywords(self, metadata: ParsedTestMetadata) -> list[str]:
        """Extract domain keywords from metadata.

        Delegates to DatasetMetadataExtractor component.

        Args:
            metadata: Parsed test metadata

        Returns:
            List of domain-specific keywords

        """
        return self._metadata_extractor.extract_keywords(metadata)

    @property
    def errors(self) -> list[ParsingError]:
        """Get list of parsing errors.

        Returns:
            List of ParsingError objects encountered during processing

        """
        return self._file_loader.errors

    def report_errors(self) -> None:
        """Log all parsing errors at ERROR level."""
        if self._file_loader.errors:
            logger.error(
                f"LIS parsing encountered {len(self._file_loader.errors)} error(s):"
            )
            for error in self._file_loader.errors:
                logger.error(
                    f"  [{error.error_type}] {error.test_id}/{error.filename}: {error.message}"
                )


__all__ = ["LISParser"]
