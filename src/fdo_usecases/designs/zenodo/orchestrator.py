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

from fdo_usecases.designer_lib.executor import (
    PidRecord,
    RecordDesign,
    placeholder_pid,
)
from fdo_usecases.designs.grant import GrantDesign
from fdo_usecases.designs.zenodo.constants import INFOTYPES
from fdo_usecases.designs.zenodo.designs import (
    PublicationDesign,
    ZenodoDatasetDesign,
    ZenodoFileDesign,
)
from fdo_usecases.designs.zenodo.fetcher import ZenodoDatasetFetcher
from fdo_usecases.designs.zenodo.handlers import ReferenceProcessor
from fdo_usecases.designs.zenodo.handlers.backlink_manager import BacklinkManager
from fdo_usecases.designs.zenodo.models import Dataset, DatasetVersion
from fdo_usecases.designs.zenodo.models.exchange import (
    CreatorData,
    DatasetFDOData,
    FileFDOData,
    GrantFDOData,
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
        self._processed_reference_versions: set[str] = (
            set()
        )  # Versions whose related identifiers have been processed
        self._record_graph: dict[str, PidRecord] = {}
        self._backlink_manager = BacklinkManager(self._record_graph)
        self._metadata_cache: dict[str, Dataset] = {}  # Cache fetched Dataset objects
        self._is_nested_execution = (
            False  # True when called via _process_zenodo_reference
        )

        # Composed designs (pass self as orchestrator for graph access)
        self.dataset_design = ZenodoDatasetDesign(self)
        self.file_design = ZenodoFileDesign(self)
        self.publication_design = PublicationDesign(self)
        self.grant_design = GrantDesign()
        self.grant_design._graph = self._record_graph  # Share same graph reference

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

        Uses an in-memory cache to avoid rebuilding Dataset objects
        that have already been fetched during this session.

        Args:
            doi: DOI to fetch metadata for

        Returns:
            Complete Dataset object with all versions and files

        """
        if doi in self._metadata_cache:
            logger.debug(f"Metadata cache hit for DOI: {doi}")
            return self._metadata_cache[doi]

        logger.info(f"Fetching metadata for DOI: {doi}")
        fetcher = ZenodoDatasetFetcher(cache_enabled=True)
        dataset = await fetcher.fetch_by_doi(doi)
        self._metadata_cache[doi] = dataset
        logger.info(
            f"Fetched {len(dataset.versions)} versions "
            f"with {len(dataset.all_files)} unique files"
        )
        return dataset

    def _transform_to_exchange_models(
        self, dataset: Dataset
    ) -> tuple[list[DatasetFDOData], list[FileFDOData], list[GrantFDOData]]:
        """Convert Pydantic metadata models to exchange models.

        Transforms the fetched metadata into clean data contracts that decouple
        FDO creation from the metadata source.

        Args:
            dataset: Complete dataset with all versions

        Returns:
            Tuple of (dataset_datas, file_datas, grant_datas)

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

            # Get date_created from first dataset version containing this file
            first_version_doi = file_obj.first_dataset_version
            date_created = dataset.versions[first_version_doi].publication_date

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
                latest_version_checksum=file_obj.latest_version_checksum,
                dataset_versions=file_obj.present_in_versions.copy(),
                date_created=date_created,
                landing_page_url=landing_page_url,
            )
            file_datas.append(file_data)

        # Transform grants (deduplicate by unique_key)
        grants_dict: dict[str, GrantFDOData] = {}
        for grant in dataset.grants:
            # Skip grants without valid funder IDs
            if not grant.funder_ror_id and not grant.funder_crossref_doi:
                logger.debug(
                    f"Skipping grant {grant.code} - no valid funder ID "
                    f"(internal_id: {grant.internal_id})"
                )
                continue

            try:
                grant_data = GrantFDOData(
                    funder_ror_id=grant.funder_ror_id,
                    funder_crossref_doi=grant.funder_crossref_doi,
                    funder_name=grant.funder_name or "Unknown",
                    grant_code=grant.code,
                    project_name=grant.title,
                    project_website=None,  # Zenodo doesn't provide this
                )

                if grant_data.unique_key not in grants_dict:
                    grants_dict[grant_data.unique_key] = grant_data
            except ValueError as e:
                logger.warning(f"Skipping invalid grant data: {e}")
                continue

        # Check against pre-registered grants (priority)
        from fdo_usecases.designs.grant import PRE_REGISTERED_GRANTS

        for key, grant_data in list(grants_dict.items()):
            # Find matching pre-registered grant by unique_key
            matching_entry = None
            for entry in PRE_REGISTERED_GRANTS.values():
                if entry.unique_key == key:
                    matching_entry = entry
                    break

            if matching_entry:
                static = matching_entry

                # Log conflict if Zenodo data differs
                if (
                    grant_data.funder_name != static.funder_name
                    or grant_data.project_name != static.project_name
                    or (
                        grant_data.project_website
                        and grant_data.project_website != static.project_website
                    )
                ):
                    logger.warning(
                        f"Grant conflict for {key}: "
                        f"Zenodo={grant_data}, Static={static}. Using static."
                    )

                # Override with static data
                grants_dict[key] = GrantFDOData(
                    funder_ror_id=static.funder_ror_id,
                    funder_crossref_doi=static.funder_crossref_doi,
                    funder_name=static.funder_name,
                    grant_code=static.grant_code,
                    project_name=static.project_name,
                    project_website=static.project_website,
                )

        grant_datas = list(grants_dict.values())

        logger.debug(
            f"Transformed to {len(dataset_datas)} dataset models, "
            f"{len(file_datas)} file models, and {len(grant_datas)} grant models"
        )
        return dataset_datas, file_datas, grant_datas

    async def _process_zenodo_reference(self, doi: str) -> None:
        """Recursively process a nested Zenodo dataset reference.

        Called by ZenodoReferenceHandler when a related identifier points
        to another Zenodo dataset.

        Args:
            doi: DOI of the referenced Zenodo dataset

        """
        logger.info(f"Processing nested Zenodo reference: {doi}")

        # Skip if already fully processed or currently being processed
        if doi in self._processed_datasets or doi in self._processing_datasets:
            logger.debug(f"Nested reference already processed or processing: {doi}")
            return

        nested_design = ZenodoFDODesign(dois=doi, max_concurrent=self._max_concurrent)
        nested_design._processed_datasets = self._processed_datasets
        nested_design._processing_datasets = (
            self._processing_datasets
        )  # Share processing set for cycle detection
        nested_design._processed_reference_versions = self._processed_reference_versions
        nested_design._record_graph = self._record_graph
        nested_design._backlink_manager = (
            self._backlink_manager
        )  # Share same backlink manager
        nested_design._metadata_cache = (
            self._metadata_cache
        )  # Share metadata cache to avoid re-fetching
        nested_design._is_nested_execution = (
            True  # Mark as nested - don't flush backlinks yet
        )
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

        # Apply all deferred backlinks after all processing completes
        await self._flush_cross_reference_backlinks()

        return successful, failed

    async def _process_doi(self, doi: str, depth: int = 0) -> None:
        """Process a single DOI.

        Tracks both version DOIs and concept DOIs to avoid duplicate FDO
        creation. When a concept is already processed, FDO creation is
        skipped but the specific version's related identifiers are still
        processed (different versions may have different references).

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

        # Check if already fully processed (FDOs created)
        if doi in self._processed_datasets:
            logger.debug(f"Dataset already fully processed: {doi}")
            return

        # Mark as currently being processed (cycle detection)
        self._processing_datasets.add(doi)
        logger.info(f"Starting FDO creation for DOI: {doi}")

        dataset = await self._fetch_metadata(doi)

        # Check if concept is already processed or being processed.
        # If so, skip FDO creation (all versions already have FDOs)
        # but still process this version's related identifiers.
        # Exclude the current DOI from the check: when doi == concept_doi,
        # the concept was just added to _processing_datasets above and should
        # not count as "already processed" for this call.
        concept_already_processed = dataset.concept_doi in self._processed_datasets or (
            dataset.concept_doi in self._processing_datasets
            and dataset.concept_doi != doi
        )

        concept_owned_by_us = False
        dataset_datas: list[DatasetFDOData] = []
        grant_ids = []

        if not concept_already_processed:
            # Mark concept as being processed by this call
            self._processing_datasets.add(dataset.concept_doi)
            concept_owned_by_us = True

            dataset_datas, file_datas, grant_datas = self._transform_to_exchange_models(
                dataset
            )

            logger.info(f"Creating {len(dataset_datas)} Dataset FDOs")
            await asyncio.gather(
                *[self.dataset_design.create_fdo(data) for data in dataset_datas]
            )

            logger.info(f"Creating {len(file_datas)} File FDOs")
            await asyncio.gather(
                *[self.file_design.create_fdo(data) for data in file_datas]
            )

            logger.info(f"Creating {len(grant_datas)} Grant FDOs")
            grant_ids = await asyncio.gather(
                *[self.grant_design.create_fdo(data) for data in grant_datas]
            )
            grant_ids = [gid for gid in grant_ids if gid is not None]
        else:
            logger.info(
                f"Concept {dataset.concept_doi} already processed, "
                f"skipping FDO creation for {doi}"
            )

        # Link datasets to grants via fundedBy relation (bidirectional via funds)
        for dataset_data in dataset_datas:
            dataset_placeholder = placeholder_pid(dataset_data.doi)
            record = self._record_graph[dataset_placeholder]
            for grant_id in grant_ids:
                record.addAttribute(INFOTYPES["fundedBy"], grant_id)
                grant_record = self._record_graph.get(grant_id)
                if grant_record:
                    grant_record.addAttribute(INFOTYPES["funds"], dataset_placeholder)

        # Always process references - each version may carry its own related
        # identifiers that need to be handled (e.g. a new version citing a work
        # that older versions did not reference). FDO records exist for every
        # version of the concept, so process each version individually.
        for version_doi, version in dataset.versions.items():
            # Skip versions already handled (shared across nested designs)
            if version_doi in self._processed_reference_versions:
                logger.debug(
                    f"Related identifiers already processed for version {version_doi}"
                )
                continue

            # Mark as processed before processing to avoid re-entry via cycles
            self._processed_reference_versions.add(version_doi)

            if not version.related_identifiers:
                continue

            # Only create forward links on versions that exist in the graph
            if placeholder_pid(version_doi) not in self._record_graph:
                logger.warning(
                    f"Skipping reference processing for {version_doi}: "
                    f"version FDO not found in graph"
                )
                continue

            logger.info(
                f"Processing {len(version.related_identifiers)} related "
                f"identifiers for version {version_doi}"
            )
            await self.reference_processor.process_all(
                version.related_identifiers,
                version_doi,
                dataset.concept_doi,
                depth,
            )

        # Mark as fully processed - remove from processing set and add to processed set
        self._processing_datasets.discard(doi)
        self._processed_datasets.add(doi)

        if concept_owned_by_us:
            self._processing_datasets.discard(dataset.concept_doi)
            self._processed_datasets.add(dataset.concept_doi)

        logger.info(f"Completed FDO creation for DOI: {doi}")

    async def _flush_cross_reference_backlinks(self) -> None:
        """Apply all deferred cross-dataset backlinks after FDO creation completes.

        Called once after all DOIs and their references have been processed.
        Ensures both source and target datasets exist in graph before creating links.

        This solves the race condition where backlinks were created during recursive
        processing before the target dataset existed in the graph. By deferring until
        all processing completes, we guarantee bidirectional links are never missed.

        Important: Only the TOP-LEVEL orchestrator should flush backlinks.
        Nested executions register backlinks but don't flush them, ensuring all
        datasets exist in the graph when the final flush occurs.

        Logs:
            INFO: Number of backlinks created vs skipped

        """
        # Only flush at top-level - nested designs share the same backlink manager
        # but shouldn't flush until ALL recursive processing completes
        if self._is_nested_execution:
            logger.debug(
                "Skipping backlink flush in nested execution - will be flushed by top-level orchestrator"
            )
            return

        success, skipped = self._backlink_manager.flush_backlinks()
        logger.info(
            f"Created {success} cross-dataset backlinks, skipped {skipped} (target not found)"
        )


__all__ = ["ZenodoFDODesign"]
