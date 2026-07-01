# SPDX-FileCopyrightText: 2025 Maximilian Inckmann <maximilian.inckmann@kit.edu>
# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for Zenodo FDO generation.

These tests verify the complete FDO generation workflow including:
- Graph structure and record relationships
- Profile compliance (Base + Versionable/DataResource/Publication)
- Backlink inference correctness
- Deduplication logic
"""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from fdo_usecases.designs.zenodo.constants import (
    BACKLINK_DATASET_FILE,
    BACKLINK_PUBLICATION_CITATION,
    BACKLINK_PUBLICATION_REFERENCE,
    BACKLINK_VERSION_CHAIN,
    BASE_PROFILE,
    DATARESOURCE_PROFILE,
    INFOTYPES,
    PROFILE_KEY,
    PUBLICATION_PROFILE,
    VERSIONABLE_PROFILE,
)
from fdo_usecases.designs.zenodo.designs.dataset import ZenodoDatasetDesign
from fdo_usecases.designs.zenodo.designs.file import ZenodoFileDesign
from fdo_usecases.designs.zenodo.designs.publication import PublicationDesign
from fdo_usecases.designs.zenodo.models import (
    Creator,
    Dataset,
    DatasetVersion,
    LicenseInfo,
    RelatedIdentifier,
    ZenodoFile,
)
from fdo_usecases.designs.zenodo.models.exchange import (
    DatasetFDOData,
    FileFDOData,
    PublicationFDOData,
)
from fdo_usecases.designs.zenodo.orchestrator import ZenodoFDODesign


@pytest.fixture
def real_world_dataset():
    """Create a realistic dataset with multiple versions, files, and references."""
    version1 = DatasetVersion(
        doi="10.5281/zenodo.111111",
        concept_doi="10.5281/zenodo.999999",
        recid=111111,
        title="Creep Reference Data v1",
        description="Initial release of creep reference data",
        publication_date=date(2024, 1, 15),
        version_label="1.0",
        creators=[
            Creator(
                name="Doe, John",
                affiliation="BAM",
                orcid="0000-0000-0000-0001",
                ror_id="https://ror.org/01234567",
            ),
            Creator(
                name="Smith, Jane",
                affiliation="Fraunhofer IWM",
                orcid="0000-0000-0000-0002",
            ),
        ],
        keywords=["creep", "superalloy", "reference data"],
        previous_version=None,
        next_version=None,
        license=LicenseInfo(
            id="cc-by-4.0",
            name="CC BY 4.0",
            url="https://creativecommons.org/licenses/by/4.0/",
        ),
        files={},
        metadata_raw={"doi": "10.5281/zenodo.111111"},
    )

    version2 = DatasetVersion(
        doi="10.5281/zenodo.222222",
        concept_doi="10.5281/zenodo.999999",
        recid=222222,
        title="Creep Reference Data v2",
        description="Updated with additional alloys",
        publication_date=date(2024, 6, 1),
        version_label="2.0",
        creators=[
            Creator(
                name="Doe, John",
                affiliation="BAM",
                orcid="0000-0000-0000-0001",
                ror_id="https://ror.org/01234567",
            ),
        ],
        keywords=["creep", "superalloy", "reference data", "updated"],
        previous_version=version1,
        next_version=None,
        license=LicenseInfo(
            id="cc-by-4.0",
            name="CC BY 4.0",
            url="https://creativecommons.org/licenses/by/4.0/",
        ),
        files={},
        metadata_raw={"doi": "10.5281/zenodo.222222"},
    )

    version1.next_version = version2

    file1 = ZenodoFile(
        checksum="md5:28573899cc09a145ac2c69fc1370c0bf",
        filename="data_v1.csv",
        size=1024,
        mimetype="text/csv",
        first_dataset_version="10.5281/zenodo.111111",
        first_dataset_recid=111111,
        present_in_versions=["10.5281/zenodo.111111"],
        download_url="https://zenodo.org/api/records/1/files/data_v1.csv",
    )

    file2 = ZenodoFile(
        checksum="md5:abcdef12345678901234567890abcdef",
        filename="data_v2.csv",
        size=2048,
        mimetype="text/csv",
        first_dataset_version="10.5281/zenodo.222222",
        first_dataset_recid=222222,
        present_in_versions=["10.5281/zenodo.222222"],
        download_url="https://zenodo.org/api/records/2/files/data_v2.csv",
    )

    file3 = ZenodoFile(
        checksum="md5:1234567890abcdef1234567890abcdef",
        filename="readme.txt",
        size=512,
        mimetype="text/plain",
        first_dataset_version="10.5281/zenodo.111111",
        first_dataset_recid=111111,
        present_in_versions=["10.5281/zenodo.111111", "10.5281/zenodo.222222"],
        download_url="https://zenodo.org/api/records/1/files/readme.txt",
    )

    related_ids = [
        RelatedIdentifier(
            identifier="10.1016/j.actamat.2025.120735",
            relation="cites",
            scheme="doi",
            resource_type="publication-article",
        ),
    ]

    dataset = Dataset(
        concept_doi="10.5281/zenodo.999999",
        concept_recid=999999,
        title="Creep Reference Data",
        description="Comprehensive creep reference data for nickel-based superalloys",
        latest_version_doi="10.5281/zenodo.222222",
        versions={"10.5281/zenodo.111111": version1, "10.5281/zenodo.222222": version2},
        all_files={
            "md5:28573899cc09a145ac2c69fc1370c0bf": file1,
            "md5:abcdef12345678901234567890abcdef": file2,
            "md5:1234567890abcdef1234567890abcdef": file3,
        },
        related_identifiers=related_ids,
    )

    return dataset


class TestFDOGraphStructure:
    """Test FDO graph structure and relationships."""

    @pytest.mark.asyncio
    async def test_complete_graph_generation(self, real_world_dataset):
        """Test that complete FDO graph is generated with all record types."""
        design = ZenodoFDODesign(doi="10.5281/zenodo.test")

        with patch.object(
            design,
            "_fetch_metadata",
            new_callable=AsyncMock,
            return_value=real_world_dataset,
        ):
            await design.execute_async()

        graph = design._record_graph

        # Verify we have records (2 datasets + 3 files + 1 publication = 6)
        assert len(graph) == 6
        assert "10.5281/zenodo.111111" in graph
        assert "10.5281/zenodo.222222" in graph
        assert "md5:28573899cc09a145ac2c69fc1370c0bf" in graph
        assert "md5:abcdef12345678901234567890abcdef" in graph
        assert "md5:1234567890abcdef1234567890abcdef" in graph
        assert "10.1016/j.actamat.2025.120735" in graph

    @pytest.mark.asyncio
    async def test_dataset_profile_compliance(self, real_world_dataset):
        """Test that Dataset FDOs comply with Base + Versionable profiles."""
        design = ZenodoFDODesign(doi="10.5281/zenodo.test")

        with patch.object(
            design,
            "_fetch_metadata",
            new_callable=AsyncMock,
            return_value=real_world_dataset,
        ):
            await design.execute_async()

        for version_doi in ["10.5281/zenodo.111111", "10.5281/zenodo.222222"]:
            record = design._record_graph[version_doi]

            # Convert tuples to dict for easier lookup
            attr_dict = {}
            for key, value in record._tuples:
                if key not in attr_dict:
                    attr_dict[key] = []
                attr_dict[key].append(value)

            profiles = attr_dict.get(PROFILE_KEY, [])
            assert BASE_PROFILE in profiles, f"{version_doi} missing Base profile"
            assert VERSIONABLE_PROFILE in profiles, (
                f"{version_doi} missing Versionable profile"
            )

            assert any(k == INFOTYPES["name"] for k in attr_dict.keys())
            assert any(k == INFOTYPES["dateCreated"] for k in attr_dict.keys())
            assert any(k == INFOTYPES["version"] for k in attr_dict.keys())

    @pytest.mark.asyncio
    async def test_file_profile_compliance(self, real_world_dataset):
        """Test that File FDOs comply with Base + DataResource profiles."""
        design = ZenodoFDODesign(doi="10.5281/zenodo.test")

        with patch.object(
            design,
            "_fetch_metadata",
            new_callable=AsyncMock,
            return_value=real_world_dataset,
        ):
            await design.execute_async()

        for checksum in real_world_dataset.all_files.keys():
            record = design._record_graph[checksum]

            # Convert tuples to dict for easier lookup
            attr_dict = {}
            for key, value in record._tuples:
                if key not in attr_dict:
                    attr_dict[key] = []
                attr_dict[key].append(value)

            profiles = attr_dict.get(PROFILE_KEY, [])
            assert BASE_PROFILE in profiles, f"{checksum} missing Base profile"
            assert DATARESOURCE_PROFILE in profiles, (
                f"{checksum} missing DataResource profile"
            )

            assert any(k == INFOTYPES["name"] for k in attr_dict.keys())
            assert any(k == INFOTYPES["dataObjectLocation"] for k in attr_dict.keys())
            assert any(k == INFOTYPES["checksum"] for k in attr_dict.keys())

    @pytest.mark.asyncio
    async def test_publication_profile_compliance(self, real_world_dataset):
        """Test that Publication FDOs comply with Base + Publication profiles."""
        design = ZenodoFDODesign(doi="10.5281/zenodo.test")

        with patch.object(
            design,
            "_fetch_metadata",
            new_callable=AsyncMock,
            return_value=real_world_dataset,
        ):
            await design.execute_async()

        pub_doi = "10.1016/j.actamat.2025.120735"
        record = design._record_graph[pub_doi]

        # Convert tuples to dict for easier lookup
        attr_dict = {}
        for key, value in record._tuples:
            if key not in attr_dict:
                attr_dict[key] = []
            attr_dict[key].append(value)

        profiles = attr_dict.get(PROFILE_KEY, [])
        assert BASE_PROFILE in profiles, f"{pub_doi} missing Base profile"
        assert PUBLICATION_PROFILE in profiles, f"{pub_doi} missing Publication profile"

        assert any(k == INFOTYPES["doi"] for k in attr_dict.keys())

    @pytest.mark.asyncio
    async def test_version_chain_relationships(self, real_world_dataset):
        """Test that version chain relationships are correctly established."""
        design = ZenodoFDODesign(doi="10.5281/zenodo.test")

        with patch.object(
            design,
            "_fetch_metadata",
            new_callable=AsyncMock,
            return_value=real_world_dataset,
        ):
            await design.execute_async()

        v1_record = design._record_graph["10.5281/zenodo.111111"]
        v2_record = design._record_graph["10.5281/zenodo.222222"]

        # Convert tuples to dict for easier lookup
        v1_attrs = {k: v for k, v in v1_record._tuples}
        v2_attrs = {k: v for k, v in v2_record._tuples}

        assert INFOTYPES["nextVersion"] in v1_attrs
        assert v1_attrs[INFOTYPES["nextVersion"]] == "10.5281/zenodo.222222"

        assert INFOTYPES["previousVersion"] in v2_attrs
        assert v2_attrs[INFOTYPES["previousVersion"]] == "10.5281/zenodo.111111"

        assert INFOTYPES["latestVersion"] in v1_attrs
        assert v1_attrs[INFOTYPES["latestVersion"]] == "10.5281/zenodo.222222"

        assert INFOTYPES["latestVersion"] not in v2_attrs

    @pytest.mark.asyncio
    async def test_backlink_structure(self, real_world_dataset):
        """Test that backlinks are correctly defined for Executor inference."""
        # Note: Backlinks are stored on RecordDesign for Executor-based inference
        # Backlinks are added during create_fdo() calls

        # Create designs and call create_fdo to trigger backlink registration
        dataset_design = ZenodoDatasetDesign()
        dataset_data = DatasetFDOData(
            doi="10.5281/zenodo.test",
            title="Test",
            description="Test",
            publication_date=date(2024, 1, 1),
            version_label="1.0",
        )
        await dataset_design.create_fdo(dataset_data)

        file_design = ZenodoFileDesign()
        file_data = FileFDOData(
            checksum="md5:1234567890abcdef1234567890abcdef",
            filename="test.txt",
            download_url="https://example.com/test.txt",
        )
        await file_design.create_fdo(file_data)

        publication_design = PublicationDesign()
        pub_data = PublicationFDOData(identifier="10.1000/test")
        await publication_design.create_fdo(pub_data)

        # Verify designs have correct backlinks configured after create_fdo
        assert BACKLINK_DATASET_FILE in dataset_design._backlinks  # type: ignore[attr-defined]
        assert BACKLINK_VERSION_CHAIN in dataset_design._backlinks  # type: ignore[attr-defined]
        assert BACKLINK_DATASET_FILE in file_design._backlinks  # type: ignore[attr-defined]
        assert BACKLINK_PUBLICATION_CITATION in publication_design._backlinks  # type: ignore[attr-defined]
        assert BACKLINK_PUBLICATION_REFERENCE in publication_design._backlinks  # type: ignore[attr-defined]


class TestCreatorAndAffiliationData:
    """Test creator ORCID and ROR ID handling."""

    @pytest.mark.asyncio
    async def test_creator_orcids_included(self, real_world_dataset):
        """Test that creator ORCIDs are included in Dataset FDOs."""
        design = ZenodoFDODesign(doi="10.5281/zenodo.test")

        with patch.object(
            design,
            "_fetch_metadata",
            new_callable=AsyncMock,
            return_value=real_world_dataset,
        ):
            await design.execute_async()

        v1_record = design._record_graph["10.5281/zenodo.111111"]
        # Collect all values for each key (lists are flattened by PidRecord)
        attr_dict = {}
        for k, v in v1_record._tuples:
            if k not in attr_dict:
                attr_dict[k] = []
            attr_dict[k].append(v)

        assert INFOTYPES["creator"] in attr_dict
        orcids = attr_dict[INFOTYPES["creator"]]
        assert "0000-0000-0000-0001" in orcids
        assert "0000-0000-0000-0002" in orcids

    @pytest.mark.asyncio
    async def test_ror_ids_included(self, real_world_dataset):
        """Test that ROR IDs are included when available."""
        design = ZenodoFDODesign(doi="10.5281/zenodo.test")

        with patch.object(
            design,
            "_fetch_metadata",
            new_callable=AsyncMock,
            return_value=real_world_dataset,
        ):
            await design.execute_async()

        v1_record = design._record_graph["10.5281/zenodo.111111"]
        attr_dict = {k: v for k, v in v1_record._tuples}

        assert INFOTYPES["creatorAffiliation"] in attr_dict
        ror_ids = attr_dict[INFOTYPES["creatorAffiliation"]]
        assert "https://ror.org/01234567" in ror_ids


class TestFileDeduplication:
    """Test file deduplication across versions."""

    @pytest.mark.asyncio
    async def test_shared_file_single_record(self, real_world_dataset):
        """Test that files appearing in multiple versions get single FDO record."""
        design = ZenodoFDODesign(doi="10.5281/zenodo.test")

        with patch.object(
            design,
            "_fetch_metadata",
            new_callable=AsyncMock,
            return_value=real_world_dataset,
        ):
            await design.execute_async()

        readme_checksum = "md5:1234567890abcdef1234567890abcdef"
        assert readme_checksum in design._record_graph

        readme_record = design._record_graph[readme_checksum]
        assert readme_record.getId() == readme_checksum

        versions_with_readme = [
            v for v in real_world_dataset.all_files[readme_checksum].present_in_versions
        ]
        assert len(versions_with_readme) == 2

    @pytest.mark.asyncio
    async def test_unique_files_per_version(self, real_world_dataset):
        """Test that unique files get their own FDO records."""
        design = ZenodoFDODesign(doi="10.5281/zenodo.test")

        with patch.object(
            design,
            "_fetch_metadata",
            new_callable=AsyncMock,
            return_value=real_world_dataset,
        ):
            await design.execute_async()

        v1_only = "md5:28573899cc09a145ac2c69fc1370c0bf"
        v2_only = "md5:abcdef12345678901234567890abcdef"

        assert v1_only in design._record_graph
        assert v2_only in design._record_graph

        v1_record = design._record_graph[v1_only]
        v2_record = design._record_graph[v2_only]

        assert v1_record.getId() != v2_record.getId()


class TestLicenseHandling:
    """Test license URL propagation from datasets to files."""

    @pytest.mark.asyncio
    async def test_file_license_from_parent_dataset(self, real_world_dataset):
        """Test that files inherit license URL from parent dataset."""
        design = ZenodoFDODesign(doi="10.5281/zenodo.test")

        with patch.object(
            design,
            "_fetch_metadata",
            new_callable=AsyncMock,
            return_value=real_world_dataset,
        ):
            await design.execute_async()

        for checksum in real_world_dataset.all_files.keys():
            record = design._record_graph[checksum]
            attr_dict = {k: v for k, v in record._tuples}
            assert INFOTYPES["spdxLicense"] in attr_dict
            license_url = attr_dict[INFOTYPES["spdxLicense"]]
            assert "creativecommons.org" in str(license_url)


class TestKeywordsAndMetadata:
    """Test keyword and metadata handling."""

    @pytest.mark.asyncio
    async def test_keywords_included(self, real_world_dataset):
        """Test that keywords are included in Dataset FDOs."""
        design = ZenodoFDODesign(doi="10.5281/zenodo.test")

        with patch.object(
            design,
            "_fetch_metadata",
            new_callable=AsyncMock,
            return_value=real_world_dataset,
        ):
            await design.execute_async()

        v1_record = design._record_graph["10.5281/zenodo.111111"]
        # Collect all values for each key (lists are flattened by PidRecord)
        attr_dict = {}
        for k, v in v1_record._tuples:
            if k not in attr_dict:
                attr_dict[k] = []
            attr_dict[k].append(v)

        assert INFOTYPES["keyword"] in attr_dict
        keywords = attr_dict[INFOTYPES["keyword"]]
        assert "creep" in keywords
        assert "superalloy" in keywords
        assert "reference data" in keywords

        v2_record = design._record_graph["10.5281/zenodo.222222"]
        attr_dict_v2 = {}
        for k, v in v2_record._tuples:
            if k not in attr_dict_v2:
                attr_dict_v2[k] = []
            attr_dict_v2[k].append(v)
        keywords_v2 = attr_dict_v2[INFOTYPES["keyword"]]
        assert "updated" in keywords_v2


class TestRecordIdentity:
    """Test record identity assignment."""

    @pytest.mark.asyncio
    async def test_dataset_identity_is_doi(self, real_world_dataset):
        """Test that Dataset FDOs use DOI as record ID."""
        design = ZenodoFDODesign(doi="10.5281/zenodo.test")

        with patch.object(
            design,
            "_fetch_metadata",
            new_callable=AsyncMock,
            return_value=real_world_dataset,
        ):
            await design.execute_async()

        for version_doi in real_world_dataset.versions.keys():
            record = design._record_graph[version_doi]
            assert record.getId() == version_doi

    @pytest.mark.asyncio
    async def test_file_identity_is_checksum(self, real_world_dataset):
        """Test that File FDOs use checksum as record ID."""
        design = ZenodoFDODesign(doi="10.5281/zenodo.test")

        with patch.object(
            design,
            "_fetch_metadata",
            new_callable=AsyncMock,
            return_value=real_world_dataset,
        ):
            await design.execute_async()

        for checksum in real_world_dataset.all_files.keys():
            record = design._record_graph[checksum]
            assert record.getId() == checksum

    @pytest.mark.asyncio
    async def test_publication_identity_is_identifier(self, real_world_dataset):
        """Test that Publication FDOs use identifier as record ID."""
        design = ZenodoFDODesign(doi="10.5281/zenodo.test")

        with patch.object(
            design,
            "_fetch_metadata",
            new_callable=AsyncMock,
            return_value=real_world_dataset,
        ):
            await design.execute_async()

        pub_doi = "10.1016/j.actamat.2025.120735"
        record = design._record_graph[pub_doi]
        assert record.getId() == pub_doi
