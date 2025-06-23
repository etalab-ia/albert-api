from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._documentmanager import DocumentManager
from app.schemas.documents import Chunker
from app.schemas.parse import ParsedDocument, ParsedDocumentMetadata, ParsedDocumentPage
from app.utils.exceptions import CollectionNotFoundException


@pytest.mark.asyncio
async def test_create_document_collection_no_longer_exists():
    """Test that CollectionNotFoundException is raised when collection is deleted during document creation."""

    # Mock dependencies
    mock_vectore_store = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)

    # Create DocumentManager instance
    document_manager = DocumentManager(vector_store=mock_vectore_store, parser=mock_parser)

    # Mock the collection existence check to pass initially
    mock_collection_result = MagicMock()
    mock_collection_result.scalar_one.return_value = MagicMock()  # Collection exists
    mock_session.execute.return_value = mock_collection_result

    # Create a mock parsed document
    mock_metadata = ParsedDocumentMetadata(document_name="test_doc.txt")
    mock_data = ParsedDocumentPage(content="Test document content", images={}, metadata=mock_metadata)
    mock_document = ParsedDocument(data=[mock_data])

    # Mock the _split method to return some chunks
    mock_chunks = [MagicMock()]
    with patch.object(document_manager, "_split", return_value=mock_chunks):
        # Configure the session.execute to:
        # 1. First call: return collection exists (for the initial check)
        # 2. Second call: raise IntegrityError with foreign key constraint message
        def side_effect(*args, **kwargs):
            statement_str = str(kwargs["statement"])
            if "INSERT INTO document" in statement_str or "document" in statement_str.lower():
                # This is the insert statement that should fail
                raise IntegrityError(statement="INSERT INTO document", params={}, orig=Exception("foreign key constraint fails"))
            else:
                # This is the collection check that should pass
                return mock_collection_result

        mock_session.execute.side_effect = side_effect

        # Test that the exception is raised with the correct message
        with pytest.raises(CollectionNotFoundException) as exc_info:
            await document_manager.create_document(
                session=mock_session,
                user_id=1,
                collection_id=123,
                document=mock_document,
                chunker=Chunker.RECURSIVE_CHARACTER_TEXT_SPLITTER,
                chunk_size=1000,
                chunk_overlap=100,
                length_function=len,
                is_separator_regex=False,
                separators=["\n\n", "\n", " "],
                chunk_min_size=50,
            )

        # Verify the exception message contains the collection ID
        assert "Collection 123 no longer exists" in str(exc_info.value.detail)
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_document_collection_no_longer_exists_with_fkey_error():
    """Test that CollectionNotFoundException is raised when fkey constraint fails."""

    # Mock dependencies
    mock_vectore_store = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)

    # Create DocumentManager instance
    document_manager = DocumentManager(vector_store=mock_vectore_store, parser=mock_parser)

    # Mock the collection existence check to pass initially
    mock_collection_result = MagicMock()
    mock_collection_result.scalar_one.return_value = MagicMock()  # Collection exists
    mock_session.execute.return_value = mock_collection_result

    # Create a mock parsed document
    mock_metadata = ParsedDocumentMetadata(document_name="test_doc.txt")
    mock_data = ParsedDocumentPage(content="Test document content", images={}, metadata=mock_metadata)
    mock_document = ParsedDocument(data=[mock_data])

    # Mock the _split method to return some chunks
    mock_chunks = [MagicMock()]
    with patch.object(document_manager, "_split", return_value=mock_chunks):
        # Configure the session.execute to raise IntegrityError with fkey message
        def side_effect(*args, **kwargs):
            statement_str = str(kwargs["statement"])
            if "INSERT INTO document" in statement_str or "document" in statement_str.lower():
                # This is the insert statement that should fail with fkey error
                raise IntegrityError(statement="INSERT INTO document", params={}, orig=Exception("fkey constraint violation"))
            else:
                # This is the collection check that should pass
                return mock_collection_result

        mock_session.execute.side_effect = side_effect

        # Test that the exception is raised with the correct message
        with pytest.raises(CollectionNotFoundException) as exc_info:
            await document_manager.create_document(
                session=mock_session,
                user_id=1,
                collection_id=456,
                document=mock_document,
                chunker=Chunker.RECURSIVE_CHARACTER_TEXT_SPLITTER,
                chunk_size=1000,
                chunk_overlap=100,
                length_function=len,
                is_separator_regex=False,
                separators=["\n\n", "\n", " "],
                chunk_min_size=50,
            )

        # Verify the exception message contains the collection ID
        assert "Collection 456 no longer exists" in str(exc_info.value.detail)
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_document_other_integrity_error_not_collection_related():
    """Test that other IntegrityErrors are not caught and converted to CollectionNotFoundException."""

    # Mock dependencies
    mock_vectore_store = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)

    # Create DocumentManager instance
    document_manager = DocumentManager(vector_store=mock_vectore_store, parser=mock_parser)

    # Mock the collection existence check to pass initially
    mock_collection_result = MagicMock()
    mock_collection_result.scalar_one.return_value = MagicMock()  # Collection exists
    mock_session.execute.return_value = mock_collection_result

    # Create a mock parsed document
    mock_metadata = ParsedDocumentMetadata(document_name="test_doc.txt")
    mock_data = ParsedDocumentPage(content="Test document content", images={}, metadata=mock_metadata)
    mock_document = ParsedDocument(data=[mock_data])

    # Mock the _split method to return some chunks
    mock_chunks = [MagicMock()]
    with patch.object(document_manager, "_split", return_value=mock_chunks):
        # Configure the session.execute to raise IntegrityError without foreign key message
        def side_effect(*args, **kwargs):
            statement_str = str(kwargs["statement"])
            if "INSERT INTO document" in statement_str or "document" in statement_str.lower():
                # This is the insert statement that should fail with non-fkey error
                raise IntegrityError(statement="INSERT INTO document", params={}, orig=Exception("unique constraint violation"))
            else:
                # This is the collection check that should pass
                return mock_collection_result

        mock_session.execute.side_effect = side_effect

        # Test that the original IntegrityError is raised, not CollectionNotFoundException
        with pytest.raises(IntegrityError):
            await document_manager.create_document(
                session=mock_session,
                user_id=1,
                collection_id=789,
                document=mock_document,
                chunker=Chunker.RECURSIVE_CHARACTER_TEXT_SPLITTER,
                chunk_size=1000,
                chunk_overlap=100,
                length_function=len,
                is_separator_regex=False,
                separators=["\n\n", "\n", " "],
                chunk_min_size=50,
            )
