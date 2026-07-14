# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for LISParser facade."""

from unittest.mock import patch

import pytest

from fdo_usecases.usecases.bam_creep_reference import LISParser
from fdo_usecases.usecases.bam_creep_reference.models import ParsingError


class TestLISParserIntegration:
    """Integration tests for complete LIS parsing workflow."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return LISParser()

    @pytest.mark.asyncio
    async def test_full_parsing_workflow(
        self, parser, mock_pid_record, sample_lis_content
    ):
        """Test complete workflow from graph loading to metadata extraction."""
        # Mock HTTP client to return sample content
        mock_graph = {
            "checksum1": mock_pid_record("Vh5205_C-78-MD-TR.lis"),
            "checksum2": mock_pid_record("Vh5205_C-78-Creep.LIS"),
            "checksum3": mock_pid_record("Vh5205_C-78-Loading.LIS"),
        }

        parser.load_from_zenodo_graph(mock_graph)

        # Mock the HTTP fetch to return sample content
        with patch.object(
            parser._http_client, "_fetch_file_content", return_value=sample_lis_content
        ):
            metadata = await parser.parse_md_tr_file("checksum1")

            assert metadata is not None
            assert metadata.test_id == "Vh5205_C-78"
            assert metadata.material_id == "CMSX-6"
            assert metadata.specified_temperature == 980.0

    @pytest.mark.asyncio
    async def test_error_handling_fetch_failure(self, parser, mock_pid_record):
        """Test graceful handling of HTTP fetch failures."""
        mock_graph = {
            "checksum1": mock_pid_record("Vh5205_C-78-MD-TR.lis"),
            "checksum2": mock_pid_record("Vh5205_C-78-Creep.LIS"),
            "checksum3": mock_pid_record("Vh5205_C-78-Loading.LIS"),
        }

        parser.load_from_zenodo_graph(mock_graph)

        # Simulate fetch failure
        with patch.object(
            parser._http_client, "_fetch_file_content", return_value=None
        ):
            metadata = await parser.parse_md_tr_file("checksum1")

            assert metadata is None
            assert len(parser.errors) > 0
            assert parser.errors[0].error_type == "FETCH_ERROR"

    @pytest.mark.asyncio
    async def test_group_files_returns_collections(self, parser, mock_pid_record):
        """Test that file grouping returns proper collections."""
        mock_graph = {
            "md_tr": mock_pid_record("Vh5205_C-78-MD-TR.lis"),
            "creep": mock_pid_record("Vh5205_C-78-Creep.LIS"),
            "loading": mock_pid_record("Vh5205_C-78-Loading.LIS"),
        }

        parser.load_from_zenodo_graph(mock_graph)
        collections = parser.group_files_by_test_id()

        assert "Vh5205_C-78" in collections
        assert collections["Vh5205_C-78"].md_tr_checksum == "md_tr"
        assert collections["Vh5205_C-78"].creep_checksum == "creep"
        assert collections["Vh5205_C-78"].loading_checksum == "loading"

    @pytest.mark.asyncio
    async def test_context_manager_initializes_http_session(self):
        """Test that async context manager initializes HTTP session."""
        async with LISParser() as parser:
            assert parser._http_client._session is not None

        # Session should be closed after exit
        assert parser._http_client._session.closed

    def test_extract_keywords_delegates_to_component(
        self, parser, sample_parsed_metadata
    ):
        """Test that keyword extraction delegates to component."""
        keywords = parser.extract_keywords(sample_parsed_metadata)

        assert "CMSX-6" in keywords
        assert "DIN EN ISO 204" in keywords

    def test_report_errors_logs_all_errors(self, parser, caplog):
        """Test error reporting logs all errors."""
        # Manually add an error
        parser._file_loader._errors.append(
            ParsingError(
                test_id="Vh5205_C-78",
                filename="checksum123",
                error_type="TEST_ERROR",
                message="Test error message",
            )
        )

        parser.report_errors()

        assert "LIS parsing encountered 1 error(s)" in caplog.text
        assert "TEST_ERROR" in caplog.text
        assert "Test error message" in caplog.text
