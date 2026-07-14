# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for image extractor."""

from unittest.mock import MagicMock

import pytest

from fdo_usecases.usecases.bam_creep_reference.image_extractor import ImageExtractor


class TestImageExtractor:
    """Test image detection logic."""

    @pytest.fixture
    def extractor(self):
        """Create image extractor instance."""
        return ImageExtractor()

    def test_extract_sem_images_by_filename(self, extractor):
        """Test SEM image detection by filename pattern."""
        mock_record = MagicMock()
        mock_record.toSimpleJSON.return_value = {
            "record": [
                {
                    "key": "21.T11969/bd3e9fb9b606d2198c9e",
                    "value": "SEM_image_001.tiff",
                },
                {"key": "21.T11969/3313b863118ed5eb0ded", "value": "image/tiff"},
                {
                    "key": "21.T11969/479febb2bbe8400da547",
                    "value": "https://example.com/file.tiff",
                },
            ]
        }

        mock_graph = {"checksum1": mock_record}
        sem_checksums, preview_urls = extractor.extract_images_from_graph(mock_graph)

        assert len(sem_checksums) == 1
        assert sem_checksums[0] == "checksum1"

    def test_extract_sem_images_by_mime_type(self, extractor):
        """Test SEM image detection by MIME type."""
        mock_record = MagicMock()
        mock_record.toSimpleJSON.return_value = {
            "record": [
                {"key": "21.T11969/bd3e9fb9b606d2198c9e", "value": "image_001.tif"},
                {"key": "21.T11969/3313b863118ed5eb0ded", "value": "image/tiff"},
                {
                    "key": "21.T11969/479febb2bbe8400da547",
                    "value": "https://example.com/file.tif",
                },
            ]
        }

        mock_graph = {"checksum1": mock_record}
        sem_checksums, preview_urls = extractor.extract_images_from_graph(mock_graph)

        # Should not match without SEM keyword
        assert len(sem_checksums) == 0

    def test_extract_preview_images(self, extractor):
        """Test preview image detection."""
        mock_record = MagicMock()
        mock_record.toSimpleJSON.return_value = {
            "record": [
                {
                    "key": "21.T11969/bd3e9fb9b606d2198c9e",
                    "value": "test_piece_location.jpg",
                },
                {"key": "21.T11969/3313b863118ed5eb0ded", "value": "image/jpeg"},
                {
                    "key": "21.T11969/479febb2bbe8400da547",
                    "value": "https://example.com/preview.jpg",
                },
            ]
        }

        mock_graph = {"checksum1": mock_record}
        sem_checksums, preview_urls = extractor.extract_images_from_graph(mock_graph)

        assert len(preview_urls) == 1
        assert preview_urls[0] == "https://example.com/preview.jpg"

    def test_dendrite_keyword_matches_sem(self, extractor):
        """Test that dendrite keyword matches SEM images."""
        mock_record = MagicMock()
        mock_record.toSimpleJSON.return_value = {
            "record": [
                {
                    "key": "21.T11969/bd3e9fb9b606d2198c9e",
                    "value": "dendrite_structure.tiff",
                },
                {"key": "21.T11969/3313b863118ed5eb0ded", "value": "image/tiff"},
                {
                    "key": "21.T11969/479febb2bbe8400da547",
                    "value": "https://example.com/file.tiff",
                },
            ]
        }

        mock_graph = {"checksum1": mock_record}
        sem_checksums, _ = extractor.extract_images_from_graph(mock_graph)

        assert len(sem_checksums) == 1

    def test_microstructure_keyword_matches_sem(self, extractor):
        """Test that microstructure keyword matches SEM images."""
        mock_record = MagicMock()
        mock_record.toSimpleJSON.return_value = {
            "record": [
                {
                    "key": "21.T11969/bd3e9fb9b606d2198c9e",
                    "value": "microstructure_analysis.tiff",
                },
                {"key": "21.T11969/3313b863118ed5eb0ded", "value": "image/tiff"},
                {
                    "key": "21.T11969/479febb2bbe8400da547",
                    "value": "https://example.com/file.tiff",
                },
            ]
        }

        mock_graph = {"checksum1": mock_record}
        sem_checksums, _ = extractor.extract_images_from_graph(mock_graph)

        assert len(sem_checksums) == 1

    def test_optical_keyword_matches_preview(self, extractor):
        """Test that optical keyword matches preview images."""
        mock_record = MagicMock()
        mock_record.toSimpleJSON.return_value = {
            "record": [
                {
                    "key": "21.T11969/bd3e9fb9b606d2198c9e",
                    "value": "optical_overview.jpg",
                },
                {"key": "21.T11969/3313b863118ed5eb0ded", "value": "image/jpeg"},
                {
                    "key": "21.T11969/479febb2bbe8400da547",
                    "value": "https://example.com/preview.jpg",
                },
            ]
        }

        mock_graph = {"checksum1": mock_record}
        _, preview_urls = extractor.extract_images_from_graph(mock_graph)

        assert len(preview_urls) == 1

    def test_missing_filename_skipped(self, extractor):
        """Test that records without filename are skipped."""
        mock_record = MagicMock()
        mock_record.toSimpleJSON.return_value = {
            "record": [
                # No name attribute
                {"key": "21.T11969/3313b863118ed5eb0ded", "value": "image/jpeg"},
            ]
        }

        mock_graph = {"checksum1": mock_record}
        sem_checksums, preview_urls = extractor.extract_images_from_graph(mock_graph)

        assert len(sem_checksums) == 0
        assert len(preview_urls) == 0

    def test_jpeg_extension_variants(self, extractor):
        """Test both .jpg and .jpeg extensions are detected."""
        mock_record_jpg = MagicMock()
        mock_record_jpg.toSimpleJSON.return_value = {
            "record": [
                {"key": "21.T11969/bd3e9fb9b606d2198c9e", "value": "location_test.jpg"},
                {"key": "21.T11969/3313b863118ed5eb0ded", "value": "image/jpeg"},
                {
                    "key": "21.T11969/479febb2bbe8400da547",
                    "value": "https://example.com/1.jpg",
                },
            ]
        }

        mock_record_jpeg = MagicMock()
        mock_record_jpeg.toSimpleJSON.return_value = {
            "record": [
                {
                    "key": "21.T11969/bd3e9fb9b606d2198c9e",
                    "value": "overview_test.jpeg",
                },
                {"key": "21.T11969/3313b863118ed5eb0ded", "value": "image/jpeg"},
                {
                    "key": "21.T11969/479febb2bbe8400da547",
                    "value": "https://example.com/2.jpeg",
                },
            ]
        }

        mock_graph = {
            "checksum1": mock_record_jpg,
            "checksum2": mock_record_jpeg,
        }

        _, preview_urls = extractor.extract_images_from_graph(mock_graph)
        assert len(preview_urls) == 2
