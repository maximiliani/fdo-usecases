# SPDX-FileCopyrightText: 2025 Maximilian Inckmann <maximilian.inckmann@kit.edu>
# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for ZenodoFileDesign."""

from unittest.mock import MagicMock, patch

import pytest

from fdo_usecases.designs.zenodo.constants import (
    BACKLINK_DATASET_FILE,
    BASE_PROFILE,
    DATARESOURCE_PROFILE,
    INFOTYPES,
    PROFILE_KEY,
)
from fdo_usecases.designs.zenodo.designs.file import ZenodoFileDesign
from fdo_usecases.designs.zenodo.models.exchange import FileFDOData


@pytest.fixture
def sample_file_data():
    """Create sample file FDO data for testing."""
    return FileFDOData(
        checksum="md5:abc123def456789012345678901234ab",
        filename="data.csv",
        mimetype="text/csv",
        download_url="https://zenodo.org/api/records/123/files/data.csv",
        license_url="https://spdx.org/licenses/CC-BY-4.0",
    )


@pytest.fixture
def file_without_license():
    """Create file data without license."""
    return FileFDOData(
        checksum="md5:def456abc789012345678901234cd",
        filename="readme.txt",
        mimetype="text/plain",
        download_url="https://zenodo.org/api/records/456/files/readme.txt",
        license_url=None,
    )


@pytest.fixture
def file_without_mimetype():
    """Create file data without MIME type."""
    return FileFDOData(
        checksum="md5:789abc012def345678901234ef",
        filename="unknown_file",
        mimetype=None,
        download_url="https://zenodo.org/api/records/789/files/unknown_file",
        license_url=None,
    )


@pytest.mark.asyncio
async def test_create_fdo_basic(sample_file_data):
    """Test basic FDO creation with all fields."""
    design = ZenodoFileDesign()

    record_id = await design.create_fdo(sample_file_data)

    # Verify return value
    assert record_id == sample_file_data.checksum

    # Verify record was created and stored locally
    assert sample_file_data.checksum in design._local_records
    record = design._local_records[sample_file_data.checksum]

    # Verify identity
    assert record.getId() == sample_file_data.checksum
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
    assert DATARESOURCE_PROFILE in profiles

    # Verify base attributes
    assert sample_file_data.filename in attr_dict[INFOTYPES["name"]]
    assert sample_file_data.mimetype in attr_dict[INFOTYPES["mimeType"]]
    assert sample_file_data.download_url in attr_dict[INFOTYPES["dataObjectLocation"]]
    assert sample_file_data.checksum in attr_dict[INFOTYPES["checksum"]]
    assert sample_file_data.license_url in attr_dict[INFOTYPES["spdxLicense"]]

    # Verify backlinks
    assert BACKLINK_DATASET_FILE in design._backlinks


@pytest.mark.asyncio
async def test_create_fdo_without_license(file_without_license):
    """Test FDO creation without license URL."""
    design = ZenodoFileDesign()

    mock_add_attribute = MagicMock()

    with patch.object(design, "addAttribute", mock_add_attribute):
        await design.create_fdo(file_without_license)

    # Verify spdxLicense is NOT added when None
    for call in mock_add_attribute.call_args_list:
        assert call[0][0] != INFOTYPES["spdxLicense"]


@pytest.mark.asyncio
async def test_create_fdo_without_mimetype(file_without_mimetype):
    """Test FDO creation without MIME type."""
    design = ZenodoFileDesign()

    mock_add_attribute = MagicMock()

    with patch.object(design, "addAttribute", mock_add_attribute):
        await design.create_fdo(file_without_mimetype)

    # Verify mimeType is NOT added when None
    for call in mock_add_attribute.call_args_list:
        assert call[0][0] != INFOTYPES["mimeType"]


@pytest.mark.asyncio
async def test_create_fdo_required_fields_only():
    """Test FDO creation with only required fields."""
    minimal_file = FileFDOData(
        checksum="md5:minimal123456789012345678901234",
        filename="minimal.dat",
        mimetype=None,
        download_url="https://zenodo.org/api/records/999/files/minimal.dat",
        license_url=None,
    )

    design = ZenodoFileDesign()

    await design.create_fdo(minimal_file)

    record = design._local_records[minimal_file.checksum]
    attr_dict = {}
    for k, v in record._tuples:
        if k not in attr_dict:
            attr_dict[k] = []
        attr_dict[k].append(v)

    # Verify required attributes are present
    assert PROFILE_KEY in attr_dict
    assert INFOTYPES["name"] in attr_dict
    assert INFOTYPES["dataObjectLocation"] in attr_dict
    assert INFOTYPES["checksum"] in attr_dict

    # Verify optional attributes are NOT present
    assert INFOTYPES["mimeType"] not in attr_dict
    assert INFOTYPES["spdxLicense"] not in attr_dict


@pytest.mark.asyncio
async def test_different_file_types():
    """Test FDO creation for different file types."""
    test_cases = [
        ("image.png", "image/png", "md5:image123456789012345678901234"),
        ("data.json", "application/json", "md5:json123456789012345678901234"),
        ("archive.zip", "application/zip", "md5:zip123456789012345678901234"),
        ("notebook.ipynb", None, "md5:ipynb123456789012345678901234"),
    ]

    for filename, mimetype, checksum in test_cases:
        design = ZenodoFileDesign()
        file_data = FileFDOData(
            checksum=checksum,
            filename=filename,
            mimetype=mimetype,
            download_url=f"https://zenodo.org/api/records/123/files/{filename}",
            license_url="https://spdx.org/licenses/MIT",
        )

        await design.create_fdo(file_data)

        record = design._local_records[checksum]
        attr_dict = {}
        for k, v in record._tuples:
            if k not in attr_dict:
                attr_dict[k] = []
            attr_dict[k].append(v)

        # Verify filename is set correctly
        assert filename in attr_dict[INFOTYPES["name"]]

        # Verify checksum is set correctly
        assert checksum in attr_dict[INFOTYPES["checksum"]]


@pytest.mark.asyncio
async def test_design_initialization():
    """Test ZenodoFileDesign initialization."""
    design = ZenodoFileDesign()

    assert isinstance(design, ZenodoFileDesign)

    from fdo_usecases.designer_lib.executor import RecordDesign

    assert isinstance(design, RecordDesign)


@pytest.mark.asyncio
async def test_checksum_as_record_id():
    """Verify that checksum is used as record ID for deduplication."""
    file_v1 = FileFDOData(
        checksum="md5:same123456789012345678901234",
        filename="data_v1.csv",
        mimetype="text/csv",
        download_url="https://zenodo.org/api/records/123/files/data.csv",
        license_url="https://spdx.org/licenses/CC-BY-4.0",
    )

    file_v2 = FileFDOData(
        checksum="md5:same123456789012345678901234",  # Same checksum
        filename="data_v2.csv",  # Different filename
        mimetype="text/csv",
        download_url="https://zenodo.org/api/records/456/files/data.csv",
        license_url="https://spdx.org/licenses/CC-BY-4.0",
    )

    design = ZenodoFileDesign()

    id1 = await design.create_fdo(file_v1)
    id2 = await design.create_fdo(file_v2)

    # Both should return the same checksum as record ID
    assert id1 == file_v1.checksum
    assert id2 == file_v2.checksum
    assert id1 == id2
