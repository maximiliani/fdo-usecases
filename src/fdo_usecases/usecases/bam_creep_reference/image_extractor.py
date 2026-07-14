# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Extract SEM and preview images from Zenodo graph.

This module identifies and categorizes image files within a Zenodo FDO graph
based on MIME types and filename patterns.

SEM Images (Scientific Microscopy):
    - MIME type: image/tiff or image/tif
    - Filename extensions: .tif, .tiff
    - Keywords in filename: SEM, dendrite, microstructure, interdendritic
    - Output: List of checksums for referencing in Material FDOs

Preview Images (Documentation):
    - MIME type: image/jpeg or image/jpg
    - Filename extensions: .jpg, .jpeg
    - Keywords in filename: location, optical, overview, test-piece
    - Output: List of download URLs for direct access

Example:
    >>> extractor = ImageExtractor()
    >>> sem_checksums, preview_urls = extractor.extract_images_from_graph(graph)
    >>> print(f"Found {len(sem_checksums)} SEM images")
    Found 15 SEM images

"""

import logging
import re

logger = logging.getLogger(__name__)


class ImageExtractor:
    """Detect and categorize image files from Zenodo graph.

    This class scans a Zenodo FDO graph to identify image files relevant
    to creep test documentation. It separates scientific microscopy images
    (SEM) from documentary preview images.

    Attributes:
        SEM_PATTERN: Compiled regex for SEM-related filenames
        PREVIEW_PATTERN: Compiled regex for preview image filenames
        TIF_PATTERN: Compiled regex for TIFF file extensions
        JPG_PATTERN: Compiled regex for JPEG file extensions

    Example:
        >>> extractor = ImageExtractor()
        >>> sem_images, preview_images = extractor.extract_images_from_graph(graph)
        >>> len(sem_images) > 0
        True

    """

    # Pattern for SEM-related filenames
    SEM_PATTERN = re.compile(
        r"(SEM|dendrite|microstructure|interdentritic)", re.IGNORECASE
    )

    # Pattern for preview image filenames
    PREVIEW_PATTERN = re.compile(
        r"(location|optical|overview|test[- ]piece)", re.IGNORECASE
    )

    # File extension patterns
    TIF_PATTERN = re.compile(r"\.tif$", re.IGNORECASE)
    JPG_PATTERN = re.compile(r"\.jpe?g$", re.IGNORECASE)

    # Attribute keys for Zenodo FDO graph
    NAME_KEY = "21.T11969/bd3e9fb9b606d2198c9e"
    MIME_KEY = "21.T11969/3313b863118ed5eb0ded"
    URL_KEY = "21.T11969/479febb2bbe8400da547"

    def extract_images_from_graph(
        self, zenodo_graph: dict
    ) -> tuple[list[str], list[str]]:
        """Extract SEM and preview image information from Zenodo graph.

        Processes each record in the graph to identify image files based on
        MIME type and filename patterns. Returns two separate lists for
        scientific and documentary images.

        Args:
            zenodo_graph: Pre-populated graph from ZenodoFDODesign
                Keys are checksums, values are PidRecord objects

        Returns:
            Tuple of (sem_checksums, preview_urls):
            - sem_checksums: List of checksums for SEM .tiff files
            - preview_urls: List of download URLs for preview .jpg files

        Example:
            >>> extractor = ImageExtractor()
            >>> sem_imgs, preview_imgs = extractor.extract_images_from_graph(graph)
            >>> isinstance(sem_imgs, list)
            True
            >>> isinstance(preview_imgs, list)
            True

        """
        sem_checksums: list[str] = []
        preview_urls: list[str] = []

        for record_id, record in zenodo_graph.items():
            # Convert PidRecord to dict
            record_dict = record.toSimpleJSON()

            # Extract filename
            name_attrs = [
                attr["value"]
                for attr in record_dict["record"]
                if attr["key"] == self.NAME_KEY
            ]
            if not name_attrs:
                continue
            filename = name_attrs[0]

            # Extract MIME type
            mime_attrs = [
                attr["value"]
                for attr in record_dict["record"]
                if attr["key"] == self.MIME_KEY
            ]
            mime_type = mime_attrs[0].lower() if mime_attrs else ""

            # Extract download URL
            url_attrs = [
                attr["value"]
                for attr in record_dict["record"]
                if attr["key"] == self.URL_KEY
            ]
            download_url = url_attrs[0] if url_attrs else None

            # Check for SEM images (.tiff files with SEM-related names)
            if self.TIF_PATTERN.search(filename) or "image/tiff" in mime_type:
                if self.SEM_PATTERN.search(filename):
                    sem_checksums.append(record_id)
                    logger.debug(f"Found SEM image: {filename} ({record_id})")

            # Check for preview images (.jpg files with preview-related names)
            if self.JPG_PATTERN.search(filename) or "image/jpeg" in mime_type:
                if self.PREVIEW_PATTERN.search(filename):
                    if download_url:
                        preview_urls.append(download_url)
                        logger.debug(f"Found preview image: {filename}")

        logger.info(
            f"Found {len(sem_checksums)} SEM images and {len(preview_urls)} preview images"
        )
        return sem_checksums, preview_urls

    def find_sem_images(self, zenodo_graph: dict) -> list[str]:
        """Find SEM .tiff image checksums from Zenodo graph.

        Convenience method that returns only SEM images from the graph.

        Args:
            zenodo_graph: Pre-populated graph from ZenodoFDODesign

        Returns:
            List of checksums for .tiff files with SEM-related names

        Example:
            >>> extractor = ImageExtractor()
            >>> sem_images = extractor.find_sem_images(graph)
            >>> len(sem_images) > 0
            True

        """
        sem_checksums, _ = self.extract_images_from_graph(zenodo_graph)
        return sem_checksums

    def find_preview_images(self, zenodo_graph: dict) -> list[str]:
        """Find preview .jpg image URLs from Zenodo graph.

        Convenience method that returns only preview images from the graph.

        Args:
            zenodo_graph: Pre-populated graph from ZenodoFDODesign

        Returns:
            List of download URLs for .jpg files with preview-related names

        Example:
            >>> extractor = ImageExtractor()
            >>> preview_images = extractor.find_preview_images(graph)
            >>> len(preview_images) > 0
            True

        """
        _, preview_urls = self.extract_images_from_graph(zenodo_graph)
        return preview_urls


__all__ = ["ImageExtractor"]
