# SPDX-FileCopyrightText: 2025 Maximilian Inckmann <maximilian.inckmann@kit.edu>
# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for ReferenceProcessor and handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fdo_usecases.designs.zenodo.designs.publication import PublicationDesign
from fdo_usecases.designs.zenodo.handlers.reference_processor import (
    PublicationReferenceHandler,
    ReferenceProcessor,
    ZenodoReferenceHandler,
)
from fdo_usecases.designs.zenodo.models import RelatedIdentifier
from fdo_usecases.designs.zenodo.models.exchange import PublicationFDOData


@pytest.fixture
def zenodo_identifier():
    """Create a Zenodo related identifier."""
    return RelatedIdentifier(
        identifier="10.5281/zenodo.987654",
        relation="cites",
        scheme="doi",
        resource_type="dataset",
    )


@pytest.fixture
def external_doi_identifier():
    """Create an external DOI related identifier."""
    return RelatedIdentifier(
        identifier="10.1016/j.actamat.2025.120735",
        relation="cites",
        scheme="doi",
        resource_type="publication-article",
    )


@pytest.fixture
def mock_orchestrator():
    """Create mock orchestrator for testing."""
    mock = MagicMock()
    mock._processed_datasets = set()
    mock._process_zenodo_reference = AsyncMock()
    return mock


class TestZenodoReferenceHandler:
    """Tests for ZenodoReferenceHandler."""

    @pytest.mark.asyncio
    async def test_can_handle_zenodo(self, zenodo_identifier):
        """Test handler can identify Zenodo references."""
        handler = ZenodoReferenceHandler(MagicMock())
        result = await handler.can_handle(zenodo_identifier)
        assert result is True

    @pytest.mark.asyncio
    async def test_can_handle_zenodo_case_insensitive(self):
        """Test handler identifies Zenodo case-insensitively."""
        handler = ZenodoReferenceHandler(MagicMock())

        for doi in [
            "10.5281/ZENODO.123",
            "10.5281/Zenodo.456",
            "https://zenodo.org/record/789",
        ]:
            identifier = RelatedIdentifier(
                identifier=doi,
                relation="cites",
                scheme="doi",
                resource_type="dataset",
            )
            result = await handler.can_handle(identifier)
            assert result is True

    @pytest.mark.asyncio
    async def test_cannot_handle_non_zenodo(self, external_doi_identifier):
        """Test handler cannot handle non-Zenodo references."""
        handler = ZenodoReferenceHandler(MagicMock())
        result = await handler.can_handle(external_doi_identifier)
        assert result is False

    @pytest.mark.asyncio
    async def test_process_new_zenodo(self, zenodo_identifier, mock_orchestrator):
        """Test processing a new Zenodo reference."""
        handler = ZenodoReferenceHandler(mock_orchestrator)

        await handler.process(zenodo_identifier)

        mock_orchestrator._process_zenodo_reference.assert_called_once_with(
            zenodo_identifier.identifier
        )

    @pytest.mark.asyncio
    async def test_process_already_processed(
        self, zenodo_identifier, mock_orchestrator
    ):
        """Test skipping already processed Zenodo dataset."""
        mock_orchestrator._processed_datasets.add(zenodo_identifier.identifier)
        handler = ZenodoReferenceHandler(mock_orchestrator)

        await handler.process(zenodo_identifier)

        mock_orchestrator._process_zenodo_reference.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialization(self, mock_orchestrator):
        """Test handler initialization."""
        handler = ZenodoReferenceHandler(mock_orchestrator)
        assert handler.orchestrator is mock_orchestrator


class TestPublicationReferenceHandler:
    """Tests for PublicationReferenceHandler."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator for testing."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_can_handle_external_doi(
        self, external_doi_identifier, mock_orchestrator
    ):
        """Test handler can identify external DOI references."""
        handler = PublicationReferenceHandler(mock_orchestrator)
        result = await handler.can_handle(external_doi_identifier)
        assert result is True

    @pytest.mark.asyncio
    async def test_can_handle_non_zenodo(self, mock_orchestrator):
        """Test handler can handle non-Zenodo identifiers."""
        handler = PublicationReferenceHandler(mock_orchestrator)

        for doi in [
            "10.1000/xyz123",
            "10.1038/nature123",
            "https://doi.org/10.1000/test",
        ]:
            identifier = RelatedIdentifier(
                identifier=doi,
                relation="references",
                scheme="doi",
                resource_type="publication-article",
            )
            result = await handler.can_handle(identifier)
            assert result is True

    @pytest.mark.asyncio
    async def test_cannot_handle_zenodo(self, zenodo_identifier, mock_orchestrator):
        """Test handler cannot handle Zenodo references."""
        handler = PublicationReferenceHandler(mock_orchestrator)
        result = await handler.can_handle(zenodo_identifier)
        assert result is False

    @pytest.mark.asyncio
    async def test_process_creates_publication_fdo(
        self, external_doi_identifier, mock_orchestrator
    ):
        """Test processing creates Publication FDO."""
        handler = PublicationReferenceHandler(mock_orchestrator)

        mock_create_fdo = AsyncMock(return_value=external_doi_identifier.identifier)

        with patch.object(handler, "publication_design") as mock_design:
            mock_design.create_fdo = mock_create_fdo
            await handler.process(external_doi_identifier)

        mock_create_fdo.assert_called_once()
        pub_data = mock_create_fdo.call_args[0][0]
        assert isinstance(pub_data, PublicationFDOData)
        assert pub_data.identifier == external_doi_identifier.identifier
        assert pub_data.resource_type == external_doi_identifier.resource_type
        assert pub_data.publisher is None
        assert pub_data.publication_date is None
        assert pub_data.title is None
        assert pub_data.description is None
        assert pub_data.creator_orcids == []

    @pytest.mark.asyncio
    async def test_process_handles_exception(
        self, external_doi_identifier, mock_orchestrator
    ):
        """Test handler continues on exception."""
        handler = PublicationReferenceHandler(mock_orchestrator)

        with patch.object(
            handler.publication_design,
            "create_fdo",
            side_effect=Exception("Test error"),
        ):
            # Should not raise exception
            await handler.process(external_doi_identifier)

    @pytest.mark.asyncio
    async def test_initialization(self, mock_orchestrator):
        """Test handler initialization."""
        handler = PublicationReferenceHandler(mock_orchestrator)
        assert isinstance(handler.publication_design, PublicationDesign)


class TestReferenceProcessor:
    """Tests for ReferenceProcessor."""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_orchestrator):
        """Test processor initializes with handlers."""
        processor = ReferenceProcessor(mock_orchestrator)
        assert len(processor.handlers) == 2
        assert isinstance(processor.handlers[0], ZenodoReferenceHandler)
        assert isinstance(processor.handlers[1], PublicationReferenceHandler)

    @pytest.mark.asyncio
    async def test_process_zenodo_identifier(
        self, zenodo_identifier, mock_orchestrator
    ):
        """Test processing Zenodo identifier routes to correct handler."""
        processor = ReferenceProcessor(mock_orchestrator)

        await processor.process_all([zenodo_identifier])

        mock_orchestrator._process_zenodo_reference.assert_called_once_with(
            zenodo_identifier.identifier
        )

    @pytest.mark.asyncio
    async def test_process_external_doi_identifier(self, external_doi_identifier):
        """Test processing external DOI routes to publication handler."""
        mock_orchestrator = MagicMock()
        mock_orchestrator._processed_datasets = set()
        processor = ReferenceProcessor(mock_orchestrator)

        with patch.object(
            processor.handlers[1].publication_design,
            "create_fdo",
            new_callable=AsyncMock,
        ) as mock_create:
            await processor.process_all([external_doi_identifier])
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_multiple_identifiers(
        self, zenodo_identifier, external_doi_identifier, mock_orchestrator
    ):
        """Test processing multiple identifiers of different types."""
        processor = ReferenceProcessor(mock_orchestrator)

        identifiers = [zenodo_identifier, external_doi_identifier]

        with patch.object(
            processor.handlers[1].publication_design,
            "create_fdo",
            new_callable=AsyncMock,
        ) as mock_create:
            await processor.process_all(identifiers)

            mock_orchestrator._process_zenodo_reference.assert_called_once()
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_empty_list(self, mock_orchestrator):
        """Test processing empty identifier list."""
        processor = ReferenceProcessor(mock_orchestrator)

        # Should not raise any errors
        await processor.process_all([])

        mock_orchestrator._process_zenodo_reference.assert_not_called()

    @pytest.mark.asyncio
    async def test_handler_error_continues_processing(self, mock_orchestrator):
        """Test that handler errors don't stop processing other identifiers."""
        processor = ReferenceProcessor(mock_orchestrator)

        identifier1 = RelatedIdentifier(
            identifier="10.5281/zenodo.error1",
            relation="cites",
            scheme="doi",
            resource_type="dataset",
        )

        identifier2 = RelatedIdentifier(
            identifier="10.5281/zenodo.success",
            relation="cites",
            scheme="doi",
            resource_type="dataset",
        )

        # Make first call fail, second succeed
        call_count = 0

        async def mock_process(doi):
            nonlocal call_count
            call_count += 1
            if doi == identifier1.identifier:
                raise Exception("Simulated error")

        mock_orchestrator._process_zenodo_reference = mock_process

        # Should not raise exception and should process both
        await processor.process_all([identifier1, identifier2])

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_no_handler_warning(self, caplog):
        """Test warning when no handler matches."""
        mock_orchestrator = MagicMock()
        mock_orchestrator._processed_datasets = set()

        # Create custom handler that rejects everything
        class RejectAllHandler:
            async def can_handle(self, identifier):
                return False

            async def process(self, identifier):
                pass

        # Replace handlers with ones that reject all
        from fdo_usecases.designs.zenodo.handlers.reference_processor import (
            ReferenceProcessor,
        )

        processor = ReferenceProcessor.__new__(ReferenceProcessor)
        processor.handlers = [RejectAllHandler()]

        # Create identifier that won't match any handler
        identifier = RelatedIdentifier(
            identifier="unknown:scheme:test",
            relation="cites",
            scheme="unknown",
            resource_type="other",
        )

        import logging

        with caplog.at_level(logging.WARNING):
            await processor.process_all([identifier])

        # Should log warning about no handler found
        assert "No handler found" in caplog.text

    @pytest.mark.asyncio
    async def test_first_matching_handler_wins(self, external_doi_identifier):
        """Test that first matching handler processes the identifier."""
        mock_orchestrator = MagicMock()
        mock_orchestrator._processed_datasets = set()
        processor = ReferenceProcessor(mock_orchestrator)

        # Track which handlers were called
        handler_calls = []

        original_can_handle_0 = processor.handlers[0].can_handle
        original_process_0 = processor.handlers[0].process
        original_can_handle_1 = processor.handlers[1].can_handle
        original_process_1 = processor.handlers[1].process

        async def mock_can_handle_0(*args):
            handler_calls.append("handler0_can")
            return await original_can_handle_0(*args)

        async def mock_process_0(*args):
            handler_calls.append("handler0_process")
            await original_process_0(*args)

        async def mock_can_handle_1(*args):
            handler_calls.append("handler1_can")
            return await original_can_handle_1(*args)

        async def mock_process_1(*args):
            handler_calls.append("handler1_process")
            await original_process_1(*args)

        processor.handlers[0].can_handle = mock_can_handle_0
        processor.handlers[0].process = mock_process_0
        processor.handlers[1].can_handle = mock_can_handle_1
        processor.handlers[1].process = mock_process_1

        await processor.process_all([external_doi_identifier])

        # Publication handler (index 1) should process, Zenodo handler (index 0) should check but not process
        assert "handler0_can" in handler_calls
        assert "handler1_can" in handler_calls
        assert "handler1_process" in handler_calls
        assert "handler0_process" not in handler_calls
