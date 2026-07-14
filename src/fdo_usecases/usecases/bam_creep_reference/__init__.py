# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""BAM Creep-Reference Usecase - Parse LIS files and create FDOs.

This package provides tools for parsing Laboratory Information System (LIS) files
from the BAM creep-reference dataset and creating FAIR Digital Objects (FDOs) for
materials science experiments.

Main Components:
    - LISParser: Main facade for all parsing operations
    - FileLoader: Discovers and groups LIS files from Zenodo graph
    - HTTPClient: Fetches file content with caching and retry logic
    - LISContentParser: Parses tab-separated LIS content
    - ImageExtractor: Identifies SEM and preview images
    - DatasetMetadataExtractor: Extracts creators, affiliations, keywords

Data Models:
    - LISFileCollection: Grouped files for a single test
    - ComplementaryFiles: Shared files across all tests
    - CommonMetadata: Metadata common to all tests
    - ParsedTestMetadata: Extracted metadata from MD-TR file
    - ParsingError: Error information for failed parses

Example:
    >>> import asyncio
    >>> from fdo_usecases.usecases.bam_creep_reference import LISParser
    >>>
    >>> async def main():
    ...     async with LISParser() as parser:
    ...         parser.load_from_zenodo_graph(zenodo_graph)
    ...         metadata = await parser.parse_md_tr_file(checksum)
    ...         return metadata
    >>>
    >>> # Run with asyncio.run(main())

For detailed documentation, see:
    src/fdo_usecases/usecases/bam_creep_reference/README.md

"""

from .dataset_metadata import DatasetMetadataExtractor
from .file_loader import FileLoader
from .http_client import HTTPClient
from .image_extractor import ImageExtractor
from .lis_parser import LISParser
from .models import (
    CommonMetadata,
    ComplementaryFiles,
    LISFileCollection,
    ParsedTestMetadata,
    ParsingError,
)
from .parser import LISContentParser

__all__ = [
    # Main facade
    "LISParser",
    # Components
    "FileLoader",
    "HTTPClient",
    "LISContentParser",
    "ImageExtractor",
    "DatasetMetadataExtractor",
    # Models
    "LISFileCollection",
    "ComplementaryFiles",
    "CommonMetadata",
    "ParsedTestMetadata",
    "ParsingError",
]
