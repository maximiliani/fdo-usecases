"""Zenodo FDO design module.

This module provides the ZenodoDesign class for creating FAIR Digital Objects (FDOs)
from Zenodo dataset metadata. It generates FDO records compliant with the BAM
creep-reference profiles for datasets, files, and publications.

Profile Compliance:
- All Dataset FDOs comply with Base + Versionable profiles
- All File FDOs comply with Base + DataResource profiles
- All Publication FDOs comply with Base + Publication profiles

Structure:
- One Dataset FDO per version (linked via previous/next version pointers)
- One File FDO per unique checksum (deduplicated across all versions)
- One Publication FDO per related identifier with DOI
- Recursive handling for Zenodo-related datasets (with deduplication)
"""

import asyncio
import re
from typing import TYPE_CHECKING, Any, Callable

from fdo_usecases.designer_lib.executor import RecordDesign

from .zenodo_metadata_extractor.fetcher import ZenodoDatasetFetcher
from .zenodo_metadata_extractor.models import Dataset, DatasetVersion

if TYPE_CHECKING:
    from .zenodo_metadata_extractor.models import ZenodoFile

PROFILE_KEY = "21.T11148/076759916209e5d62bd5"

BASE_PROFILE = "21.T11969/077fe9c54ed5ed26fa54"
VERSIONABLE_PROFILE = "21.T11969/6c663a0695a411803d70"
DATARESOURCE_PROFILE = "21.T11969/0738c2ef35faef0fb552"
PUBLICATION_PROFILE = "21.T11969/e00441c49bf6cb62a4a5"

INFOTYPES = {
    "creator": "21.T11969/7c67083a5d218e544063",
    "creatorAffiliation": "21.T11969/ea9f6b3d78c6608fe801",
    "dateCreated": "21.T11969/29f92bd203dd3eaa5a1f",
    "dateModified": "21.T11969/397d831aa3a9d18eb52c",
    "keyword": "21.T11969/793ff5c33c3aeb32907a",
    "name": "21.T11969/bd3e9fb9b606d2198c9e",
    "description": "21.T11969/880724416f5857987e70",
    "mimeType": "21.T11969/3313b863118ed5eb0ded",
    "dataObjectLocation": "21.T11969/479febb2bbe8400da547",
    "spdxLicense": "21.T11969/623654b1072ae7b88202",
    "checksum": "21.T11969/a80ed2ef79e22f1d8af8",
    "version": "21.T11969/be1ae3492b235faad933",
    "nextVersion": "21.T11969/7f1a6afddcfeefbf195b",
    "previousVersion": "21.T11969/7c97f00a2a95826c1a8f",
    "latestVersion": "21.T11969/2b4d6ceda80ddd63f7a9",
    "doi": "21.T11969/48e563f148dc04d8b31c",
    "dataCitePublicationType": "21.T11969/48dbf6a89f9748ae4ead",
    "publisher": "21.T11969/cdd96207a7dfbcc0db93",
    "datePublished": "21.T11969/0c9b86e828976a85d4f2",
}


def _strip_html_and_truncate(text: str | None, max_words: int = 500) -> str | None:
    """Remove HTML tags and truncate text to maximum word count.

    Args:
        text: Input text potentially containing HTML
        max_words: Maximum number of words (default: 500)

    Returns:
        Cleaned text or None if input was None

    """
    if not text:
        return None

    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"\s+", " ", clean).strip()

    words = clean.split()
    if len(words) > max_words:
        return " ".join(words[:max_words]) + "..."

    return clean


class ZenodoDesign(RecordDesign):
    """Zenodo dataset record design.

    Creates FDO records from Zenodo dataset metadata. Accepts a DOI as input
    and generates compliant FDOs for:
    - Dataset versions (Base + Versionable profiles)
    - Files (Base + DataResource profiles)
    - Related publications (Base + Publication profiles)
    - Nested Zenodo datasets (recursive with deduplication)

    Attributes:
        doi: Input DOI for the dataset to process

    """

    def __init__(self, doi: str):
        """Initialize Zenodo design with DOI.

        Args:
            doi: Digital Object Identifier of the dataset

        """
        super().__init__()
        self.doi = doi
        self._processed_datasets: set[str] = set()
        self._dataset: Dataset | None = None
        self._records_created: list[tuple[str, dict]] = []

    def _create_dataset_fdo(self, version: DatasetVersion, dataset: Dataset) -> str:
        """Create FDO record for a dataset version.

        Creates a record compliant with Base and Versionable profiles.

        Args:
            version: DatasetVersion object to create FDO for
            dataset: Parent Dataset object for context

        Returns:
            Record ID (the version DOI)

        """
        record_id = version.doi

        profiles: list[str] = [BASE_PROFILE, VERSIONABLE_PROFILE]

        def get_profiles() -> list[str]:
            return profiles

        def get_title() -> str:
            return version.title

        def get_description() -> str | None:
            return _strip_html_and_truncate(version.description)

        def get_date_created() -> str:
            return version.publication_date.isoformat()

        def get_creators() -> list[str]:
            return [c.orcid for c in version.creators if c.orcid]

        def get_ror_ids() -> list[str]:
            return [c.ror_id for c in version.creators if c.ror_id]

        def get_keywords() -> list[str]:
            return version.keywords

        def get_version_label() -> str:
            return version.version_label

        self.addAttribute(PROFILE_KEY, get_profiles)
        self.addAttribute(INFOTYPES["name"], get_title)
        self.addAttribute(INFOTYPES["description"], get_description)
        self.addAttribute(INFOTYPES["dateCreated"], get_date_created)

        creators_orcid: list[str] = [c.orcid for c in version.creators if c.orcid]
        if creators_orcid:
            self.addAttribute(INFOTYPES["creator"], get_creators)

        creator_ror: list[str] = [c.ror_id for c in version.creators if c.ror_id]
        if creator_ror:
            self.addAttribute(INFOTYPES["creatorAffiliation"], get_ror_ids)

        if version.keywords:
            self.addAttribute(INFOTYPES["keyword"], get_keywords)

        self.addAttribute(INFOTYPES["version"], get_version_label)

        if version.previous_version:
            prev_doi = version.previous_version.doi

            def get_prev_version() -> str:
                return prev_doi

            self.addAttribute(INFOTYPES["previousVersion"], get_prev_version)

        if version.next_version:
            next_doi = version.next_version.doi

            def get_next_version() -> str:
                return next_doi

            self.addAttribute(INFOTYPES["nextVersion"], get_next_version)

        latest_doi = dataset.latest_version_doi
        if latest_doi != version.doi:

            def get_latest_version() -> str:
                return latest_doi

            self.addAttribute(INFOTYPES["latestVersion"], get_latest_version)

        def get_record_id() -> str:
            return record_id

        self.setId(get_record_id)
        self.setPid(lambda: "")

        self.addBacklink("isNewVersionOf", "isPreviousVersionOf")
        self.addBacklink("hasData", "isPartOf")

        return record_id

    def _create_file_fdos(self, dataset: Dataset) -> list[str]:
        """Create FDO records for all unique files in dataset.

        Creates one record per unique checksum, compliant with Base and
        DataResource profiles.

        Args:
            dataset: Dataset object containing files

        Returns:
            List of created record IDs (checksums)

        """
        record_ids: list[str] = []

        for checksum, file_obj in dataset.all_files.items():
            record_id = checksum
            record_ids.append(record_id)

            def make_add_file_attrs(fo: ZenodoFile, rid: str) -> Callable[[], None]:
                profiles: list[str] = [BASE_PROFILE, DATARESOURCE_PROFILE]

                def add_attrs() -> None:
                    self.addAttribute(PROFILE_KEY, lambda: profiles)
                    self.addAttribute(INFOTYPES["name"], lambda: fo.filename)
                    self.addAttribute(INFOTYPES["mimeType"], lambda: fo.mimetype)
                    self.addAttribute(
                        INFOTYPES["dataObjectLocation"], lambda: str(fo.download_url)
                    )
                    self.addAttribute(INFOTYPES["checksum"], lambda: fo.checksum)

                    lic_url: str | None = None
                    for vdoi in fo.present_in_versions:
                        if vdoi in dataset.versions:
                            ver = dataset.versions[vdoi]
                            if ver.license and ver.license.url:
                                lic_url = str(ver.license.url)
                                break

                    if lic_url:
                        self.addAttribute(INFOTYPES["spdxLicense"], lambda: lic_url)

                    self.setId(lambda: rid)
                    self.setPid(lambda: "")
                    self.addBacklink("isPartOf", "hasData")

                return add_attrs

            add_file_attrs = make_add_file_attrs(file_obj, record_id)
            add_file_attrs()

        return record_ids

    def _create_publication_fdo(
        self, identifier: str, rel_data: dict[str, Any] | None = None
    ) -> str:
        """Create FDO record for a related publication.

        Creates a record compliant with Base and Publication profiles.

        Args:
            identifier: DOI or other persistent identifier
            rel_data: Optional metadata about the publication

        Returns:
            Record ID (the identifier)

        """
        record_id = identifier

        profiles: list[str] = [BASE_PROFILE, PUBLICATION_PROFILE]

        def get_pub_profiles() -> list[str]:
            return profiles

        def get_doi() -> str:
            return identifier

        self.addAttribute(PROFILE_KEY, get_pub_profiles)
        self.addAttribute(INFOTYPES["doi"], get_doi)

        if rel_data:
            pub_type = rel_data.get("resource_type", "Other")

            def get_pub_type() -> str:
                return pub_type

            self.addAttribute(INFOTYPES["dataCitePublicationType"], get_pub_type)

            publisher = rel_data.get("publisher")
            if publisher:

                def get_publisher() -> str:
                    return publisher

                self.addAttribute(INFOTYPES["publisher"], get_publisher)

            pub_date = rel_data.get("publication_date")
            if pub_date:

                def get_pub_date() -> str:
                    return pub_date  # type: ignore[return-value]

                self.addAttribute(INFOTYPES["datePublished"], get_pub_date)

            title = rel_data.get("title")
            if title:

                def get_title() -> str:
                    return title

                self.addAttribute(INFOTYPES["name"], get_title)

            description = rel_data.get("description")
            if description:
                desc = _strip_html_and_truncate(description)

                def get_desc() -> str | None:
                    return desc

                self.addAttribute(INFOTYPES["description"], get_desc)

            creators = rel_data.get("creators", [])
            creator_orcids: list[str] = [
                c.get("orcid")
                for c in creators
                if isinstance(c, dict) and c.get("orcid")
            ]
            if creator_orcids:

                def get_creator_orcids() -> list[str]:
                    return creator_orcids

                self.addAttribute(INFOTYPES["creator"], get_creator_orcids)

        def get_pub_id() -> str:
            return record_id

        self.setId(get_pub_id)
        self.setPid(lambda: "")

        self.addBacklink("cites", "isCitedBy")
        self.addBacklink("references", "isReferencedBy")

        return record_id

    async def _fetch_metadata(self) -> Dataset:
        """Fetch and cache Zenodo metadata.

        Returns:
            Complete Dataset object with all versions and files

        """
        if self._dataset is None:
            fetcher = ZenodoDatasetFetcher(cache_enabled=True)
            self._dataset = await fetcher.fetch_by_doi(self.doi)
        return self._dataset

    def _process_related_identifiers(self, dataset: Dataset) -> None:
        """Process related identifiers and create Publication FDOs.

        For each related identifier:
        - If it's a Zenodo DOI, recursively fetch and create Dataset FDOs
        - Otherwise, create a Publication FDO with available metadata

        Args:
            dataset: Dataset object with related identifiers

        """
        for rel in dataset.related_identifiers:
            identifier = rel.identifier

            if "zenodo" in identifier.lower():
                if identifier not in self._processed_datasets:
                    nested_design = ZenodoDesign(identifier)
                    nested_design._processed_datasets = self._processed_datasets

                    async def fetch_nested(design: ZenodoDesign) -> None:
                        nested_dataset = await design._fetch_metadata()
                        design._create_all_fdos(nested_dataset)

                    asyncio.run(fetch_nested(nested_design))
            else:
                self._create_publication_fdo(identifier, None)

    def _create_all_fdos(self, dataset: Dataset) -> None:
        """Create all FDO records for a dataset.

        Creates:
        1. Dataset FDOs for each version
        2. File FDOs for each unique checksum
        3. Publication FDOs for related identifiers

        Args:
            dataset: Complete Dataset object

        """
        for version in dataset.versions.values():
            self._create_dataset_fdo(version, dataset)

        self._create_file_fdos(dataset)

        self._process_related_identifiers(dataset)

    def execute(self) -> None:
        """Execute the design and create all FDO records.

        Fetches metadata from Zenodo and creates compliant FDO records
        for datasets, files, and publications.

        """
        if self.doi in self._processed_datasets:
            print(f"Skipping already processed dataset: {self.doi}")
            return

        self._processed_datasets.add(self.doi)

        async def run() -> None:
            dataset = await self._fetch_metadata()
            self._create_all_fdos(dataset)

        asyncio.run(run())
