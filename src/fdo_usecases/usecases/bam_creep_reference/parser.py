# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Parse LIS file content (tab-separated format).

This module handles the core parsing logic for tab-separated LIS files
from the BAM creep-reference dataset. It extracts structured metadata
including test parameters, material properties, and file references.

The parser supports multiple date formats commonly found in LIS files:
- ISO format: "2023-02-08 09:06:15"
- US short format: "8.2.23 9:06 AM"
- European format: "08.02.2023 09:06"

LIS File Format:
    Columns (tab-separated):
    CATEGORIZATION | ENTRY | ADDITIONAL_INFO | SYMBOL | UNIT | REQUIREMENT | INFORMATION | COMMON_TO_ALL

    Example row:
    Metadata --> Test info --> Test parameters | Specified temperature | T | °C | Mandatory | 980 | *

Example:
    >>> parser = LISContentParser()
    >>> metadata = parser._parse_lis_content(content, "Vh5205_C-78")
    >>> metadata.specified_temperature
    980.0

"""

import logging
import re
from datetime import datetime
from typing import Optional

from ...utils.duration import to_iso8601_duration
from .models import ParsedTestMetadata

logger = logging.getLogger(__name__)


class LISContentParser:
    """Parse LIS file content and extract structured metadata.

    This class implements the core parsing logic for extracting metadata
    from tab-separated LIS files. It handles hierarchical categorization,
    multi-format date parsing, and file reference extraction.

    Attributes:
        DATE_FORMATS: List of date format strings to try during parsing
        FILE_REF_PATTERN: Compiled regex for extracting file references

    """

    # Supported date formats in order of preference
    DATE_FORMATS = [
        "%Y-%m-%d %H:%M:%S",  # 2023-02-08 09:06:15
        "%d.%m.%y %I:%M %p",  # 8.2.23 9:06 AM
        "%d.%m.%y %H:%M",  # 8.2.23 09:06
        "%d.%m.%Y %H:%M:%S",  # 08.02.2023 09:06:15
        "%d.%m.%Y %H:%M",  # 08.02.2023 09:06
        "%d.%m.%y %I:%M%p",  # 8.2.23 9:06AM (no space)
    ]

    # Pattern for extracting file references: See file "filename.ext"
    FILE_REF_PATTERN = re.compile(r'See file "([^"]+)"', re.IGNORECASE)

    def _parse_date(
        self,
        date_str: str,
        line_num: int,
        parse_errors: list[str],
        test_id: str,
    ) -> Optional[datetime]:
        """Parse date string with multiple format support.

        Attempts to parse a date string using multiple predefined formats
        commonly found in LIS files. Falls back gracefully if no format matches.

        Args:
            date_str: Date string to parse
            line_num: Line number in source file (for error reporting)
            parse_errors: List to append error messages to
            test_id: Test identifier for logging context

        Returns:
            datetime object if successful, None if all formats fail

        Example:
            >>> parser = LISContentParser()
            >>> errors = []
            >>> result = parser._parse_date("2023-02-08 09:06:15", 5, errors, "Vh5205_C-78")
            >>> result.year
            2023

        """
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # All formats failed
        parse_errors.append(f"Line {line_num}: Invalid date format '{date_str}'")
        logger.warning(
            f"{test_id}: Could not parse date '{date_str}' with any known format"
        )
        return None

    def _parse_lis_content(
        self, content: str, test_id: str
    ) -> Optional[ParsedTestMetadata]:
        """Parse LIS file content (tab-separated format).

        Extracts structured metadata from raw LIS file content by processing
        each line and navigating the hierarchical categorization structure.

        The parser looks for specific fields in the INFORMATION column (column 7)
        based on matching CATEGORIZATION and ENTRY patterns.

        Args:
            content: Raw LIS file content (tab-separated lines)
            test_id: Test identifier for error reporting and logging

        Returns:
            ParsedTestMetadata object if parsing successful,
            None if required fields are missing

        Raises:
            No exceptions raised - errors are logged and None returned

        Example:
            >>> parser = LISContentParser()
            >>> # Parse tab-separated LIS content to extract metadata
            >>> metadata = parser._parse_lis_content(content, "Vh5205_C-78")

        """
        metadata: dict = {
            "test_id": test_id,
            "project": "",
            "date_test_start": None,
            "date_test_end": None,
            "applicable_standard": "",
            "specified_temperature": 0.0,
            "initial_stress": 0.0,
            "material_id": "",
            "single_crystal_orientation": 0.0,
            "percentage_creep_extension": 0.0,
            "test_duration": "PT0S",
            "manufacturing_as_manufactured": None,
            "manufacturing_as_tested": None,
            "file_references": [],
        }

        lines = content.split("\n")
        parse_errors: list[str] = []

        for line_num, line in enumerate(lines, 1):
            cols = line.split("\t")
            if len(cols) < 7:
                continue

            categorization = cols[0].strip()
            entry = cols[1].strip()
            unit = cols[4].strip()
            # Strip whitespace including Windows line endings (\r\n)
            information = cols[6].strip().rstrip("\r\n")

            # Skip empty or N/A values
            if not information or information.lower() in [
                "not applicable",
                "n/a",
                "",
                "-",
            ]:
                continue

            try:
                # Navigate hierarchy and extract values
                if "Metadata --> Test info --> Test job details" in categorization:
                    if "Date of test start" in entry:
                        metadata["date_test_start"] = self._parse_date(
                            information, line_num, parse_errors, test_id
                        )
                    elif "Date of test end" in entry:
                        metadata["date_test_end"] = self._parse_date(
                            information, line_num, parse_errors, test_id
                        )
                    elif "Project" in entry:
                        metadata["project"] = information
                    elif "Test ID" in entry:
                        # Override test_id if different
                        if information and information != test_id:
                            metadata["test_id"] = information

                elif "Metadata --> Test info --> Test parameters" in categorization:
                    if "Test standard" in entry and "applied" not in entry.lower():
                        metadata["applicable_standard"] = information
                    elif "Specified temperature" in entry:
                        try:
                            metadata["specified_temperature"] = float(information)
                        except ValueError:
                            parse_errors.append(
                                f"Line {line_num}: Invalid temperature value"
                            )
                    elif "Initial stress" in entry:
                        try:
                            metadata["initial_stress"] = float(information)
                        except ValueError:
                            parse_errors.append(
                                f"Line {line_num}: Invalid stress value"
                            )
                    elif "Percentage creep extension" in entry:
                        try:
                            # Convert percentage to ratio (e.g., "1.5%" -> 0.015)
                            value = information.replace("%", "").strip()
                            metadata["percentage_creep_extension"] = (
                                float(value) / 100.0
                            )
                        except ValueError:
                            parse_errors.append(
                                f"Line {line_num}: Invalid percentage value"
                            )

                elif "Metadata --> Material history and condition" in categorization:
                    if "Material Identifier" in entry:
                        metadata["material_id"] = information
                    elif (
                        "Single crystal orientation" in entry
                        and "Determination method" not in categorization
                    ):
                        try:
                            # Handle various formats: "6.9°", "6.9", "<001>, 6.9 deg"
                            clean_value = re.sub(r"[°]", "", information).strip()

                            # Check if this looks like actual orientation data
                            match = re.match(r"(?:<[\d]+>)?\s*([\d.]+)", clean_value)
                            if (
                                match and len(clean_value) < 50
                            ):  # Real data is usually short
                                metadata["single_crystal_orientation"] = float(
                                    match.group(1)
                                )
                            else:
                                # It's descriptive text, not actual orientation value
                                logger.debug(
                                    f"{test_id}: Skipping descriptive orientation text: {information[:80]}..."
                                )
                                continue  # Skip this line, don't treat as error
                        except (ValueError, AttributeError) as e:
                            logger.warning(
                                f"{test_id}: Line {line_num}: Cannot parse orientation '{information}': {e}"
                            )
                            parse_errors.append(
                                f"Line {line_num}: Invalid orientation value '{information}' - {str(e)}"
                            )
                    elif (
                        "Manufacturing process description as-manufactured material"
                        in entry
                    ):
                        metadata["manufacturing_as_manufactured"] = information
                    elif (
                        "Manufacturing process description as-tested material" in entry
                    ):
                        metadata["manufacturing_as_tested"] = information
                elif (
                    "Primary data --> Test result --> Values recorded during test run"
                    in categorization
                ):
                    if "Test duration" in entry:
                        try:
                            metadata["test_duration"] = to_iso8601_duration(
                                float(information), unit
                            )
                        except ValueError as e:
                            parse_errors.append(
                                f"Line {line_num}: Invalid test duration "
                                f"{information!r} {unit!r}: {e}"
                            )

                # Extract file references from any field
                file_refs = self.FILE_REF_PATTERN.findall(information)
                metadata["file_references"].extend(file_refs)

            except Exception as e:
                parse_errors.append(f"Line {line_num}: {str(e)}")
                continue

        # Log parse errors as warnings
        if parse_errors:
            for error in parse_errors[:5]:  # Limit to first 5 errors
                logger.warning(f"{test_id}: {error}")
            if len(parse_errors) > 5:
                logger.warning(
                    f"{test_id}: ... and {len(parse_errors) - 5} more parse errors"
                )

        # Validate required fields
        if not metadata["date_test_start"] or not metadata["date_test_end"]:
            logger.warning(f"Missing dates for {test_id}")
            return None

        # Note: applicable_standard and material_id may come from MD-TR_Common-to-all.LIS
        # so we don't fail here if they're missing from individual test files
        if not metadata["material_id"]:
            logger.debug(f"No material ID in {test_id} (may be in Common-to-all file)")

        if not metadata["applicable_standard"]:
            logger.debug(
                f"No test standard in {test_id} (may be in Common-to-all file)"
            )

        # Remove duplicates from file references
        metadata["file_references"] = list(set(metadata["file_references"]))

        return ParsedTestMetadata(**metadata)


__all__ = ["LISContentParser"]
