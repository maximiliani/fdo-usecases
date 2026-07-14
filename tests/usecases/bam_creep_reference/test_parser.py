# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for LIS content parser."""

from datetime import datetime

import pytest

from fdo_usecases.usecases.bam_creep_reference.parser import LISContentParser


class TestLISContentParser:
    """Test LIS content parsing logic."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return LISContentParser()

    def test_parse_complete_lis_content(
        self, parser, sample_lis_content, sample_parsed_metadata
    ):
        """Test parsing complete LIS content with all required fields."""
        metadata = parser._parse_lis_content(sample_lis_content, "Vh5205_C-78")

        assert metadata is not None
        assert metadata.test_id == "Vh5205_C-78"
        assert metadata.project == "Vh 5205"
        assert metadata.date_test_start == datetime(2023, 2, 8, 9, 6, 15)
        assert metadata.date_test_end == datetime(2023, 2, 11, 15, 48, 15)
        assert metadata.applicable_standard == "DIN EN ISO 204:2019-4"
        assert metadata.specified_temperature == 980.0
        assert metadata.initial_stress == 230.0
        assert abs(metadata.percentage_creep_extension - 0.015) < 0.001
        assert metadata.material_id == "CMSX-6"
        assert metadata.single_crystal_orientation == 6.9
        assert metadata.manufacturing_as_manufactured == "Vacuum Induction Refined"
        assert metadata.manufacturing_as_tested == "Single Crystal Investment Cast"

    def test_extract_file_references(self, parser, sample_lis_content):
        """Test extraction of 'See file' references."""
        metadata = parser._parse_lis_content(sample_lis_content, "Vh5205_C-78")

        assert len(metadata.file_references) == 2
        assert (
            "TestPieceCreepTests-TechnicalDrawing-FormA.pdf" in metadata.file_references
        )
        assert "Vh5205_Complementary_Ch.-Comp.-measured.LIS" in metadata.file_references

    @pytest.mark.parametrize(
        "date_str,expected",
        [
            ("2023-02-08 09:06:15", datetime(2023, 2, 8, 9, 6, 15)),
            ("8.2.23 9:06 AM", datetime(2023, 2, 8, 9, 6)),
            ("08.02.2023 09:06", datetime(2023, 2, 8, 9, 6)),
            ("8.2.23 09:06", datetime(2023, 2, 8, 9, 6)),
            ("08.02.2023 09:06:15", datetime(2023, 2, 8, 9, 6, 15)),
            ("8.2.23 9:06AM", datetime(2023, 2, 8, 9, 6)),  # No space
        ],
    )
    def test_parse_date_multiple_formats(self, parser, date_str, expected):
        """Test date parsing with various formats found in LIS files."""
        parse_errors = []
        result = parser._parse_date(date_str, 1, parse_errors, "Vh5205_C-78")
        assert result == expected
        assert len(parse_errors) == 0

    def test_parse_invalid_date(self, parser):
        """Test graceful handling of invalid dates."""
        parse_errors = []
        result = parser._parse_date("invalid-date", 1, parse_errors, "Vh5205_C-78")
        assert result is None
        assert len(parse_errors) == 1
        assert "Invalid date format" in parse_errors[0]

    def test_missing_required_dates_returns_none(self, parser):
        """Test that missing dates cause parse failure."""
        content = """CATEGORIZATION\tENTRY\t...\tINFORMATION
Metadata --> Test info --> Test parameters\tSpecified temperature\t\t\t\tMandatory\t980\t*
"""
        metadata = parser._parse_lis_content(content, "Vh5205_C-78")
        assert metadata is None

    def test_skip_na_values(self, parser):
        """Test that N/A and empty values are skipped."""
        content = """CATEGORIZATION\tENTRY\t...\tINFORMATION
Metadata --> Test info --> Test job details\tProject\t\t\t\tOptional\tn/a\t
Metadata --> Test info --> Test job details\tTest ID\t\t\t\tMandatory\t-\t
Metadata --> Test info --> Test parameters\tSpecified temperature\t\t\t\tMandatory\t980\t*
Metadata --> Test info --> Test job details\tDate of test start\t\t\t\tMandatory\t2023-02-08 09:06:15\t
Metadata --> Test info --> Test job details\tDate of test end\t\t\t\tMandatory\t2023-02-11 15:48:15\t
"""
        metadata = parser._parse_lis_content(content, "Vh5205_C-78")
        assert metadata is not None
        assert metadata.project == ""  # n/a was skipped
        assert metadata.specified_temperature == 980.0

    def test_percentage_conversion(self, parser):
        """Test percentage to ratio conversion."""
        content = """CATEGORIZATION\tENTRY\t...\tINFORMATION
Metadata --> Test info --> Test job details\tDate of test start\t\t\t\tMandatory\t2023-02-08 09:06:15\t
Metadata --> Test info --> Test job details\tDate of test end\t\t\t\tMandatory\t2023-02-11 15:48:15\t
Metadata --> Test info --> Test parameters\tPercentage creep extension\t\t\t\tOptional\t2.5%\t
"""
        metadata = parser._parse_lis_content(content, "Vh5205_C-78")
        assert abs(metadata.percentage_creep_extension - 0.025) < 0.001

    def test_orientation_with_degree_symbol(self, parser):
        """Test orientation parsing with degree symbol."""
        content = """CATEGORIZATION\tENTRY\t...\tINFORMATION
Metadata --> Test info --> Test job details\tDate of test start\t\t\t\tMandatory\t2023-02-08 09:06:15\t
Metadata --> Test info --> Test job details\tDate of test end\t\t\t\tMandatory\t2023-02-11 15:48:15\t
Metadata --> Material history and condition --> Microstructure\tSingle crystal orientation\t\t\t\tMandatory\t12.5°\t
"""
        metadata = parser._parse_lis_content(content, "Vh5205_C-78")
        assert metadata.single_crystal_orientation == 12.5

    def test_descriptive_orientation_text_skipped(self, parser):
        """Test that descriptive orientation text is skipped, not treated as error."""
        content = """CATEGORIZATION\tENTRY\t...\tINFORMATION
Metadata --> Test info --> Test job details\tDate of test start\t\t\t\tMandatory\t2023-02-08 09:06:15\t
Metadata --> Test info --> Test job details\tDate of test end\t\t\t\tMandatory\t2023-02-11 15:48:15\t
Metadata --> Material history and condition --> Microstructure\tSingle crystal orientation\t\t\t\tMandatory\tOrientation determined by Laue method\t
"""
        metadata = parser._parse_lis_content(content, "Vh5205_C-78")
        assert metadata is not None
        assert metadata.single_crystal_orientation == 0.0  # Default, not an error

    def test_duplicate_file_references_removed(self, parser):
        """Test that duplicate file references are removed."""
        content = """CATEGORIZATION\tENTRY\t...\tINFORMATION
Metadata --> Test info --> Test job details\tDate of test start\t\t\t\tMandatory\t2023-02-08 09:06:15\t
Metadata --> Test info --> Test job details\tDate of test end\t\t\t\tMandatory\t2023-02-11 15:48:15\t
Metadata --> Test piece\tDrawing 1\t\t\t\tMandatory\tSee file "drawing.pdf"\t
Metadata --> Test piece\tDrawing 2\t\t\t\tMandatory\tSee file "drawing.pdf"\t
"""
        metadata = parser._parse_lis_content(content, "Vh5205_C-78")
        assert len(metadata.file_references) == 1
        assert metadata.file_references[0] == "drawing.pdf"
