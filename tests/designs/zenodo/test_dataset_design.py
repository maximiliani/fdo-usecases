# SPDX-FileCopyrightText: 2025 Maximilian Inckmann <maximilian.inckmann@kit.edu>
# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for ZenodoDatasetDesign."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from fdo_usecases.designs.zenodo.constants import (
    BACKLINK_DATASET_FILE,
    BACKLINK_VERSION_CHAIN,
    BASE_PROFILE,
    INFOTYPES,
    PROFILE_KEY,
    VERSIONABLE_PROFILE,
)
from fdo_usecases.designs.zenodo.designs.dataset import ZenodoDatasetDesign
from fdo_usecases.designs.zenodo.models.exchange import CreatorData, DatasetFDOData


@pytest.fixture
def sample_dataset_data():
    """Create sample dataset FDO data for testing."""
    return DatasetFDOData(
        doi="10.5281/zenodo.123456",
        title="Test Dataset Title",
        description="This is a test description",
        publication_date=date(2024, 1, 15),
        version_label="1.0",
        creators=[
            CreatorData(
                orcid="0000-0000-0000-0001", ror_id="https://ror.org/03x516a66"
            ),
            CreatorData(orcid="0000-0000-0000-0002"),
        ],
        keywords=["keyword1", "keyword2"],
        previous_version_doi=None,
        next_version_doi="10.5281/zenodo.789012",
        latest_version_doi="10.5281/zenodo.999999",
    )


@pytest.fixture
def dataset_with_version_chain():
    """Create dataset data with full version chain."""
    return DatasetFDOData(
        doi="10.5281/zenodo.789012",
        title="Middle Version Dataset",
        description="Description with <html>tags</html> that should be stripped",
        publication_date=date(2024, 6, 1),
        version_label="2.0",
        creators=[
            CreatorData(orcid="0000-0000-0000-0003", ror_id="https://ror.org/04hm8eb66")
        ],
        keywords=["test", "version"],
        previous_version_doi="10.5281/zenodo.123456",
        next_version_doi="10.5281/zenodo.999999",
        latest_version_doi="10.5281/zenodo.999999",
    )


@pytest.mark.asyncio
async def test_create_fdo_basic(sample_dataset_data):
    """Test basic FDO creation with minimal required fields."""
    design = ZenodoDatasetDesign()

    record_id = await design.create_fdo(sample_dataset_data)

    # Verify return value
    assert record_id == sample_dataset_data.doi

    # Verify record was created and stored locally
    assert sample_dataset_data.doi in design._local_records
    record = design._local_records[sample_dataset_data.doi]

    # Verify identity
    assert record.getId() == sample_dataset_data.doi
    assert record.getPid() == ""

    # Convert tuples to dict for easier lookup
    attr_dict = {}
    for k, v in record._tuples:
        if k not in attr_dict:
            attr_dict[k] = []
        attr_dict[k].append(v)

    # Verify profiles
    assert PROFILE_KEY in attr_dict
    profiles = attr_dict[PROFILE_KEY]
    assert BASE_PROFILE in profiles
    assert VERSIONABLE_PROFILE in profiles

    # Verify base attributes
    assert sample_dataset_data.title in attr_dict[INFOTYPES["name"]]
    assert (
        sample_dataset_data.publication_date.isoformat()
        in attr_dict[INFOTYPES["dateCreated"]]
    )

    # Verify versionable attributes
    assert sample_dataset_data.version_label in attr_dict[INFOTYPES["version"]]
    assert sample_dataset_data.next_version_doi in attr_dict[INFOTYPES["nextVersion"]]
    assert (
        sample_dataset_data.latest_version_doi in attr_dict[INFOTYPES["latestVersion"]]
    )

    # Verify backlinks
    assert BACKLINK_DATASET_FILE in design._backlinks
    assert BACKLINK_VERSION_CHAIN in design._backlinks


@pytest.mark.asyncio
async def test_create_fdo_with_creators(sample_dataset_data):
    """Test FDO creation includes creator ORCIDs and ROR IDs."""
    design = ZenodoDatasetDesign()

    await design.create_fdo(sample_dataset_data)

    record = design._local_records[sample_dataset_data.doi]
    attr_dict = {}
    for k, v in record._tuples:
        if k not in attr_dict:
            attr_dict[k] = []
        attr_dict[k].append(v)

    # Verify creator ORCIDs
    assert INFOTYPES["creator"] in attr_dict
    orcids = attr_dict[INFOTYPES["creator"]]
    assert "0000-0000-0000-0001" in orcids
    assert "0000-0000-0000-0002" in orcids
    assert len(orcids) == 2

    # Verify creator affiliations (ROR IDs)
    assert INFOTYPES["creatorAffiliation"] in attr_dict
    ror_ids = attr_dict[INFOTYPES["creatorAffiliation"]]
    assert "https://ror.org/03x516a66" in ror_ids
    assert len(ror_ids) == 1


@pytest.mark.asyncio
async def test_create_fdo_with_keywords(sample_dataset_data):
    """Test FDO creation includes keywords."""
    design = ZenodoDatasetDesign()

    await design.create_fdo(sample_dataset_data)

    record = design._local_records[sample_dataset_data.doi]
    attr_dict = {}
    for k, v in record._tuples:
        if k not in attr_dict:
            attr_dict[k] = []
        attr_dict[k].append(v)

    assert INFOTYPES["keyword"] in attr_dict
    keywords = attr_dict[INFOTYPES["keyword"]]
    assert "keyword1" in keywords
    assert "keyword2" in keywords


@pytest.mark.asyncio
async def test_create_fdo_with_html_stripping(dataset_with_version_chain):
    """Test that HTML tags are stripped from descriptions."""
    design = ZenodoDatasetDesign()

    await design.create_fdo(dataset_with_version_chain)

    record = design._local_records[dataset_with_version_chain.doi]
    attr_dict = {}
    for k, v in record._tuples:
        if k not in attr_dict:
            attr_dict[k] = []
        attr_dict[k].append(v)

    assert INFOTYPES["description"] in attr_dict
    description = attr_dict[INFOTYPES["description"]][0]
    assert "<html>" not in description
    assert "</html>" not in description
    assert "tags" in description


@pytest.mark.asyncio
async def test_create_fdo_version_chain(dataset_with_version_chain):
    """Test FDO creation with full version chain relationships."""
    design = ZenodoDatasetDesign()

    await design.create_fdo(dataset_with_version_chain)

    record = design._local_records[dataset_with_version_chain.doi]
    attr_dict = {}
    for k, v in record._tuples:
        if k not in attr_dict:
            attr_dict[k] = []
        attr_dict[k].append(v)

    # Verify previous version
    assert INFOTYPES["previousVersion"] in attr_dict
    assert (
        dataset_with_version_chain.previous_version_doi
        in attr_dict[INFOTYPES["previousVersion"]]
    )

    # Verify next version
    assert INFOTYPES["nextVersion"] in attr_dict
    assert (
        dataset_with_version_chain.next_version_doi
        in attr_dict[INFOTYPES["nextVersion"]]
    )

    # Verify latest version (should not be set when it equals current DOI)
    assert INFOTYPES["latestVersion"] in attr_dict
    assert (
        dataset_with_version_chain.latest_version_doi
        in attr_dict[INFOTYPES["latestVersion"]]
    )


@pytest.mark.asyncio
async def test_create_fdo_first_version():
    """Test FDO creation for first version (no previous version)."""
    first_version = DatasetFDOData(
        doi="10.5281/zenodo.111111",
        title="First Version",
        description="Initial release",
        publication_date=date(2023, 1, 1),
        version_label="1.0",
        creators=[],
        keywords=[],
        previous_version_doi=None,
        next_version_doi=None,
        latest_version_doi=None,
    )

    design = ZenodoDatasetDesign()

    mock_add_attribute = MagicMock()

    with patch.object(design, "addAttribute", mock_add_attribute):
        await design.create_fdo(first_version)

    # Verify previousVersion is NOT added
    for call in mock_add_attribute.call_args_list:
        assert call[0][0] != INFOTYPES["previousVersion"]

    # Verify nextVersion is NOT added
    for call in mock_add_attribute.call_args_list:
        assert call[0][0] != INFOTYPES["nextVersion"]

    # Verify latestVersion is NOT added
    for call in mock_add_attribute.call_args_list:
        assert call[0][0] != INFOTYPES["latestVersion"]


@pytest.mark.asyncio
async def test_create_fdo_no_creators():
    """Test FDO creation without creators."""
    dataset_no_creators = DatasetFDOData(
        doi="10.5281/zenodo.222222",
        title="Anonymous Dataset",
        description="No creators",
        publication_date=date(2024, 1, 1),
        version_label="1.0",
        creators=[],
        keywords=[],
    )

    design = ZenodoDatasetDesign()

    mock_add_attribute = MagicMock()

    with patch.object(design, "addAttribute", mock_add_attribute):
        await design.create_fdo(dataset_no_creators)

    # Verify creator ORCIDs are NOT added
    for call in mock_add_attribute.call_args_list:
        assert call[0][0] != INFOTYPES["creator"]

    # Verify creator affiliations are NOT added
    for call in mock_add_attribute.call_args_list:
        assert call[0][0] != INFOTYPES["creatorAffiliation"]


@pytest.mark.asyncio
async def test_create_fdo_no_keywords():
    """Test FDO creation without keywords."""
    dataset_no_keywords = DatasetFDOData(
        doi="10.5281/zenodo.333333",
        title="No Keywords Dataset",
        description="Empty keywords",
        publication_date=date(2024, 1, 1),
        version_label="1.0",
        creators=[],
        keywords=[],
    )

    design = ZenodoDatasetDesign()

    mock_add_attribute = MagicMock()

    with patch.object(design, "addAttribute", mock_add_attribute):
        await design.create_fdo(dataset_no_keywords)

    # Verify keyword attribute is NOT added
    for call in mock_add_attribute.call_args_list:
        assert call[0][0] != INFOTYPES["keyword"]


@pytest.mark.asyncio
async def test_create_fdo_latest_version_is_current():
    """Test that latestVersion is not added when current version is latest."""
    latest_version = DatasetFDOData(
        doi="10.5281/zenodo.999999",
        title="Latest Version",
        description="Final release",
        publication_date=date(2024, 12, 1),
        version_label="3.0",
        creators=[],
        keywords=[],
        previous_version_doi="10.5281/zenodo.789012",
        next_version_doi=None,
        latest_version_doi=None,  # None because this IS the latest
    )

    design = ZenodoDatasetDesign()

    mock_add_attribute = MagicMock()

    with patch.object(design, "addAttribute", mock_add_attribute):
        await design.create_fdo(latest_version)

    # Verify latestVersion is NOT added when it equals current DOI
    for call in mock_add_attribute.call_args_list:
        assert call[0][0] != INFOTYPES["latestVersion"]


@pytest.mark.asyncio
async def test_design_initialization():
    """Test ZenodoDatasetDesign initialization."""
    design = ZenodoDatasetDesign()

    # Verify design is properly initialized
    assert isinstance(design, ZenodoDatasetDesign)
    # Verify it inherits from RecordDesign
    from fdo_usecases.designer_lib.executor import RecordDesign

    assert isinstance(design, RecordDesign)
