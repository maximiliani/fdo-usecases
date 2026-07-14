# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Shared pytest fixtures for BAM creep-reference tests."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from fdo_usecases.usecases.bam_creep_reference.models import (
    CommonMetadata,
    ComplementaryFiles,
    LISFileCollection,
    ParsedTestMetadata,
)


@pytest.fixture
def sample_parsed_metadata():
    """Create sample ParsedTestMetadata for testing."""
    return ParsedTestMetadata(
        test_id="Vh5205_C-78",
        project="Vh 5205",
        date_test_start=datetime(2023, 2, 8, 9, 6, 15),
        date_test_end=datetime(2023, 2, 11, 15, 48, 15),
        applicable_standard="DIN EN ISO 204:2019-4",
        specified_temperature=980.0,
        initial_stress=230.0,
        material_id="CMSX-6",
        single_crystal_orientation=6.9,
        percentage_creep_extension=0.015,
        manufacturing_as_manufactured="Vacuum Induction Refined",
        manufacturing_as_tested="Single Crystal Investment Cast",
        file_references=["TechnicalDrawing.pdf", "ChemicalComposition.LIS"],
    )


@pytest.fixture
def sample_file_collection():
    """Create sample LISFileCollection for testing."""
    return LISFileCollection(
        test_id="Vh5205_C-78",
        md_tr_checksum="md5:abc123",
        creep_checksum="md5:def456",
        loading_checksum="md5:ghi789",
        standalone_lis_files=["md5:jkl012"],
    )


@pytest.fixture
def sample_complementary_files():
    """Create sample ComplementaryFiles for testing."""
    return ComplementaryFiles(
        heat_treatment="md5:heat123",
        chemical_composition_measured="md5:chem456",
        chemical_composition_nominal="md5:chem789",
        data_acquisition="md5:data012",
        data_acquisition_creep="md5:data345",
        primary_processed_data="md5:primary678",
        roughness="md5:rough901",
        rp02="md5:rp02234",
        md_tr_common="md5:common567",
    )


@pytest.fixture
def sample_common_metadata():
    """Create sample CommonMetadata for testing."""
    return CommonMetadata(
        material_id="CMSX-6",
        applicable_standard="DIN EN ISO 204:2019-4",
        form_of_as_manufactured_material="Circular ingot",
        geometry_size_as_manufactured="Diameter 50mm",
        geometry_size_as_tested="Gauge diameter 6mm",
    )


@pytest.fixture
def sample_lis_content():
    """Sample LIS content with tab-separated values.

    LIS format has 8 columns:
    CATEGORIZATION | ENTRY | ADDITIONAL_INFO | SYMBOL | UNIT | REQUIREMENT | INFORMATION | COMMON_TO_ALL

    Note: INFORMATION is in column 6 (7th position), REQUIREMENT is in column 5, COMMON_TO_ALL is column 7.
    """
    # Build lines manually to ensure correct tab count (8 columns per line)
    header = "CATEGORIZATION\tENTRY\tENTRY - ADDITIONAL INFORMATION\tSYMBOL\tUNIT\tREQUIREMENT\tINFORMATION\tINFORMATION COMMON TO ALL (*)"
    lines = [
        "Metadata --> Test info --> Test job details\tDate of test start\t\t\t\t\t2023-02-08 09:06:15\t",
        "Metadata --> Test info --> Test job details\tDate of test end\t\t\t\t\t2023-02-11 15:48:15\t",
        "Metadata --> Test info --> Test job details\tProject\t\t\t\t\tVh 5205\t*",
        "Metadata --> Test info --> Test job details\tTest ID\t\t\t\t\tVh5205_C-78\t",
        "Metadata --> Test info --> Test parameters\tTest standard applied\tWas the test performed according to a test standard?\t\t\t\tYes\t*",
        "Metadata --> Test info --> Test parameters\tTest standard\t\t\t\t\tDIN EN ISO 204:2019-4\t*",
        "Metadata --> Test info --> Test parameters\tSpecified temperature\tT\t°C\t\t\t980\t*",
        "Metadata --> Test info --> Test parameters\tInitial stress\tRo\tMPa\t\t\t230\t",
        "Metadata --> Test info --> Test parameters\tPercentage creep extension\t\t\t\t\t1.5%\t",  # Exactly 8 columns
        "Metadata --> Material history and condition\tMaterial Identifier\tE.g., NIMONIC 75, 2.4630, CMSX-6, CMSX-4, ERBO1, …\t\t\t\tCMSX-6\t*",
        "Metadata --> Material history and condition --> Microstructure\tSingle crystal orientation\tLink to file, preferably with machine-readable (meta)data. Laue Crystal Verification. Must be documented for each test piece.\t\t\t\t6.9\t",
        # Parser checks for manufacturing description IN categorization column (not entry)
        "Metadata --> Material history and condition\tManufacturing process description as-manufactured material\tE.g., Cast / Melting, Casting, and Remelting / Induction melting in air, casting into a circular ingot and then electroslag remelting\t\t\t\tVacuum Induction Refined\t*",
        "Metadata --> Material history and condition\tManufacturing process description as-tested material\tThe test piece is manufactured from the as-tested material. Please add a description or a link to Image or technical drawing. The as-tested material is the material to be tested. The as-tested material can be a component.\t\t\t\tSingle Crystal Investment Cast\t*",
        'Metadata --> Test piece\tTest piece technical drawing\tLink to file, preferably with machine-readable (meta)data\t\t\t\tSee file "TestPieceCreepTests-TechnicalDrawing-FormA.pdf"\t*',
        'Metadata --> Material history and condition --> Chemical composition\tChemical composition - measured\tInclude precision, if available. Link to file, preferably with machine-readable (meta)data or add the wt.-% value of for each element\t\twt.-% / at.-%\t\tSee file "Vh5205_Complementary_Ch.-Comp.-measured.LIS"\t*',
    ]
    return header + "\n" + "\n".join(lines) + "\n"


@pytest.fixture
def mock_pid_record():
    """Create a mock PidRecord for testing."""

    def _create_mock(filename: str, download_url: str = None):
        mock = MagicMock()
        mock.toSimpleJSON.return_value = {
            "record": [
                {"key": "21.T11969/bd3e9fb9b606d2198c9e", "value": filename},
                {
                    "key": "21.T11969/479febb2bbe8400da547",
                    "value": download_url or f"https://example.com/{filename}",
                },
            ]
        }
        return mock

    return _create_mock


@pytest.fixture
def sample_zenodo_graph(mock_pid_record):
    """Create a sample Zenodo graph with test LIS files."""
    return {
        "md5:abc123": mock_pid_record("Vh5205_C-78-MD-TR.lis"),
        "md5:def456": mock_pid_record("Vh5205_C-78-Creep.LIS"),
        "md5:ghi789": mock_pid_record("Vh5205_C-78-Loading.LIS"),
        "md5:chem456": mock_pid_record("Vh5205_Complementary_Ch.-Comp.-measured.LIS"),
        "md5:heat123": mock_pid_record("Vh5205_Complementary_Heat-treatment.LIS"),
    }
