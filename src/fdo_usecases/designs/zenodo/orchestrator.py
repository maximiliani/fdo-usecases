# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

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
from fdo_usecases.designs.zenodo.models import Dataset
from fdo_usecases.designs.zenodo.models.exchange import (
    CreatorData,
    DatasetFDOData,
    FileFDOData,
)

logger = logging.getLogger(__name__)


class ZenodoFDODesign(RecordDesign):
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

    def __init__(self, doi: str):
        """Initialize orchestrator with DOI.

        Args:
            doi: Digital Object Identifier of the dataset

        """
        super().__init__()
        self.doi = doi
        self._processed_datasets: set[str] = set()
        self._dataset: Dataset | None = None
        self._record_graph: dict[str, PidRecord] = {}

        # Composed designs (pass self as orchestrator for graph access)
        self.dataset_design = ZenodoDatasetDesign(self)
        self.file_design = ZenodoFileDesign(self)
        self.publication_design = PublicationDesign(self)

        # Reference processing service
        self.reference_processor = ReferenceProcessor(self)

        logger.info(f"ZenodoFDODesign initialized for DOI: {doi}")

    async def _fetch_metadata(self) -> Dataset:
        """Fetch and cache Zenodo metadata.

        Returns:
            Complete Dataset object with all versions and files

        """
        if self._dataset is None:
            logger.info(f"Fetching metadata for DOI: {self.doi}")
            fetcher = ZenodoDatasetFetcher(cache_enabled=True)
            self._dataset = await fetcher.fetch_by_doi(self.doi)
            logger.info(
                f"Fetched {len(self._dataset.versions)} versions "
                f"with {len(self._dataset.all_files)} unique files"
            )
        return self._dataset

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

            file_data = FileFDOData(
                checksum=checksum,
                filename=file_obj.filename,
                mimetype=file_obj.mimetype,
                download_url=str(file_obj.download_url),
                license_url=license_url,
                previous_version_checksum=file_obj.previous_version_checksum,
                next_version_checksum=file_obj.next_version_checksum,
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
        nested_design = ZenodoFDODesign(doi)
        nested_design._processed_datasets = self._processed_datasets
        await nested_design.execute_async()

    def execute(self) -> None:
        """Execute FDO creation synchronously.

        Main entry point that wraps async execution. Fetches metadata,
        transforms to exchange models, and creates all FDOs.

        """
        asyncio.run(self.execute_async())

    async def execute_async(self) -> None:
        """Async execution entry point.

        Main workflow:
        1. Check deduplication
        2. Fetch metadata
        3. Transform to exchange models
        4. Create Dataset FDOs
        5. Create File FDOs
        6. Process references

        """
        if self.doi in self._processed_datasets:
            logger.warning(f"Skipping already processed dataset: {self.doi}")
            return

        self._processed_datasets.add(self.doi)
        logger.info(f"Starting FDO creation for DOI: {self.doi}")

        # Fetch metadata
        dataset = await self._fetch_metadata()

        # Transform to exchange models
        dataset_datas, file_datas = self._transform_to_exchange_models(dataset)

        # Create Dataset FDOs
        logger.info(f"Creating {len(dataset_datas)} Dataset FDOs")
        for data in dataset_datas:
            await self.dataset_design.create_fdo(data)

        # Create File FDOs
        logger.info(f"Creating {len(file_datas)} File FDOs")
        for data in file_datas:
            await self.file_design.create_fdo(data)

        # Process references via service
        await self.reference_processor.process_all(dataset.related_identifiers)

        logger.info(f"Completed FDO creation for DOI: {self.doi}")


__all__ = ["ZenodoFDODesign"]
