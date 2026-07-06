# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Zenodo FDO orchestrator - coordinates all FDO creation.

This module provides the ZenodoFDODesign class which orchestrates the complete
workflow of fetching Zenodo metadata, transforming it to exchange models, and
creating FDO records via specialized design classes.

Architecture:
    ZenodoFDODesign (orchestrator)
        ├── ZenodoDatasetFetcher (metadata extraction)
        ├── ZenodoDatasetDesign (dataset FDOs)
        ├── ZenodoFileDesign (file FDOs)
        ├── PublicationDesign (publication FDOs)
        └── ReferenceProcessor (related identifier handling)
"""

import asyncio
import logging

from fdo_usecases.designer_lib.executor import PidRecord, RecordDesign
from fdo_usecases.designs.zenodo.designs import (
    PublicationDesign,
    ZenodoDatasetDesign,
    ZenodoFileDesign,
)
from fdo_usecases.designs.zenodo.fetcher import ZenodoDatasetFetcher
from fdo_usecases.designs.zenodo.handlers import ReferenceProcessor
from fdo_usecases.designs.zenodo.models import Dataset, DatasetVersion
from fdo_usecases.designs.zenodo.models.exchange import (
    CreatorData,
    DatasetFDOData,
    FileFDOData,
)

logger = logging.getLogger(__name__)


class ZenodoFDODesign(RecordDesign):
    """Orchestrate creation of all FDO types from Zenodo metadata."""

    #: Supported preview image MIME types (browser-compatible)
    IMAGE_MIME_TYPES = frozenset(
        [
            "image/png",
            "image/jpeg",
            "image/gif",
            "image/webp",
        ]
    )

    #: Supported preview image filename extensions
    IMAGE_EXTENSIONS = frozenset([".png", ".jpg", ".jpeg", ".gif", ".webp"])

    #: Maximum number of preview images per dataset version
    MAX_PREVIEW_IMAGES = 10

    def _extract_preview_images(
        self,
        version: DatasetVersion,
    ) -> list[str]:
        """Extract preview image URLs from dataset version.

        Filters files by MIME type or filename extension, prioritizing
        browser-compatible formats (PNG, JPEG, GIF, WebP). Excludes TIFF
        due to poor browser support.

        Args:
            version: Dataset version to extract images from

        Returns:
            List of up to MAX_PREVIEW_IMAGES download URLs

        """
        preview_urls = []

        for file_obj in version.files.values():
            is_image = False

            # Primary check: MIME type
            if file_obj.mimetype and file_obj.mimetype in self.IMAGE_MIME_TYPES:
                is_image = True

            # Fallback: filename extension
            if not is_image:
                filename_lower = file_obj.filename.lower()
                if any(filename_lower.endswith(ext) for ext in self.IMAGE_EXTENSIONS):
                    is_image = True

            if is_image:
                preview_urls.append(str(file_obj.download_url))

                # Stop at limit
                if len(preview_urls) >= self.MAX_PREVIEW_IMAGES:
                    break

        return preview_urls

    """Orchestrate creation of all FDO types from Zenodo metadata.

    This is the main entry point for Zenodo FDO generation. It:
    1. Fetches metadata from Zenodo API
    2. Transforms metadata to exchange models
    3. Delegates to specialized design classes
    4. Handles nested references via ReferenceProcessor

    Example:
        ```python
        from fdo_usecases.designs.zenodo import ZenodoFDODesign

        design = ZenodoFDODesign(doi="10.5281/zenodo.20132712")
        design.execute()  # Creates all FDOs
        ```

    Attributes:
        doi: Input DOI for the dataset to process
        _processed_datasets: Set of already processed DOIs (deduplication)
        _dataset: Cached dataset metadata

    """

    def __init__(
        self,
        dois: list[str] | str,
        max_concurrent: int = 10,
        reference_recursion_depth: int = 3,
    ):
        """Initialize orchestrator with DOI(s).

        Args:
            dois: Single DOI string or list of DOI strings to process
            max_concurrent: Maximum number of concurrent API requests (default: 10)
            reference_recursion_depth: Maximum depth for recursive reference fetching (default: 3)

        """
        super().__init__()
        self.dois = [dois] if isinstance(dois, str) else dois
        self._max_concurrent = max_concurrent
        self._reference_recursion_depth = reference_recursion_depth
        self._semaphore: asyncio.Semaphore | None = None
        self._processed_datasets: set[str] = set()
        self._processing_datasets: set[str] = (
            set()
        )  # Currently being processed (cycle detection)
        self._record_graph: dict[str, PidRecord] = {}
        self._cross_reference_registry: dict[str, set[str]] = {}

        # Composed designs (pass self as orchestrator for graph access)
        self.dataset_design = ZenodoDatasetDesign(self)
        self.file_design = ZenodoFileDesign(self)
        self.publication_design = PublicationDesign(self)

        # Reference processing service
        self.reference_processor = ReferenceProcessor(self)

        logger.info(
            f"ZenodoFDODesign initialized for {len(self.dois)} DOI(s), "
            f"max_concurrent={max_concurrent}"
        )

    async def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create semaphore for concurrency limiting.

        Returns:
            Semaphore instance for limiting concurrent requests

        """
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max_concurrent)
        return self._semaphore

    async def _fetch_metadata(self, doi: str) -> Dataset:
        """Fetch Zenodo metadata for a specific DOI.

        Args:
            doi: DOI to fetch metadata for

        Returns:
            Complete Dataset object with all versions and files

        """
        logger.info(f"Fetching metadata for DOI: {doi}")
        fetcher = ZenodoDatasetFetcher(cache_enabled=True)
        dataset = await fetcher.fetch_by_doi(doi)
        logger.info(
            f"Fetched {len(dataset.versions)} versions "
            f"with {len(dataset.all_files)} unique files"
        )
        return dataset

    def _transform_to_exchange_models(
        self, dataset: Dataset
    ) -> tuple[list[DatasetFDOData], list[FileFDOData]]:
        """Convert Pydantic metadata models to exchange models.

        Transforms the fetched metadata into clean data contracts that decouple
        FDO creation from the metadata source.

        Args:
            dataset: Complete dataset with all versions

        Returns:
            Tuple of (dataset_datas, file_datas)

        """
        logger.debug("Transforming metadata to exchange models")

        dataset_datas: list[DatasetFDOData] = []
        file_datas: list[FileFDOData] = []

        # Transform each version
        for version in dataset.versions.values():
            landing_page_url = f"https://doi.org/{version.doi}"

            # Extract preview images for this version
            preview_images = self._extract_preview_images(version)

            dataset_data = DatasetFDOData(
                doi=version.doi,
                title=version.title,
                description=version.description,
                publication_date=version.publication_date,
                version_label=version.version_label,
                creators=[
                    CreatorData(orcid=c.orcid, ror_id=c.ror_id)
                    for c in version.creators
                ],
                keywords=version.keywords,
                previous_version_doi=(
                    version.previous_version.doi if version.previous_version else None
                ),
                next_version_doi=(
                    version.next_version.doi if version.next_version else None
                ),
                latest_version_doi=(
                    dataset.latest_version_doi
                    if dataset.latest_version_doi != version.doi
                    else None
                ),
                files=list(version.files.keys()),
                landing_page_url=landing_page_url,
                preview_images=preview_images,
            )
            dataset_datas.append(dataset_data)

        # Transform files (deduplicated by checksum)
        for checksum, file_obj in dataset.all_files.items():
            # Find license from parent dataset version
            license_url = None
            for version_doi in file_obj.present_in_versions:
                if version_doi in dataset.versions:
                    ver = dataset.versions[version_doi]
                    if ver.license and ver.license.url:
                        license_url = str(ver.license.url)
                        break

            # Landing page points to the first dataset version where this file appeared
            landing_page_url = f"https://doi.org/{file_obj.first_dataset_version}"

            file_data = FileFDOData(
                checksum=checksum,
                filename=file_obj.filename,
                mimetype=file_obj.mimetype,
                download_url=str(file_obj.download_url),
                license_url=license_url,
                previous_version_checksum=file_obj.previous_version_checksum,
                next_version_checksum=file_obj.next_version_checksum,
                dataset_versions=file_obj.present_in_versions.copy(),
                landing_page_url=landing_page_url,
            )
            file_datas.append(file_data)

        logger.debug(
            f"Transformed to {len(dataset_datas)} dataset models "
            f"and {len(file_datas)} file models"
        )
        return dataset_datas, file_datas

    async def _process_zenodo_reference(self, doi: str) -> None:
        """Recursively process a nested Zenodo dataset reference.

        Called by ZenodoReferenceHandler when a related identifier points
        to another Zenodo dataset.

        Args:
            doi: DOI of the referenced Zenodo dataset

        """
        logger.info(f"Processing nested Zenodo reference: {doi}")
        nested_design = ZenodoFDODesign(dois=doi, max_concurrent=self._max_concurrent)
        nested_design._processed_datasets = self._processed_datasets
        nested_design._processing_datasets = (
            self._processing_datasets
        )  # Share processing set for cycle detection
        nested_design._record_graph = self._record_graph
        await nested_design.execute_async()

    def execute(
        self,
    ) -> tuple[list[str], list[tuple[str, BaseException]]]:
        """Execute FDO creation synchronously.

        Returns:
            Tuple of (successful_dois, [(failed_doi, exception), ...])

        """
        return asyncio.run(self.execute_async())

    async def execute_async(
        self,
    ) -> tuple[list[str], list[tuple[str, BaseException]]]:
        """Process all DOIs concurrently with error aggregation.

        Main workflow for each DOI:
        1. Check deduplication
        2. Fetch metadata
        3. Transform to exchange models
        4. Create Dataset FDOs (parallel)
        5. Create File FDOs (parallel)
        6. Process references

        Returns:
            Tuple of (successful_dois, [(failed_doi, exception), ...])

        """
        semaphore = await self._get_semaphore()

        async def process_single_doi(doi: str) -> str:
            async with semaphore:
                await self._process_doi(doi, depth=0)
                return doi

        results = await asyncio.gather(
            *[process_single_doi(doi) for doi in self.dois],
            return_exceptions=True,
        )

        successful: list[str] = []
        failed: list[tuple[str, BaseException]] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                logger.error(
                    f"Failed to process {self.dois[i]}: {result}", exc_info=result
                )
                failed.append((self.dois[i], result))
            else:
                successful.append(result)

        if failed:
            print(f"\n❌ Failed DOIs ({len(failed)}):")
            for doi, exc in failed:
                print(f"  - {doi}: {type(exc).__name__}: {exc}")

        return successful, failed

    async def _process_doi(self, doi: str, depth: int = 0) -> None:
        """Process a single DOI.

        Args:
            doi: Digital Object Identifier to process
            depth: Current recursion depth (for reference processing)

        """
        # Check for cycles - if already being processed, skip
        if doi in self._processing_datasets:
            logger.warning(
                f"Cycle detected! Skipping dataset currently being processed: {doi}"
            )
            return

        if doi in self._processed_datasets:
            logger.warning(f"Skipping already processed dataset: {doi}")
            return

        # Mark as currently being processed (cycle detection)
        self._processing_datasets.add(doi)
        self._processed_datasets.add(doi)
        logger.info(f"Starting FDO creation for DOI: {doi}")

        dataset = await self._fetch_metadata(doi)

        dataset_datas, file_datas = self._transform_to_exchange_models(dataset)

        logger.info(f"Creating {len(dataset_datas)} Dataset FDOs")
        await asyncio.gather(
            *[self.dataset_design.create_fdo(data) for data in dataset_datas]
        )

        logger.info(f"Creating {len(file_datas)} File FDOs")
        await asyncio.gather(
            *[self.file_design.create_fdo(data) for data in file_datas]
        )

        # Process references with context of which dataset is referencing them
        # Pass concept DOI to detect cross-dataset references
        await self.reference_processor.process_all(
            dataset.related_identifiers,
            doi,
            dataset.concept_doi,
            depth,
        )

        logger.info(f"Completed FDO creation for DOI: {doi}")


__all__ = ["ZenodoFDODesign"]
