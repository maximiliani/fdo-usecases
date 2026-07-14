# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Load and group LIS files from Zenodo FDO graph.

This module handles file discovery and organization from a Zenodo FDO graph.
It supports two filename naming conventions for test-specific LIS files:

Pattern A (legacy):
    Vh5205_C-XX-Type.LIS
    Example: Vh5205_C-78-MD-TR.lis, Vh5205_C-78-Creep.LIS

Pattern B (preferred):
    Vh5205_Type_C-XX.LIS
    Example: Vh5205_MD-TR_C-78.LIS, Vh5205_Creep_C-78.LIS

When both patterns exist for the same test ID, Pattern B takes precedence.

The module also identifies:
- Standalone LIS files (Vh5205_C-XX.LIS without type suffix)
- Complementary files shared across all tests
- MD-TR_Common-to-all.LIS for shared metadata

Example:
    >>> loader = FileLoader()
    >>> loader.load_from_zenodo_graph(zenodo_graph)
    >>> collections = loader.group_files_by_test_id()
    >>> "Vh5205_C-78" in collections
    True

"""

import logging
import re
from typing import Optional

from .models import ComplementaryFiles, LISFileCollection, ParsingError

logger = logging.getLogger(__name__)


class FileLoader:
    """Extract and group LIS files from Zenodo graph.

    This class processes a Zenodo FDO graph to discover, categorize, and group
    LIS files by test ID. It handles multiple naming conventions and validates
    that complete file sets exist before creating file collections.

    Attributes:
        _test_id_pattern: Regex for extracting test IDs (C-XX)
        _file_type_pattern: Regex for extracting file types (MD-TR, Creep, Loading)
        _complementary_pattern: Regex for complementary files
        _md_tr_common_pattern: Regex for common-to-all file
        _errors: List of errors encountered during loading
        _file_collections: Grouped file collections by test ID
        _complementary_files: Shared complementary files
        _file_urls: Mapping of checksums to download URLs
        _md_tr_common_checksum: Checksum for common metadata file

    """

    def __init__(self):
        """Initialize file loader with regex patterns."""
        # Flexible pattern for test-specific LIS files handling multiple naming conventions
        self._test_id_pattern = re.compile(r"C-(\d+)", re.IGNORECASE)
        self._file_type_pattern = re.compile(r"(MD-TR|Creep|Loading)", re.IGNORECASE)
        self._complementary_pattern = re.compile(
            r"Vh\d+_Complementary_(.+)\.lis", re.IGNORECASE
        )
        self._md_tr_common_pattern = re.compile(
            r"Vh\d+_MD-TR_Common-to-all\.lis", re.IGNORECASE
        )
        self._errors: list[ParsingError] = []
        self._file_collections: dict[str, LISFileCollection] = {}
        self._complementary_files: Optional[ComplementaryFiles] = None
        self._file_urls: dict[str, str] = {}  # checksum -> download URL
        self._md_tr_common_checksum: Optional[str] = None

    def load_from_zenodo_graph(self, zenodo_graph: dict) -> None:
        """Extract file checksums and URLs from existing Zenodo FDO graph.

        Processes each record in the graph to identify LIS files, extract
        their checksums and download URLs, and group them by test ID.

        The method handles:
        - Test-specific LIS files (MD-TR, Creep, Loading)
        - Standalone LIS files (Vh5205_C-XX.LIS)
        - Complementary files (chemical composition, heat treatment, etc.)
        - Common metadata file (MD-TR_Common-to-all.LIS)

        Args:
            zenodo_graph: Pre-populated graph from ZenodoFDODesign
                Keys are checksums, values are PidRecord objects

        Example:
            >>> loader = FileLoader()
            >>> loader.load_from_zenodo_graph(graph)
            >>> len(loader._file_collections)
            42

        """
        logger.info("Loading file information from Zenodo graph")

        # Group files by test ID
        test_files: dict[str, dict[str, str]] = {}
        standalone_files_map: dict[str, list[str]] = {}
        complementary: dict[str, str] = {}

        for record_id, record in zenodo_graph.items():
            # Convert PidRecord to dict
            record_dict = record.toSimpleJSON()

            # Extract filename from name attribute
            name_attrs = [
                attr["value"]
                for attr in record_dict["record"]
                if attr["key"] == "21.T11969/bd3e9fb9b606d2198c9e"
            ]
            if not name_attrs:
                continue

            filename = name_attrs[0]

            # Skip non-LIS files (JSON translations, etc.)
            if not filename.lower().endswith(".lis"):
                continue

            # Extract download URL from dataObjectLocation attribute
            url_attrs = [
                attr["value"]
                for attr in record_dict["record"]
                if attr["key"] == "21.T11969/479febb2bbe8400da547"
            ]
            download_url = url_attrs[0] if url_attrs else None

            # Check if it's a test-specific LIS file using flexible pattern matching
            test_id_match = self._test_id_pattern.search(filename)
            file_type_match = self._file_type_pattern.search(filename)

            if test_id_match and file_type_match:
                # Extract test ID and file type independently of filename order
                test_id = f"Vh5205_C-{test_id_match.group(1)}"
                file_type = file_type_match.group(1).lower().replace("-", "_")

                if test_id not in test_files:
                    test_files[test_id] = {}

                # Prefer Pattern B (Vh5205_Type_C-XX.LIS) over Pattern A (Vh5205_C-XX-Type.LIS)
                # Pattern B has format: ...Type_C-XX... while Pattern A has ...C-XX-Type...
                # Check if Type comes before C-XX in filename
                type_pos = file_type_match.start()
                test_id_pos = test_id_match.start()
                is_pattern_b = type_pos < test_id_pos  # Type appears before test ID

                if file_type == "md_tr":
                    # Only overwrite if this is Pattern B or if no file exists yet
                    if "md_tr" not in test_files[test_id] or is_pattern_b:
                        test_files[test_id]["md_tr"] = record_id
                        if download_url:
                            self._file_urls[record_id] = download_url
                elif file_type == "creep":
                    if "creep" not in test_files[test_id] or is_pattern_b:
                        test_files[test_id]["creep"] = record_id
                        if download_url:
                            self._file_urls[record_id] = download_url
                elif file_type == "loading":
                    if "loading" not in test_files[test_id] or is_pattern_b:
                        test_files[test_id]["loading"] = record_id
                        if download_url:
                            self._file_urls[record_id] = download_url

            # Check for standalone LIS files: Vh5205_C-XX.LIS (no MD-TR/Creep/Loading suffix)
            elif test_id_match and not file_type_match:
                # This is a standalone LIS file like Vh5205_C-85.LIS
                test_id = f"Vh5205_C-{test_id_match.group(1)}"

                # Skip if it matches complementary or common-to-all patterns
                if not self._complementary_pattern.match(
                    filename
                ) and not self._md_tr_common_pattern.match(filename):
                    if test_id not in test_files:
                        test_files[test_id] = {}

                    if test_id not in standalone_files_map:
                        standalone_files_map[test_id] = []
                    standalone_files_map[test_id].append(record_id)
                    if download_url:
                        self._file_urls[record_id] = download_url
                    logger.debug(
                        f"Found standalone LIS file {filename} for test {test_id}"
                    )

            # Check if it's a complementary file
            comp_match = self._complementary_pattern.match(filename)
            if comp_match:
                comp_type = comp_match.group(1).lower()
                if "heat-treatment" in comp_type or "heat_treatment" in comp_type:
                    complementary["heat_treatment"] = record_id
                    if download_url:
                        self._file_urls[record_id] = download_url
                elif "ch.-comp.-measured" in comp_type or "chemical" in comp_type:
                    complementary["chemical_measured"] = record_id
                    if download_url:
                        self._file_urls[record_id] = download_url
                elif "ch.-comp.-nominal" in comp_type:
                    complementary["chemical_nominal"] = record_id
                    if download_url:
                        self._file_urls[record_id] = download_url
                elif "data-acquisition-creep" in comp_type:
                    complementary["data_acquisition_creep"] = record_id
                    if download_url:
                        self._file_urls[record_id] = download_url
                elif "data-acquisition" in comp_type:
                    complementary["data_acquisition"] = record_id
                    if download_url:
                        self._file_urls[record_id] = download_url
                elif "primary" in comp_type:
                    complementary["primary_processed"] = record_id
                    if download_url:
                        self._file_urls[record_id] = download_url
                elif "roughness" in comp_type:
                    complementary["roughness"] = record_id
                    if download_url:
                        self._file_urls[record_id] = download_url
                elif "rp0.2" in comp_type or "rp02" in comp_type:
                    complementary["rp02"] = record_id
                    if download_url:
                        self._file_urls[record_id] = download_url

            # Check if it's MD-TR_Common-to-all.LIS
            if self._md_tr_common_pattern.match(filename):
                self._md_tr_common_checksum = record_id
                if download_url:
                    self._file_urls[record_id] = download_url
                    logger.debug(f"Found MD-TR_Common-to-all.LIS: {record_id}")

        # Create file collections (only for complete sets)
        for test_id, files in test_files.items():
            if all(k in files for k in ["md_tr", "creep", "loading"]):
                standalone_files = standalone_files_map.get(test_id, [])
                self._file_collections[test_id] = LISFileCollection(
                    test_id=test_id,
                    md_tr_checksum=files["md_tr"],
                    creep_checksum=files["creep"],
                    loading_checksum=files["loading"],
                    standalone_lis_files=standalone_files,
                )
            else:
                logger.warning(f"Incomplete file set for {test_id}, skipping")
                self._errors.append(
                    ParsingError(
                        test_id=test_id,
                        filename="multiple",
                        error_type="INCOMPLETE_FILES",
                        message=f"Missing files: {set(['md_tr', 'creep', 'loading']) - set(files.keys())}",
                    )
                )

        # Create complementary files object
        if complementary:
            self._complementary_files = ComplementaryFiles(
                heat_treatment=complementary.get("heat_treatment", ""),
                chemical_composition_measured=complementary.get(
                    "chemical_measured", ""
                ),
                chemical_composition_nominal=complementary.get("chemical_nominal", ""),
                data_acquisition=complementary.get("data_acquisition", ""),
                data_acquisition_creep=complementary.get("data_acquisition_creep", ""),
                primary_processed_data=complementary.get("primary_processed", ""),
                roughness=complementary.get("roughness", ""),
                rp02=complementary.get("rp02", ""),
            )

        logger.info(f"Found {len(self._file_collections)} test file collections")
        logger.info(f"Found {len(self._file_urls)} file URLs for downloading")
        if self._md_tr_common_checksum:
            logger.info(f"Found MD-TR_Common-to-all.LIS: {self._md_tr_common_checksum}")

    def group_files_by_test_id(self) -> dict[str, LISFileCollection]:
        """Return grouped file collections by test ID.

        Returns:
            Dictionary mapping test IDs to LISFileCollection objects

        Example:
            >>> loader = FileLoader()
            >>> loader.load_from_zenodo_graph(graph)
            >>> collections = loader.group_files_by_test_id()
            >>> isinstance(collections["Vh5205_C-78"], LISFileCollection)
            True

        """
        return self._file_collections

    def find_complementary_files(self) -> ComplementaryFiles:
        """Identify complementary files by filename matching.

        Returns:
            ComplementaryFiles object containing all shared file checksums

        Raises:
            ValueError: If load_from_zenodo_graph hasn't been called yet

        Example:
            >>> loader = FileLoader()
            >>> loader.load_from_zenodo_graph(graph)
            >>> comp = loader.find_complementary_files()
            >>> comp.heat_treatment
            'md5:abc123'

        """
        if not self._complementary_files:
            raise ValueError(
                "No complementary files found. Call load_from_zenodo_graph first."
            )
        return self._complementary_files

    @property
    def file_urls(self) -> dict[str, str]:
        """Return mapping of checksums to download URLs.

        Returns:
            Dictionary mapping file checksums to Zenodo download URLs

        """
        return self._file_urls

    @property
    def md_tr_common_checksum(self) -> Optional[str]:
        """Return checksum for MD-TR_Common-to-all.LIS file.

        Returns:
            Checksum string if found, None otherwise

        """
        return self._md_tr_common_checksum

    @property
    def errors(self) -> list[ParsingError]:
        """Return list of errors encountered during loading.

        Returns:
            List of ParsingError objects

        """
        return self._errors


__all__ = ["FileLoader"]
