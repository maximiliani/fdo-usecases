# SPDX-FileCopyrightText: 2025 Maximilian Inckmann <maximilian.inckmann@kit.edu>
# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for ZenodoFDODesign orchestrator."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fdo_usecases.designer_lib.executor import PidRecord
from fdo_usecases.designs.zenodo.models import (
    Creator,
    Dataset,
    DatasetVersion,
    RelatedIdentifier,
    ZenodoFile,
)
from fdo_usecases.designs.zenodo.models.exchange import (
    CreatorData,
)
from fdo_usecases.designs.zenodo.orchestrator import ZenodoFDODesign


@pytest.fixture
def mock_dataset():
    """Create a mock Dataset with versions and files."""
    version1 = DatasetVersion(
        doi="10.5281/zenodo.111111",
        concept_doi="10.5281/zenodo.999999",
        recid=111111,
        title="Test Dataset v1",
        description="First version",
        publication_date=date(2024, 1, 1),
        version_label="1.0",
        creators=[
            Creator(
                name="Doe, John",
                affiliation="BAM",
                orcid="0000-0000-0000-0001",
                ror_id="https://ror.org/01234567",
            )
        ],
        keywords=["test"],
        previous_version=None,
        next_version=None,
        license=None,
        files={},
        metadata_raw={"doi": "10.5281/zenodo.111111"},
    )

    version2 = DatasetVersion(
        doi="10.5281/zenodo.222222",
        concept_doi="10.5281/zenodo.999999",
        recid=222222,
        title="Test Dataset v2",
        description="Second version",
        publication_date=date(2024, 6, 1),
        version_label="2.0",
        creators=[
            Creator(
                name="Doe, John",
                affiliation="BAM",
                orcid="0000-0000-0000-0001",
                ror_id="https://ror.org/01234567",
            )
        ],
        keywords=["test", "updated"],
        previous_version=version1,
        next_version=None,
        license=None,
        files={},
        metadata_raw={"doi": "10.5281/zenodo.222222"},
    )

    version1.next_version = version2

    file1 = ZenodoFile(
        checksum="md5:28573899cc09a145ac2c69fc1370c0bf",
        filename="data.csv",
        size=1024,
        mimetype="text/csv",
        first_dataset_version="10.5281/zenodo.111111",
        first_dataset_recid=111111,
        present_in_versions=["10.5281/zenodo.111111", "10.5281/zenodo.222222"],
        download_url="https://zenodo.org/api/records/1/files/data.csv",
    )

    dataset = Dataset(
        concept_doi="10.5281/zenodo.999999",
        concept_recid=999999,
        title="Test Dataset",
        description="Test dataset with multiple versions",
        latest_version_doi="10.5281/zenodo.222222",
        versions={"10.5281/zenodo.111111": version1, "10.5281/zenodo.222222": version2},
        all_files={"md5:28573899cc09a145ac2c69fc1370c0bf": file1},
        related_identifiers=[],
    )

    return dataset


@pytest.fixture
def mock_dataset_with_references():
    """Create a mock Dataset with related identifiers on a version."""
    related_ids = [
        RelatedIdentifier(
            identifier="10.5281/zenodo.999999",
            relation="cites",
            scheme="doi",
            resource_type="dataset",
        ),
        RelatedIdentifier(
            identifier="10.1016/j.actamat.2025.120735",
            relation="cites",
            scheme="doi",
            resource_type="publication-article",
        ),
    ]

    version1 = DatasetVersion(
        doi="10.5281/zenodo.111111",
        concept_doi="10.5281/zenodo.999999",
        recid=111111,
        title="Dataset with References",
        description="Has references",
        publication_date=date(2024, 1, 1),
        version_label="1.0",
        creators=[],
        keywords=[],
        previous_version=None,
        next_version=None,
        license=None,
        files={},
        related_identifiers=related_ids,
        metadata_raw={"doi": "10.5281/zenodo.111111"},
    )

    file1 = ZenodoFile(
        checksum="md5:abcdef12345678901234567890abcdef",
        filename="file.txt",
        size=512,
        mimetype="text/plain",
        first_dataset_version="10.5281/zenodo.111111",
        first_dataset_recid=111111,
        present_in_versions=["10.5281/zenodo.111111"],
        download_url="https://zenodo.org/api/records/1/files/file.txt",
    )

    dataset = Dataset(
        concept_doi="10.5281/zenodo.999999",
        concept_recid=999999,
        title="Dataset with References",
        description="Has references",
        latest_version_doi="10.5281/zenodo.111111",
        versions={"10.5281/zenodo.111111": version1},
        all_files={"md5:abcdef12345678901234567890abcdef": file1},
    )

    return dataset


@pytest.mark.asyncio
async def test_orchestrator_initialization():
    """Test ZenodoFDODesign initialization."""
    design = ZenodoFDODesign(dois=["10.5281/zenodo.test"])

    assert design.dois[0] == "10.5281/zenodo.test"
    assert isinstance(design._processed_datasets, set)
    # assert design._dataset is None  # Attribute removed
    assert hasattr(design, "dataset_design")
    assert hasattr(design, "file_design")
    assert hasattr(design, "publication_design")
    assert hasattr(design, "reference_processor")


@pytest.mark.asyncio
async def test_fetch_metadata_caching(mock_dataset):
    """Test metadata fetching and caching."""
    design = ZenodoFDODesign(dois=["10.5281/zenodo.test"])

    with patch(
        "fdo_usecases.designs.zenodo.orchestrator.ZenodoDatasetFetcher"
    ) as mock_fetcher_class:
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_by_doi = AsyncMock(return_value=mock_dataset)
        mock_fetcher_class.return_value = mock_fetcher

        result1 = await design._fetch_metadata("10.5281/zenodo.test")
        result2 = await design._fetch_metadata("10.5281/zenodo.test")

        assert result1 is mock_dataset
        assert result2 is mock_dataset
        mock_fetcher.fetch_by_doi.assert_called_with("10.5281/zenodo.test")


@pytest.mark.asyncio
async def test_transform_to_exchange_models(mock_dataset):
    """Test transformation of metadata to exchange models."""
    design = ZenodoFDODesign(dois=["10.5281/zenodo.test"])
    dataset_datas, file_datas, _ = design._transform_to_exchange_models(mock_dataset)

    assert len(dataset_datas) == 2
    assert len(file_datas) == 1

    assert dataset_datas[0].doi == "10.5281/zenodo.111111"
    assert dataset_datas[0].title == "Test Dataset v1"
    assert dataset_datas[0].version_label == "1.0"
    assert len(dataset_datas[0].creators) == 1
    assert dataset_datas[0].creators[0].orcid == "https://orcid.org/0000-0000-0000-0001"

    assert dataset_datas[1].doi == "10.5281/zenodo.222222"
    assert dataset_datas[1].previous_version_doi == "10.5281/zenodo.111111"
    assert dataset_datas[1].next_version_doi is None

    assert file_datas[0].checksum == "md5:28573899cc09a145ac2c69fc1370c0bf"
    assert file_datas[0].filename == "data.csv"


@pytest.mark.asyncio
async def test_execute_async_processes_all(mock_dataset):
    """Test that execute_async processes datasets, files, and references."""
    design = ZenodoFDODesign(dois=["10.5281/zenodo.test"])

    with (
        patch.object(
            design, "_fetch_metadata", new_callable=AsyncMock, return_value=mock_dataset
        ),
        patch.object(
            design.dataset_design, "create_fdo", new_callable=AsyncMock
        ) as mock_ds,
        patch.object(
            design.file_design, "create_fdo", new_callable=AsyncMock
        ) as mock_file,
        patch.object(
            design.reference_processor, "process_all", new_callable=AsyncMock
        ) as mock_refs,
    ):
        # Pre-populate graph with version FDOs (create_fdo is mocked)
        for version_doi in ["10.5281/zenodo.111111", "10.5281/zenodo.222222"]:
            design._record_graph[version_doi] = PidRecord().setId(version_doi)

        await design.execute_async()

        assert design.dois[0] in design._processed_datasets
        assert mock_ds.call_count == 2
        assert mock_file.call_count == 1
        # Versions carry no related identifiers -> no reference processing
        mock_refs.assert_not_called()
        assert design._processed_reference_versions == {
            "10.5281/zenodo.111111",
            "10.5281/zenodo.222222",
        }


@pytest.mark.asyncio
async def test_execute_async_skips_already_processed():
    """Test that already processed datasets are skipped."""
    design = ZenodoFDODesign(dois=["10.5281/zenodo.test"])
    design._processed_datasets.add("10.5281/zenodo.test")

    with patch.object(design, "_fetch_metadata", new_callable=AsyncMock) as mock_fetch:
        await design.execute_async()
        mock_fetch.assert_not_called()


def test_execute_sync():
    """Test synchronous execution wrapper."""
    design = ZenodoFDODesign(dois=["10.5281/zenodo.test"])

    with (
        patch.object(design, "execute_async", new_callable=AsyncMock) as mock_async,
        patch.object(design, "_fetch_metadata", new_callable=AsyncMock),
        patch.object(design.dataset_design, "create_fdo", new_callable=AsyncMock),
        patch.object(design.file_design, "create_fdo", new_callable=AsyncMock),
        patch.object(design.reference_processor, "process_all", new_callable=AsyncMock),
    ):
        design.execute()
        mock_async.assert_called_once()


@pytest.mark.asyncio
async def test_process_zenodo_reference():
    """Test processing nested Zenodo reference."""
    design = ZenodoFDODesign(dois=["10.5281/zenodo.parent"])
    design._processed_datasets.add("10.5281/zenodo.parent")

    captured_sets = []

    class MockNestedDesign:
        def __init__(self, dois, max_concurrent=10):
            self.dois = dois if isinstance(dois, list) else [dois]

        async def execute_async(self):
            pass

        @property
        def _processed_datasets(self):
            return self._stored_set

        @_processed_datasets.setter
        def _processed_datasets(self, value):
            captured_sets.append(value)
            self._stored_set = value

    with patch(
        "fdo_usecases.designs.zenodo.orchestrator.ZenodoFDODesign", MockNestedDesign
    ):
        await design._process_zenodo_reference("10.5281/zenodo.child")
        # Verify _processed_datasets was shared (second assignment after init)
        assert len(captured_sets) >= 1
        assert captured_sets[-1] is design._processed_datasets


@pytest.mark.asyncio
async def test_execute_with_references(mock_dataset_with_references):
    """Test execution processes related identifiers."""
    design = ZenodoFDODesign(dois=["10.5281/zenodo.test"])

    with (
        patch.object(
            design,
            "_fetch_metadata",
            new_callable=AsyncMock,
            return_value=mock_dataset_with_references,
        ),
        patch.object(design.dataset_design, "create_fdo", new_callable=AsyncMock),
        patch.object(design.file_design, "create_fdo", new_callable=AsyncMock),
        patch.object(
            design.reference_processor, "process_all", new_callable=AsyncMock
        ) as mock_proc,
    ):
        # Pre-populate graph with version FDOs (create_fdo is mocked)
        design._record_graph["10.5281/zenodo.111111"] = PidRecord().setId(
            "10.5281/zenodo.111111"
        )
        await design.execute_async()

    mock_proc.assert_called_once()
    called_ids, referencing_doi, concept_doi, depth = mock_proc.call_args[0]
    assert len(called_ids) == 2
    assert referencing_doi == "10.5281/zenodo.111111"
    assert concept_doi == "10.5281/zenodo.999999"
    assert depth == 0


@pytest.mark.asyncio
async def test_processes_references_for_each_version():
    """Each version's related identifiers are processed with its own DOI."""
    related_ids = [
        RelatedIdentifier(
            identifier="10.1016/j.actamat.2025.120735",
            relation="cites",
            scheme="doi",
            resource_type="publication-article",
        )
    ]
    version1 = DatasetVersion(
        doi="10.5281/zenodo.111111",
        concept_doi="10.5281/zenodo.999999",
        recid=111111,
        title="Dataset v1",
        publication_date=date(2024, 1, 1),
        version_label="1.0",
        creators=[],
        keywords=[],
        files={},
        related_identifiers=related_ids,
        metadata_raw={"doi": "10.5281/zenodo.111111"},
    )
    version2 = DatasetVersion(
        doi="10.5281/zenodo.222222",
        concept_doi="10.5281/zenodo.999999",
        recid=222222,
        title="Dataset v2",
        publication_date=date(2024, 6, 1),
        version_label="2.0",
        creators=[],
        keywords=[],
        files={},
        related_identifiers=[],
        metadata_raw={"doi": "10.5281/zenodo.222222"},
    )

    dataset = Dataset(
        concept_doi="10.5281/zenodo.999999",
        concept_recid=999999,
        title="Dataset",
        latest_version_doi="10.5281/zenodo.222222",
        versions={
            "10.5281/zenodo.111111": version1,
            "10.5281/zenodo.222222": version2,
        },
        all_files={},
    )

    design = ZenodoFDODesign(dois=["10.5281/zenodo.222222"])

    with (
        patch.object(
            design,
            "_fetch_metadata",
            new_callable=AsyncMock,
            return_value=dataset,
        ),
        patch.object(design.dataset_design, "create_fdo", new_callable=AsyncMock),
        patch.object(design.file_design, "create_fdo", new_callable=AsyncMock),
        patch.object(
            design.reference_processor, "process_all", new_callable=AsyncMock
        ) as mock_proc,
    ):
        # Pre-populate graph with version FDOs (create_fdo is mocked)
        for version_doi in ["10.5281/zenodo.111111", "10.5281/zenodo.222222"]:
            design._record_graph[version_doi] = PidRecord().setId(version_doi)

        await design.execute_async()

    # Only the old version carries a reference -> processed exactly once
    mock_proc.assert_called_once()
    called_ids, referencing_doi, concept_doi, depth = mock_proc.call_args[0]
    assert called_ids == related_ids
    assert referencing_doi == "10.5281/zenodo.111111"
    assert concept_doi == "10.5281/zenodo.999999"
    assert depth == 0


@pytest.mark.asyncio
async def test_skips_already_processed_reference_versions(mock_dataset_with_references):
    """Versions already marked as reference-processed are skipped."""
    design = ZenodoFDODesign(dois=["10.5281/zenodo.test"])
    design._processed_reference_versions.add("10.5281/zenodo.111111")

    with (
        patch.object(
            design,
            "_fetch_metadata",
            new_callable=AsyncMock,
            return_value=mock_dataset_with_references,
        ),
        patch.object(design.dataset_design, "create_fdo", new_callable=AsyncMock),
        patch.object(design.file_design, "create_fdo", new_callable=AsyncMock),
        patch.object(
            design.reference_processor, "process_all", new_callable=AsyncMock
        ) as mock_proc,
    ):
        design._record_graph["10.5281/zenodo.111111"] = PidRecord().setId(
            "10.5281/zenodo.111111"
        )
        await design.execute_async()

    mock_proc.assert_not_called()


@pytest.mark.asyncio
async def test_transform_handles_missing_license():
    """Test transformation when file has no license."""
    version = DatasetVersion(
        doi="10.5281/zenodo.111111",
        concept_doi="10.5281/zenodo.999999",
        recid=111111,
        title="No License Dataset",
        description="No license",
        publication_date=date(2024, 1, 1),
        version_label="1.0",
        creators=[],
        keywords=[],
        previous_version=None,
        next_version=None,
        license=None,
        files={},
        metadata_raw={"doi": "10.5281/zenodo.111111"},
    )

    file1 = ZenodoFile(
        checksum="md5:1234567890abcdef1234567890abcdef",
        filename="file.txt",
        size=256,
        mimetype="text/plain",
        first_dataset_version="10.5281/zenodo.111111",
        first_dataset_recid=111111,
        present_in_versions=["10.5281/zenodo.111111"],
        download_url="https://zenodo.org/api/records/1/files/file.txt",
    )

    dataset = Dataset(
        concept_doi="10.5281/zenodo.999999",
        concept_recid=999999,
        title="No License Dataset",
        description="No license",
        latest_version_doi="10.5281/zenodo.111111",
        versions={"10.5281/zenodo.111111": version},
        all_files={"md5:1234567890abcdef1234567890abcdef": file1},
        related_identifiers=[],
    )

    design = ZenodoFDODesign(dois=["10.5281/zenodo.test"])
    _, file_datas, _ = design._transform_to_exchange_models(dataset)

    assert len(file_datas) == 1
    assert file_datas[0].license_url is None


@pytest.mark.asyncio
async def test_transform_version_chain_links(mock_dataset):
    """Test that version chain links are properly transformed."""
    design = ZenodoFDODesign(dois=["10.5281/zenodo.test"])
    dataset_datas, _, _ = design._transform_to_exchange_models(mock_dataset)

    first_version = dataset_datas[0]
    second_version = dataset_datas[1]

    assert first_version.previous_version_doi is None
    assert first_version.next_version_doi == "10.5281/zenodo.222222"
    assert first_version.latest_version_doi == "10.5281/zenodo.222222"

    assert second_version.previous_version_doi == "10.5281/zenodo.111111"
    assert second_version.next_version_doi is None
    assert second_version.latest_version_doi is None


@pytest.mark.asyncio
async def test_transform_creators_data(mock_dataset):
    """Test creator data transformation."""
    design = ZenodoFDODesign(dois=["10.5281/zenodo.test"])
    dataset_datas, _, _ = design._transform_to_exchange_models(mock_dataset)

    for dataset_data in dataset_datas:
        assert len(dataset_data.creators) == 1
        creator = dataset_data.creators[0]
        assert isinstance(creator, CreatorData)
        assert creator.orcid == "https://orcid.org/0000-0000-0000-0001"
        assert creator.ror_id == "https://ror.org/01234567"
