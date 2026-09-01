# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for dataset metadata extractor."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from fdo_usecases.usecases.bam_creep_reference.dataset_metadata import (
    DatasetMetadataExtractor,
)
from fdo_usecases.usecases.bam_creep_reference.models import ParsedTestMetadata


class TestDatasetMetadataExtractor:
    """Test metadata extraction logic."""

    @pytest.fixture
    def extractor(self):
        """Create metadata extractor instance."""
        return DatasetMetadataExtractor()

    def test_get_creators_from_dataset(self, extractor):
        """Test creator ORCID extraction."""
        mock_record = MagicMock()
        mock_record.toSimpleJSON.return_value = {
            "record": [
                {
                    "key": "21.T11969/7c67083a5d218e544063",
                    "value": "https://orcid.org/0000-0003-0012-2414",
                },
            ]
        }

        mock_graph = {"checksum1": mock_record}
        creators = extractor.get_creators_from_dataset(mock_graph)

        assert len(creators) == 1
        assert "https://orcid.org/0000-0003-0012-2414" in creators

    def test_get_creators_deduplicated(self, extractor):
        """Test that duplicate creators are removed."""
        mock_record1 = MagicMock()
        mock_record1.toSimpleJSON.return_value = {
            "record": [
                {
                    "key": "21.T11969/7c67083a5d218e544063",
                    "value": "https://orcid.org/0000-0003-0012-2414",
                },
            ]
        }

        mock_record2 = MagicMock()
        mock_record2.toSimpleJSON.return_value = {
            "record": [
                {
                    "key": "21.T11969/7c67083a5d218e544063",
                    "value": "https://orcid.org/0000-0003-0012-2414",  # Same ORCID
                },
            ]
        }

        mock_graph = {
            "checksum1": mock_record1,
            "checksum2": mock_record2,
        }

        creators = extractor.get_creators_from_dataset(mock_graph)
        assert len(creators) == 1  # Deduplicated

    def test_get_affiliations_from_dataset(self, extractor):
        """Test ROR affiliation extraction."""
        mock_record = MagicMock()
        mock_record.toSimpleJSON.return_value = {
            "record": [
                {
                    "key": "21.T11969/ea9f6b3d78c6608fe801",
                    "value": "https://ror.org/03x516a66",
                },
            ]
        }

        mock_graph = {"checksum1": mock_record}
        affiliations = extractor.get_creator_affiliations_from_dataset(mock_graph)

        assert len(affiliations) == 1
        assert "https://ror.org/03x516a66" in affiliations

    def test_get_keywords_from_dataset(self, extractor):
        """Test keyword extraction."""
        mock_record = MagicMock()
        mock_record.toSimpleJSON.return_value = {
            "record": [
                {"key": "21.T11969/793ff5c33c3aeb32907a", "value": "creep test"},
                {
                    "key": "21.T11969/793ff5c33c3aeb32907a",
                    "value": "Ni-based superalloy",
                },
            ]
        }

        mock_graph = {"checksum1": mock_record}
        keywords = extractor.get_keywords_from_dataset(mock_graph)

        assert len(keywords) == 2
        assert "creep test" in keywords
        assert "Ni-based superalloy" in keywords

    def test_get_funders_from_dataset(self, extractor):
        """Test fundedBy grant PID extraction from Dataset FDOs."""
        mock_record = MagicMock()
        mock_record.toSimpleJSON.return_value = {
            "record": [
                {
                    "key": "21.T11969/28ca0d5c50678433e5a8",
                    "value": "PID_grant:https://ror.org/018mejw64::460247524",
                },
            ]
        }

        mock_graph = {"PID_10.5281/zenodo.20132712": mock_record}
        funders = extractor.get_funders_from_dataset(mock_graph)

        assert len(funders) == 1
        assert "PID_grant:https://ror.org/018mejw64::460247524" in funders

    def test_get_funders_from_dataset_deduplicated(self, extractor):
        """Test that duplicate grant PIDs are removed."""
        mock_record = MagicMock()
        mock_record.toSimpleJSON.return_value = {
            "record": [
                {
                    "key": "21.T11969/28ca0d5c50678433e5a8",
                    "value": "PID_grant:https://ror.org/018mejw64::460247524",
                },
                {
                    "key": "21.T11969/28ca0d5c50678433e5a8",
                    "value": "PID_grant:https://ror.org/018mejw64::460247524",  # Same grant
                },
            ]
        }

        mock_graph = {"PID_10.5281/zenodo.20132712": mock_record}
        funders = extractor.get_funders_from_dataset(mock_graph)
        assert len(funders) == 1  # Deduplicated

    def test_get_funders_restricted_to_dataset_dois(self, extractor):
        """Test filtering funders by a specific set of dataset records."""
        mock_record = MagicMock()
        mock_record.toSimpleJSON.return_value = {
            "record": [
                {
                    "key": "21.T11969/28ca0d5c50678433e5a8",
                    "value": "PID_grant:https://ror.org/018mejw64::460247524",
                },
            ]
        }
        other_record = MagicMock()
        other_record.toSimpleJSON.return_value = {
            "record": [
                {
                    "key": "21.T11969/28ca0d5c50678433e5a8",
                    "value": "PID_grant:https://ror.org/other::999",
                },
            ]
        }

        mock_graph = {
            "PID_10.5281/zenodo.20132712": mock_record,
            "PID_10.5281/zenodo.11668376": other_record,
        }

        funders = extractor.get_funders_from_dataset(
            mock_graph, ["PID_10.5281/zenodo.20132712"]
        )
        assert funders == ["PID_grant:https://ror.org/018mejw64::460247524"]

    def test_extract_keywords_from_metadata(self, extractor):
        """Test keyword extraction from parsed metadata."""
        metadata = ParsedTestMetadata(
            test_id="Vh5205_C-78",
            project="Vh 5205",
            date_test_start=datetime(2023, 2, 8, 9, 6, 15),
            date_test_end=datetime(2023, 2, 11, 15, 48, 15),
            applicable_standard="DIN EN ISO 204:2019-4",
            specified_temperature=980.0,
            initial_stress=230.0,
            material_id="CMSX-6",
            single_crystal_orientation=6.9,
        )

        keywords = extractor.extract_keywords(metadata)

        assert "CMSX-6" in keywords
        assert "DIN EN ISO 204" in keywords  # Standard without year/revision

    def test_extract_keywords_handles_missing_standard(self, extractor):
        """Test keyword extraction when standard is missing."""
        metadata = ParsedTestMetadata(
            test_id="Vh5205_C-78",
            project="Vh 5205",
            date_test_start=datetime(2023, 2, 8, 9, 6, 15),
            date_test_end=datetime(2023, 2, 11, 15, 48, 15),
            applicable_standard="",  # Empty standard
            specified_temperature=980.0,
            initial_stress=230.0,
            material_id="CMSX-6",
            single_crystal_orientation=6.9,
        )

        keywords = extractor.extract_keywords(metadata)

        assert "CMSX-6" in keywords
        assert len(keywords) == 1  # Only material ID

    def test_extract_keywords_deduplicated(self, extractor):
        """Test that extracted keywords are deduplicated."""
        metadata = ParsedTestMetadata(
            test_id="Vh5205_C-78",
            project="Vh 5205",
            date_test_start=datetime(2023, 2, 8, 9, 6, 15),
            date_test_end=datetime(2023, 2, 11, 15, 48, 15),
            applicable_standard="CMSX-6",  # Same as material_id
            specified_temperature=980.0,
            initial_stress=230.0,
            material_id="CMSX-6",
            single_crystal_orientation=6.9,
        )

        keywords = extractor.extract_keywords(metadata)
        assert len(keywords) == 1  # Deduplicated
