"""Tests for Zenodo metadata extractor."""

import pytest
from pydantic import ValidationError
from zenodo_metadata_extractor import (
    Creator,
    DatasetVersion,
    LicenseInfo,
    RelatedIdentifier,
    ZenodoDatasetFetcher,
    ZenodoFile,
)
from zenodo_metadata_extractor.exceptions import (
    DOINotFoundError,
)


class TestZenodoFile:
    """Test ZenodoFile model validation."""

    def test_valid_file(self):
        file = ZenodoFile(
            checksum="md5:28573899cc09a145ac2c69fc1370c0bf",
            filename="test.txt",
            size=1024,
            first_dataset_version="10.5281/zenodo.123",
            first_dataset_recid=123,
            download_url="https://zenodo.org/api/files/test.txt",
        )
        assert file.checksum == "md5:28573899cc09a145ac2c69fc1370c0bf"
        assert file.filename == "test.txt"
        assert file.size == 1024
        assert file.id is not None

    def test_invalid_checksum_format(self):
        with pytest.raises(ValidationError, match="Checksum must be MD5 format"):
            ZenodoFile(
                checksum="sha256:abc123",
                filename="test.txt",
                size=1024,
                first_dataset_version="10.5281/zenodo.123",
                first_dataset_recid=123,
                download_url="https://zenodo.org/api/files/test.txt",
            )

    def test_invalid_checksum_length(self):
        with pytest.raises(ValidationError, match="Checksum must be MD5 format"):
            ZenodoFile(
                checksum="md5:tooshort",
                filename="test.txt",
                size=1024,
                first_dataset_version="10.5281/zenodo.123",
                first_dataset_recid=123,
                download_url="https://zenodo.org/api/files/test.txt",
            )

    def test_invalid_size_zero(self):
        with pytest.raises(ValidationError, match="File size must be positive"):
            ZenodoFile(
                checksum="md5:28573899cc09a145ac2c69fc1370c0bf",
                filename="test.txt",
                size=0,
                first_dataset_version="10.5281/zenodo.123",
                first_dataset_recid=123,
                download_url="https://zenodo.org/api/files/test.txt",
            )

    def test_invalid_size_negative(self):
        with pytest.raises(ValidationError, match="File size must be positive"):
            ZenodoFile(
                checksum="md5:28573899cc09a145ac2c69fc1370c0bf",
                filename="test.txt",
                size=-100,
                first_dataset_version="10.5281/zenodo.123",
                first_dataset_recid=123,
                download_url="https://zenodo.org/api/files/test.txt",
            )

    def test_file_with_optional_fields(self):
        file = ZenodoFile(
            checksum="md5:28573899cc09a145ac2c69fc1370c0bf",
            filename="data.csv",
            size=2048,
            mimetype="text/csv",
            first_dataset_version="10.5281/zenodo.123",
            first_dataset_recid=123,
            download_url="https://zenodo.org/api/files/data.csv",
        )
        assert file.mimetype == "text/csv"


class TestCreator:
    """Test Creator model validation."""

    def test_minimal_creator(self):
        creator = Creator(name="Doe, John")
        assert creator.name == "Doe, John"
        assert creator.affiliation is None
        assert creator.orcid is None

    def test_full_creator(self):
        creator = Creator(
            name="Doe, John",
            affiliation="University of Example",
            orcid="0000-0002-1694-233X",
        )
        assert creator.name == "Doe, John"
        assert creator.affiliation == "University of Example"
        assert creator.orcid == "0000-0002-1694-233X"

    def test_invalid_orcid(self):
        with pytest.raises(ValidationError, match="Invalid ORCID format"):
            Creator(
                name="Doe, John",
                orcid="invalid-orcid",
            )


class TestRelatedIdentifier:
    """Test RelatedIdentifier model validation."""

    def test_valid_identifier(self):
        rel = RelatedIdentifier(
            identifier="10.5281/zenodo.123456",
            relation="isSupplementTo",
            resource_type="dataset",
            scheme="doi",
        )
        assert rel.identifier == "10.5281/zenodo.123456"
        assert rel.relation == "isSupplementTo"

    def test_invalid_relation(self):
        with pytest.raises(ValidationError, match="Invalid relation type"):
            RelatedIdentifier(
                identifier="10.5281/zenodo.123456",
                relation="invalidRelation",
            )

    def test_valid_relations(self):
        valid_relations = [
            "isCitedBy",
            "cites",
            "isSupplementTo",
            "isSupplementedBy",
            "isNewVersionOf",
            "isPreviousVersionOf",
            "references",
            "isReferencedBy",
        ]
        for relation in valid_relations:
            rel = RelatedIdentifier(
                identifier="10.5281/zenodo.123456",
                relation=relation,
            )
            assert rel.relation == relation


class TestDatasetVersion:
    """Test DatasetVersion model validation."""

    def test_minimal_version(self):
        version = DatasetVersion(
            doi="10.5281/zenodo.123456",
            concept_doi="10.5281/zenodo.123450",
            recid=123456,
            version_label="1.0",
            title="Test Dataset",
            creators=[Creator(name="Doe, John")],
            publication_date="2024-01-15",
            files={},
            metadata_raw={},
        )
        assert version.doi == "10.5281/zenodo.123456"
        assert version.title == "Test Dataset"

    def test_invalid_doi(self):
        with pytest.raises(ValidationError, match="Invalid DOI format"):
            DatasetVersion(
                doi="invalid-doi",
                concept_doi="10.5281/zenodo.123450",
                recid=123456,
                version_label="1.0",
                title="Test Dataset",
                creators=[Creator(name="Doe, John")],
                publication_date="2024-01-15",
                files={},
                metadata_raw={},
            )

    def test_with_license(self):
        version = DatasetVersion(
            doi="10.5281/zenodo.123456",
            concept_doi="10.5281/zenodo.123450",
            recid=123456,
            version_label="1.0",
            title="Test Dataset",
            creators=[Creator(name="Doe, John")],
            publication_date="2024-01-15",
            license=LicenseInfo(id="cc-by-4.0"),
            files={},
            metadata_raw={},
        )
        assert version.license.id == "cc-by-4.0"


@pytest.mark.asyncio
class TestZenodoDatasetFetcherLive:
    """Live integration tests with Zenodo API."""

    async def test_fetch_example_dataset(self):
        fetcher = ZenodoDatasetFetcher(cache_enabled=True)
        dataset = await fetcher.fetch_by_doi("10.5281/zenodo.20132712")

        assert dataset.concept_doi == "10.5281/zenodo.13937986"
        assert dataset.concept_recid == 13937986
        assert len(dataset.versions) >= 1
        assert dataset.latest_version_doi in dataset.versions
        assert len(dataset.all_files) > 0

    async def test_version_relationships(self):
        fetcher = ZenodoDatasetFetcher(cache_enabled=False)
        dataset = await fetcher.fetch_by_doi("10.5281/zenodo.20132712")

        latest = dataset.versions[dataset.latest_version_doi]

        if len(dataset.versions) > 1:
            assert latest.previous_version is not None
            prev = latest.previous_version
            assert prev.next_version is latest

    async def test_file_tracking_across_versions(self):
        fetcher = ZenodoDatasetFetcher(cache_enabled=False)
        dataset = await fetcher.fetch_by_doi("10.5281/zenodo.20132712")

        multi_version_files = [
            f for f in dataset.all_files.values() if len(f.present_in_versions) > 1
        ]

        assert len(multi_version_files) > 0

    async def test_file_version_chains(self):
        fetcher = ZenodoDatasetFetcher(cache_enabled=False)
        dataset = await fetcher.fetch_by_doi("10.5281/zenodo.20132712")

        chain_roots = [
            f
            for f in dataset.all_files.values()
            if f.previous_version is None and f.next_version is not None
        ]

        if chain_roots:
            root = chain_roots[0]
            chain_length = 1
            current = root.next_version
            while current:
                chain_length += 1
                assert current.previous_version is not None
                current = current.next_version

            assert chain_length >= 2

    async def test_related_identifiers(self):
        fetcher = ZenodoDatasetFetcher(cache_enabled=True)
        dataset = await fetcher.fetch_by_doi("10.5281/zenodo.20132712")

        assert len(dataset.related_identifiers) > 0

        relations = {rel.relation for rel in dataset.related_identifiers}
        assert "cites" in relations or "isSupplementedBy" in relations

    async def test_nonexistent_record_id(self):
        """Test that non-existent record IDs raise DOINotFoundError."""
        fetcher = ZenodoDatasetFetcher(cache_enabled=False)

        async with fetcher.api_client:
            with pytest.raises(DOINotFoundError):
                await fetcher.api_client.get("/records/999999999")

    async def test_caching(self):
        fetcher = ZenodoDatasetFetcher(cache_enabled=True)

        dataset1 = await fetcher.fetch_by_doi("10.5281/zenodo.20132712")
        dataset2 = await fetcher.fetch_by_doi("10.5281/zenodo.20132712")

        assert dataset1.concept_recid == dataset2.concept_recid
