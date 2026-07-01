# SPDX-FileCopyrightText: 2025 Maximilian Inckmann <maximilian.inckmann@kit.edu>
# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for PublicationDesign."""

from unittest.mock import MagicMock, patch

import pytest

from fdo_usecases.designs.zenodo.constants import (
    BACKLINK_PUBLICATION_CITATION,
    BACKLINK_PUBLICATION_REFERENCE,
    BASE_PROFILE,
    INFOTYPES,
    PROFILE_KEY,
    PUBLICATION_PROFILE,
)
from fdo_usecases.designs.zenodo.designs.publication import PublicationDesign
from fdo_usecases.designs.zenodo.models.exchange import PublicationFDOData


@pytest.fixture
def sample_publication_data():
    """Create sample publication FDO data for testing."""
    return PublicationFDOData(
        identifier="10.1016/j.actamat.2025.120735",
        resource_type="publication-article",
        publisher="Elsevier",
        publication_date="2025-01-15",
        title="Creep reference data for nickel-based superalloys",
        description="This paper presents comprehensive creep reference data...",
        creator_orcids=["0000-0000-0000-0001", "0000-0000-0000-0002"],
    )


@pytest.fixture
def minimal_publication_data():
    """Create minimal publication FDO data (as from related identifiers)."""
    return PublicationFDOData(
        identifier="10.1000/xyz123",
        resource_type=None,
        publisher=None,
        publication_date=None,
        title=None,
        description=None,
        creator_orcids=[],
    )


@pytest.fixture
def publication_with_html():
    """Create publication data with HTML in description."""
    return PublicationFDOData(
        identifier="10.1000/html123",
        resource_type="publication-conferencepaper",
        publisher="IEEE",
        publication_date="2024-06-01",
        title="Conference Paper",
        description="<p>This is a <strong>description</strong> with HTML tags.</p>",
        creator_orcids=["0000-0000-0000-0003"],
    )


@pytest.mark.asyncio
async def test_create_fdo_basic(sample_publication_data):
    """Test basic FDO creation with all fields."""
    design = PublicationDesign()

    record_id = await design.create_fdo(sample_publication_data)

    # Verify return value
    assert record_id == sample_publication_data.identifier

    # Verify record was created and stored locally
    assert sample_publication_data.identifier in design._local_records
    record = design._local_records[sample_publication_data.identifier]

    # Verify identity
    assert record.getId() == sample_publication_data.identifier
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
    assert PUBLICATION_PROFILE in profiles

    # Verify publication attributes
    assert sample_publication_data.identifier in attr_dict[INFOTYPES["doi"]]
    assert (
        sample_publication_data.resource_type
        in attr_dict[INFOTYPES["dataCitePublicationType"]]
    )
    assert sample_publication_data.publisher in attr_dict[INFOTYPES["publisher"]]
    assert (
        sample_publication_data.publication_date
        in attr_dict[INFOTYPES["datePublished"]]
    )
    assert sample_publication_data.title in attr_dict[INFOTYPES["name"]]
    assert sample_publication_data.description in attr_dict[INFOTYPES["description"]]
    assert sample_publication_data.creator_orcids[0] in attr_dict[INFOTYPES["creator"]]

    # Verify backlinks
    assert BACKLINK_PUBLICATION_CITATION in design._backlinks
    assert BACKLINK_PUBLICATION_REFERENCE in design._backlinks


@pytest.mark.asyncio
async def test_create_fdo_minimal(minimal_publication_data):
    """Test FDO creation with minimal metadata."""
    design = PublicationDesign()

    await design.create_fdo(minimal_publication_data)

    record = design._local_records[minimal_publication_data.identifier]
    attr_dict = {}
    for k, v in record._tuples:
        if k not in attr_dict:
            attr_dict[k] = []
        attr_dict[k].append(v)

    # Verify DOI is always set
    assert INFOTYPES["doi"] in attr_dict
    assert minimal_publication_data.identifier in attr_dict[INFOTYPES["doi"]]

    # Verify optional fields are NOT added
    assert INFOTYPES["dataCitePublicationType"] not in attr_dict
    assert INFOTYPES["publisher"] not in attr_dict
    assert INFOTYPES["datePublished"] not in attr_dict
    assert INFOTYPES["name"] not in attr_dict
    assert INFOTYPES["description"] not in attr_dict
    assert INFOTYPES["creator"] not in attr_dict


@pytest.mark.asyncio
async def test_create_fdo_with_html_stripping(publication_with_html):
    """Test that HTML tags are stripped from descriptions."""
    design = PublicationDesign()

    await design.create_fdo(publication_with_html)

    record = design._local_records[publication_with_html.identifier]
    attr_dict = {}
    for k, v in record._tuples:
        if k not in attr_dict:
            attr_dict[k] = []
        attr_dict[k].append(v)

    assert INFOTYPES["description"] in attr_dict
    description = attr_dict[INFOTYPES["description"]][0]
    assert "<p>" not in description
    assert "</p>" not in description
    assert "<strong>" not in description
    assert "</strong>" not in description
    assert "description" in description


@pytest.mark.asyncio
async def test_create_fdo_multiple_creators():
    """Test FDO creation with multiple creator ORCIDs."""
    publication = PublicationFDOData(
        identifier="10.1000/multi123",
        resource_type="publication-article",
        title="Multi-author Paper",
        creator_orcids=[
            "0000-0000-0000-0001",
            "0000-0000-0000-0002",
            "0000-0000-0000-0003",
            "0000-0000-0000-0004",
        ],
    )

    design = PublicationDesign()

    await design.create_fdo(publication)

    record = design._local_records[publication.identifier]
    attr_dict = {}
    for k, v in record._tuples:
        if k not in attr_dict:
            attr_dict[k] = []
        attr_dict[k].append(v)

    assert INFOTYPES["creator"] in attr_dict
    orcids = attr_dict[INFOTYPES["creator"]]
    assert len(orcids) == 4
    assert "0000-0000-0000-0001" in orcids
    assert "0000-0000-0000-0004" in orcids


@pytest.mark.asyncio
async def test_create_fdo_no_creators():
    """Test FDO creation without creators."""
    publication = PublicationFDOData(
        identifier="10.1000/nocreator",
        resource_type="publication-article",
        title="Anonymous Paper",
        creator_orcids=[],
    )

    design = PublicationDesign()

    mock_add_attribute = MagicMock()

    with patch.object(design, "addAttribute", mock_add_attribute):
        await design.create_fdo(publication)

    # Verify creator attribute is NOT added when empty
    for call in mock_add_attribute.call_args_list:
        assert call[0][0] != INFOTYPES["creator"]


@pytest.mark.asyncio
async def test_different_publication_types():
    """Test FDO creation for different publication types."""
    test_cases = [
        ("publication-article", "Journal Article"),
        ("publication-conferencepaper", "Conference Paper"),
        ("publication-book", "Book"),
        ("publication-thesis", "Thesis"),
        ("publication-datapaper", "Data Paper"),
    ]

    for pub_type, title in test_cases:
        design = PublicationDesign()
        pub_data = PublicationFDOData(
            identifier=f"10.1000/{pub_type}",
            resource_type=pub_type,
            title=title,
        )

        await design.create_fdo(pub_data)

        record = design._local_records[pub_data.identifier]
        attr_dict = {}
        for k, v in record._tuples:
            if k not in attr_dict:
                attr_dict[k] = []
            attr_dict[k].append(v)

        assert INFOTYPES["dataCitePublicationType"] in attr_dict
        assert pub_type in attr_dict[INFOTYPES["dataCitePublicationType"]]


@pytest.mark.asyncio
async def test_design_initialization():
    """Test PublicationDesign initialization."""
    design = PublicationDesign()

    assert isinstance(design, PublicationDesign)

    from fdo_usecases.designer_lib.executor import RecordDesign

    assert isinstance(design, RecordDesign)


@pytest.mark.asyncio
async def test_identifier_as_record_id():
    """Verify that identifier is used as record ID."""
    pub_data = PublicationFDOData(
        identifier="10.5281/zenodo.external123",
        title="External Reference",
    )

    design = PublicationDesign()

    record_id = await design.create_fdo(pub_data)

    assert record_id == pub_data.identifier
    assert design._local_records[pub_data.identifier].getId() == pub_data.identifier
