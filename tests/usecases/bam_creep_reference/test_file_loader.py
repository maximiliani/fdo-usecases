# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for file loader."""

import pytest

from fdo_usecases.usecases.bam_creep_reference.file_loader import FileLoader


class TestFileLoader:
    """Test file discovery and grouping logic."""

    @pytest.fixture
    def loader(self):
        """Create file loader instance."""
        return FileLoader()

    def test_pattern_a_naming(self, loader, mock_pid_record):
        """Test Pattern A: Vh5205_C-XX-Type.LIS."""
        mock_graph = {
            "checksum1": mock_pid_record("Vh5205_C-78-MD-TR.lis"),
            "checksum2": mock_pid_record("Vh5205_C-78-Creep.LIS"),
            "checksum3": mock_pid_record("Vh5205_C-78-Loading.LIS"),
        }

        loader.load_from_zenodo_graph(mock_graph)
        collections = loader.group_files_by_test_id()

        assert "Vh5205_C-78" in collections
        assert collections["Vh5205_C-78"].md_tr_checksum == "checksum1"
        assert collections["Vh5205_C-78"].creep_checksum == "checksum2"
        assert collections["Vh5205_C-78"].loading_checksum == "checksum3"

    def test_pattern_b_naming(self, loader, mock_pid_record):
        """Test Pattern B: Vh5205_Type_C-XX.LIS."""
        mock_graph = {
            "checksum1": mock_pid_record("Vh5205_MD-TR_C-78.LIS"),
            "checksum2": mock_pid_record("Vh5205_Creep_C-78.LIS"),
            "checksum3": mock_pid_record("Vh5205_Loading_C-78.LIS"),
        }

        loader.load_from_zenodo_graph(mock_graph)
        collections = loader.group_files_by_test_id()

        assert "Vh5205_C-78" in collections
        assert collections["Vh5205_C-78"].md_tr_checksum == "checksum1"

    def test_pattern_b_preferred_over_pattern_a(self, loader, mock_pid_record):
        """Test that Pattern B takes precedence when both exist."""
        mock_graph = {
            "pattern_a": mock_pid_record("Vh5205_C-78-MD-TR.lis"),
            "pattern_b": mock_pid_record("Vh5205_MD-TR_C-78.LIS"),
            "creep": mock_pid_record("Vh5205_C-78-Creep.LIS"),
            "loading": mock_pid_record("Vh5205_C-78-Loading.LIS"),
        }

        loader.load_from_zenodo_graph(mock_graph)
        collection = loader.group_files_by_test_id()["Vh5205_C-78"]

        assert collection.md_tr_checksum == "pattern_b"

    def test_standalone_lis_files(self, loader, mock_pid_record):
        """Test detection of standalone Vh5205_C-XX.LIS files."""
        mock_graph = {
            "standalone": mock_pid_record("Vh5205_C-85.LIS"),
            "md_tr": mock_pid_record("Vh5205_C-85-MD-TR.lis"),
            "creep": mock_pid_record("Vh5205_C-85-Creep.LIS"),
            "loading": mock_pid_record("Vh5205_C-85-Loading.LIS"),
        }

        loader.load_from_zenodo_graph(mock_graph)
        collections = loader.group_files_by_test_id()

        assert "Vh5205_C-85" in collections
        assert "standalone" in collections["Vh5205_C-85"].standalone_lis_files

    def test_complementary_files(self, loader, mock_pid_record):
        """Test complementary file detection."""
        mock_graph = {
            "chem": mock_pid_record("Vh5205_Complementary_Ch.-Comp.-measured.LIS"),
            "heat": mock_pid_record("Vh5205_Complementary_Heat-treatment.LIS"),
            "roughness": mock_pid_record("Vh5205_Complementary_Roughness.LIS"),
        }

        loader.load_from_zenodo_graph(mock_graph)
        comp_files = loader.find_complementary_files()

        assert comp_files.chemical_composition_measured == "chem"
        assert comp_files.heat_treatment == "heat"
        assert comp_files.roughness == "roughness"

    def test_md_tr_common_file(self, loader, mock_pid_record):
        """Test MD-TR_Common-to-all.LIS detection."""
        mock_graph = {
            "common": mock_pid_record("Vh5205_MD-TR_Common-to-all.LIS"),
            "md_tr": mock_pid_record("Vh5205_C-78-MD-TR.lis"),
            "creep": mock_pid_record("Vh5205_C-78-Creep.LIS"),
            "loading": mock_pid_record("Vh5205_C-78-Loading.LIS"),
        }

        loader.load_from_zenodo_graph(mock_graph)

        assert loader.md_tr_common_checksum == "common"

    def test_incomplete_file_set_skipped(self, loader, mock_pid_record):
        """Test that incomplete file sets are skipped."""
        mock_graph = {
            "md_tr": mock_pid_record("Vh5205_C-99-MD-TR.lis"),
            "creep": mock_pid_record("Vh5205_C-99-Creep.LIS"),
            # Missing Loading file
        }

        loader.load_from_zenodo_graph(mock_graph)
        collections = loader.group_files_by_test_id()

        assert "Vh5205_C-99" not in collections
        assert len(loader.errors) == 1
        assert loader.errors[0].error_type == "INCOMPLETE_FILES"

    def test_non_lis_files_skipped(self, loader, mock_pid_record):
        """Test that non-LIS files are skipped."""
        mock_graph = {
            "json": mock_pid_record("translation.json"),
            "xml": mock_pid_record("metadata.xml"),
            "md_tr": mock_pid_record("Vh5205_C-78-MD-TR.lis"),
            "creep": mock_pid_record("Vh5205_C-78-Creep.LIS"),
            "loading": mock_pid_record("Vh5205_C-78-Loading.LIS"),
        }

        loader.load_from_zenodo_graph(mock_graph)
        collections = loader.group_files_by_test_id()

        assert len(collections) == 1
        assert "Vh5205_C-78" in collections

    def test_file_urls_extracted(self, loader, mock_pid_record):
        """Test that download URLs are extracted."""
        mock_graph = {
            "checksum1": mock_pid_record(
                "Vh5205_C-78-MD-TR.lis",
                download_url="https://zenodo.org/api/records/123/files/file.lis",
            ),
            "checksum2": mock_pid_record("Vh5205_C-78-Creep.LIS"),
            "checksum3": mock_pid_record("Vh5205_C-78-Loading.LIS"),
        }

        loader.load_from_zenodo_graph(mock_graph)

        assert "checksum1" in loader.file_urls
        assert (
            loader.file_urls["checksum1"]
            == "https://zenodo.org/api/records/123/files/file.lis"
        )

    def test_find_complementary_files_raises_if_not_loaded(self, loader):
        """Test that find_complementary_files raises if graph not loaded."""
        with pytest.raises(ValueError, match="Call load_from_zenodo_graph first"):
            loader.find_complementary_files()
