# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Data models for BAM creep-reference usecase.

This module defines all data structures used throughout the LIS parsing pipeline.
These dataclasses represent:
- File collections grouped by test ID
- Complementary files shared across tests
- Parsed metadata from individual LIS files
- Error information for failed parses

Example:
    >>> from models import LISFileCollection, ParsedTestMetadata
    >>> collection = LISFileCollection(
    ...     test_id="Vh5205_C-78",
    ...     md_tr_checksum="md5:abc123",
    ...     creep_checksum="md5:def456",
    ...     loading_checksum="md5:ghi789"
    ... )
    >>> collection.test_id
    'Vh5205_C-78'

"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class LISFileCollection:
    """Files belonging to one creep test.

    Groups the three required LIS files (MD-TR, Creep, Loading) plus any
    standalone metadata files for a single creep test identified by test ID.

    Attributes:
        test_id: Unique test identifier (e.g., "Vh5205_C-78")
        md_tr_checksum: Checksum for MD-TR file (Vh5205_C-XX-MD-TR.lis)
        creep_checksum: Checksum for Creep file (Vh5205_C-XX-Creep.LIS)
        loading_checksum: Checksum for Loading file (Vh5205_C-XX-Loading.LIS)
        standalone_lis_files: List of checksums for standalone metadata files
        translated_json_checksum: Checksum for MD-TR.translated.json file (optional)

    """

    test_id: str
    md_tr_checksum: str
    creep_checksum: str
    loading_checksum: str
    standalone_lis_files: list[str] = field(default_factory=list)
    translated_json_checksum: str | None = (
        None  # NEW: For <projectID>_<testID>-MD-TR.translated.json
    )


@dataclass
class ComplementaryFiles:
    """Shared files across all tests.

    Contains checksums for complementary LIS files that provide common
    information used by multiple creep tests, such as chemical composition,
    heat treatment procedures, and data acquisition parameters.

    Attributes:
        heat_treatment: Heat treatment procedure file
        chemical_composition_measured: Measured chemical composition
        chemical_composition_nominal: Nominal chemical composition
        data_acquisition: Data acquisition parameters
        data_acquisition_creep: Creep-specific acquisition parameters
        primary_processed_data: Primary and processed data series
        roughness: Surface roughness measurements
        rp02: Rp0.2 yield strength data
        md_tr_common: Common metadata for all tests (optional)

    """

    heat_treatment: str
    chemical_composition_measured: str
    chemical_composition_nominal: str
    data_acquisition: str
    data_acquisition_creep: str
    primary_processed_data: str
    roughness: str
    rp02: str
    md_tr_common: str = ""


@dataclass
class CommonMetadata:
    """Metadata common to all tests from MD-TR_Common-to-all.LIS.

    Extracted from the special MD-TR_Common-to-all.LIS file that contains
    material and standard information applicable to all creep tests in the
    dataset.

    Attributes:
        material_id: Material identifier (e.g., "CMSX-6")
        applicable_standard: Test standard applied (e.g., "DIN EN ISO 204:2019-4")
        form_of_as_manufactured_material: Form of material as manufactured
        geometry_size_as_manufactured: Geometry/size in as-manufactured state
        geometry_size_as_tested: Geometry/size in as-tested state

    """

    material_id: str = ""
    applicable_standard: str = ""
    form_of_as_manufactured_material: Optional[str] = None
    geometry_size_as_manufactured: Optional[str] = None
    geometry_size_as_tested: Optional[str] = None


@dataclass
class ParsedTestMetadata:
    """Extracted metadata from MD-TR.lis file.

    Complete structured metadata extracted from a single creep test's
    MD-TR (Master Data - Technical Report) LIS file.

    Attributes:
        test_id: Unique test identifier
        project: Project name/code
        date_test_start: Test start timestamp
        date_test_end: Test end timestamp
        applicable_standard: Applied test standard
        specified_temperature: Test temperature in °C
        initial_stress: Applied stress in MPa
        material_id: Material identifier
        single_crystal_orientation: Crystal orientation angle in degrees
        percentage_creep_extension: Creep strain as ratio (0-1)
        manufacturing_as_manufactured: Manufacturing process description
        manufacturing_as_tested: As-tested material description
        file_references: List of referenced filenames from "See file" entries

    """

    test_id: str
    project: str
    date_test_start: datetime
    date_test_end: datetime
    applicable_standard: str
    specified_temperature: float
    initial_stress: float
    material_id: str
    single_crystal_orientation: float
    percentage_creep_extension: float = 0.0
    test_duration: str = (
        "PT0S"  # ISO 8601 duration parsed from "Test duration" field in .LIS
    )
    manufacturing_as_manufactured: Optional[str] = None
    manufacturing_as_tested: Optional[str] = None
    file_references: list[str] = field(default_factory=list)


@dataclass
class ParsingError:
    """Represents a parsing error encountered during LIS file processing.

    Captures detailed information about errors that occur during file
    fetching or content parsing, enabling proper error reporting and
    debugging.

    Attributes:
        test_id: Test ID associated with the error
        filename: Filename or checksum where error occurred
        error_type: Type of error (FETCH_ERROR, PARSE_ERROR, etc.)
        message: Detailed error message

    Example:
        >>> error = ParsingError(
        ...     test_id="Vh5205_C-78",
        ...     filename="md5:abc123",
        ...     error_type="FETCH_ERROR",
        ...     message="HTTP 404: File not found"
        ... )
        >>> print(f"{error.test_id}: {error.error_type}")
        Vh5205_C-78: FETCH_ERROR

    """

    test_id: str
    filename: str
    error_type: str
    message: str


__all__ = [
    "LISFileCollection",
    "ComplementaryFiles",
    "CommonMetadata",
    "ParsedTestMetadata",
    "ParsingError",
]
