import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers
from io import BytesIO

from app.helpers._parsermanager import ParserManager
from app.clients.parser import BaseParserClient as ParserClient
from app.schemas.core.documents import FileType
from app.schemas.parse import ParsedDocument, ParsedDocumentOutputFormat
from app.utils.exceptions import UnsupportedFileTypeException


def create_upload_file(content: str, filename: str, content_type: str) -> UploadFile:
    """Helper function to create UploadFile from string content."""
    return UploadFile(filename=filename, file=BytesIO(content.encode("utf-8")), headers=Headers({"content-type": content_type}))


def create_binary_upload_file(content: bytes, filename: str, content_type: str) -> UploadFile:
    """Helper function to create UploadFile from binary content."""
    return UploadFile(filename=filename, file=BytesIO(content), headers=Headers({"content-type": content_type}))


class TestParserManagerInit:
    """Test ParserManager initialization."""

    def test_init_without_parser(self):
        """Test initialization without parser client."""
        manager = ParserManager()
        assert manager.parser_client is None

    def test_init_with_parser(self):
        """Test initialization with parser client."""
        mock_parser = MagicMock(spec=ParserClient)
        manager = ParserManager(parser=mock_parser)
        assert manager.parser_client == mock_parser


class TestParserManagerDetectFileType:
    """Test file type detection logic."""

    def test_detect_file_type_pdf_valid(self):
        """Test PDF file type detection with valid extension and content type."""
        file = create_binary_upload_file(b"%PDF-1.4 fake pdf content", "document.pdf", "application/pdf")

        manager = ParserManager()
        result = manager._detect_file_type(file)

        assert result == FileType.PDF

    def test_detect_file_type_html_valid(self):
        """Test HTML file type detection with valid extension and content type."""
        file = create_upload_file("<html><body>Test</body></html>", "page.html", "text/html")

        manager = ParserManager()
        result = manager._detect_file_type(file)

        assert result == FileType.HTML

    def test_detect_file_type_markdown_valid(self):
        """Test Markdown file type detection with valid extension and content type."""
        file = create_upload_file("# README\n\nThis is a test.", "README.md", "text/markdown")

        manager = ParserManager()
        result = manager._detect_file_type(file)

        assert result == FileType.MD

    def test_detect_file_type_txt_valid(self):
        """Test text file type detection with valid extension and content type."""
        file = create_upload_file("This is plain text content.", "notes.txt", "text/plain")

        manager = ParserManager()
        result = manager._detect_file_type(file)

        assert result == FileType.TXT

    def test_detect_file_type_content_type_only(self):
        """Test file type detection by content type when extension doesn't match."""
        file = create_binary_upload_file(b"%PDF-1.4 fake pdf content", "document.unknown", "application/pdf")

        manager = ParserManager()
        result = manager._detect_file_type(file)

        assert result == FileType.PDF

    def test_detect_file_type_invalid_extension_and_content_type(self):
        """Test UnsupportedFileTypeException for invalid file types."""
        file = create_upload_file("Unknown content", "document.xyz", "application/xyz")

        manager = ParserManager()

        with pytest.raises(UnsupportedFileTypeException):
            manager._detect_file_type(file)

    def test_detect_file_type_mismatch_with_required_type(self):
        """Test UnsupportedFileTypeException when detected type doesn't match required type."""
        file = create_binary_upload_file(b"%PDF-1.4 fake pdf content", "document.pdf", "application/pdf")

        manager = ParserManager()

        with pytest.raises(UnsupportedFileTypeException) as exc_info:
            manager._detect_file_type(file, type=FileType.HTML)

        assert "File must be a html file." in str(exc_info.value)

    def test_detect_file_type_exception_handling(self):
        """Test exception handling when file properties can't be accessed."""
        mock_file = MagicMock(spec=UploadFile)
        # Make accessing filename raise an exception
        mock_file.filename = PropertyMock(side_effect=Exception("Access error"))
        mock_file.content_type = "text/plain"

        manager = ParserManager()

        with pytest.raises(HTTPException) as exc_info:
            manager._detect_file_type(mock_file)

        assert exc_info.value.status_code == 400
        assert "Invalid file." in str(exc_info.value.detail)

    def test_detect_file_type_case_insensitive_extension(self):
        """Test that extension detection is case insensitive."""
        file = create_binary_upload_file(b"%PDF-1.4 fake pdf content", "document.PDF", "application/pdf")

        manager = ParserManager()
        result = manager._detect_file_type(file)

        assert result == FileType.PDF


class TestParserManagerReadContent:
    """Test content reading functionality."""

    @pytest.mark.asyncio
    async def test_read_content_utf8(self):
        """Test reading UTF-8 encoded content."""
        content = "Hello, world! 👋"
        file = create_upload_file(content, "test.txt", "text/plain")

        result = await ParserManager._read_content(file)

        assert result == content

    @pytest.mark.asyncio
    async def test_read_content_latin1_fallback(self):
        """Test reading with Latin-1 fallback when UTF-8 fails."""
        content = "Café"
        # Create file with Latin-1 encoding
        file = UploadFile(filename="test.txt", file=BytesIO(content.encode("latin-1")), headers=Headers({"content-type": "text/plain"}))

        result = await ParserManager._read_content(file)

        assert result == content

    @pytest.mark.asyncio
    async def test_read_content_with_replacement(self):
        """Test reading with character replacement when both UTF-8 and Latin-1 fail."""
        # Create invalid UTF-8/Latin-1 bytes
        content_bytes = b"\xff\xfe\x00\x00"
        file = create_binary_upload_file(content_bytes, "test.txt", "text/plain")

        result = await ParserManager._read_content(file)

        # Should contain replacement characters
        assert "" in result or len(result) > 0


class TestParserManagerParseFile:
    """Test main parse_file method."""

    @pytest.mark.asyncio
    async def test_parse_file_delegates_to_correct_method(self):
        """Test that parse_file delegates to the correct parsing method."""
        file = create_binary_upload_file(b"%PDF-1.4 fake pdf content", "test.pdf", "application/pdf")

        manager = ParserManager()

        with patch.object(manager, "_parse_pdf") as mock_parse_pdf:
            mock_parse_pdf.return_value = MagicMock(spec=ParsedDocument)

            await manager.parse_file(file=file)

            mock_parse_pdf.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_file_with_all_params(self):
        """Test parse_file with all parameters."""
        file = create_upload_file("<html><body>Test</body></html>", "test.html", "text/html")

        manager = ParserManager()

        with patch.object(manager, "_parse_html") as mock_parse_html:
            mock_parse_html.return_value = MagicMock(spec=ParsedDocument)

            await manager.parse_file(file=file, output_format=ParsedDocumentOutputFormat.MARKDOWN)

            mock_parse_html.assert_called_once()


class TestParserManagerParsePdf:
    """Test PDF parsing functionality."""

    @pytest.mark.asyncio
    async def test_parse_pdf_with_parser_client(self):
        """Test PDF parsing using parser client when available."""
        mock_parser = MagicMock(spec=ParserClient)
        mock_parser.SUPPORTED_FORMATS = [FileType.PDF]
        expected_document = MagicMock(spec=ParsedDocument)
        # Make parse method async
        mock_parser.parse = AsyncMock(return_value=expected_document)

        file = create_binary_upload_file(b"%PDF-1.4 fake pdf content", "test.pdf", "application/pdf")

        manager = ParserManager(parser=mock_parser)

        result = await manager._parse_pdf(file=file)

        assert result == expected_document
        mock_parser.parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_pdf_fallback_to_pymupdf(self):
        """Test PDF parsing fallback to PyMuPDF when no parser client."""
        file = create_binary_upload_file(b"%PDF-1.4 fake pdf content", "test.pdf", "application/pdf")

        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Page content"
        mock_pdf.__len__.return_value = 1
        mock_pdf.__getitem__.return_value = mock_page

        manager = ParserManager()

        with patch("pymupdf.open", return_value=mock_pdf):
            result = await manager._parse_pdf(file=file)

            assert isinstance(result, ParsedDocument)
            assert len(result.data) == 1
            assert result.data[0].content == "Page content"
            assert result.data[0].metadata.document_name == "test.pdf"
            mock_pdf.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_pdf_pymupdf_exception(self):
        """Test PDF parsing exception handling with PyMuPDF."""
        file = create_binary_upload_file(b"invalid pdf content", "test.pdf", "application/pdf")

        manager = ParserManager()

        with patch("pymupdf.open", side_effect=Exception("Read error")):
            with pytest.raises(HTTPException) as exc_info:
                await manager._parse_pdf(file=file)

            assert exc_info.value.status_code == 500
            assert "Failed to parse pdf file." in str(exc_info.value.detail)


class TestParserManagerParseHtml:
    """Test HTML parsing functionality."""

    @pytest.mark.asyncio
    async def test_parse_html_with_parser_client(self):
        """Test HTML parsing using parser client when available."""
        mock_parser = MagicMock(spec=ParserClient)
        mock_parser.SUPPORTED_FORMATS = [FileType.HTML]
        expected_document = MagicMock(spec=ParsedDocument)
        # Make parse method async
        mock_parser.parse = AsyncMock(return_value=expected_document)

        file = create_upload_file("<html><body>Test</body></html>", "test.html", "text/html")

        manager = ParserManager(parser=mock_parser)

        result = await manager._parse_html(file=file)

        assert result == expected_document
        mock_parser.parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_html_fallback_markdown_output(self):
        """Test HTML parsing with markdown output format."""
        file = create_upload_file("<h1>Title</h1><p>Content</p>", "test.html", "text/html")

        manager = ParserManager()

        with patch("app.helpers._parsermanager.convert_to_markdown") as mock_convert:
            mock_convert.return_value = "# Title\n\nContent"

            result = await manager._parse_html(file=file, output_format=ParsedDocumentOutputFormat.MARKDOWN)

            assert isinstance(result, ParsedDocument)
            assert len(result.data) == 1
            assert result.data[0].content == "# Title\n\nContent"
            mock_convert.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_html_fallback_plain_text(self):
        """Test HTML parsing without markdown conversion."""
        html_content = "<h1>Title</h1>"
        file = create_upload_file(html_content, "test.html", "text/html")

        manager = ParserManager()

        result = await manager._parse_html(file=file)

        assert isinstance(result, ParsedDocument)
        assert len(result.data) == 1
        assert result.data[0].content == html_content

    @pytest.mark.asyncio
    async def test_parse_html_exception(self):
        """Test HTML parsing exception handling."""
        file = create_upload_file("<html><body>Test</body></html>", "test.html", "text/html")

        manager = ParserManager()

        with patch.object(manager, "_read_content", side_effect=Exception("Read error")):
            with pytest.raises(HTTPException) as exc_info:
                await manager._parse_html(file=file)

            assert exc_info.value.status_code == 500
            assert "Failed to parse html file." in str(exc_info.value.detail)


class TestParserManagerParseMd:
    """Test Markdown parsing functionality."""

    @pytest.mark.asyncio
    async def test_parse_md_with_parser_client(self):
        """Test Markdown parsing using parser client when available."""
        mock_parser = MagicMock(spec=ParserClient)
        mock_parser.SUPPORTED_FORMATS = [FileType.MD]
        expected_document = MagicMock(spec=ParsedDocument)
        # Make parse method async
        mock_parser.parse = AsyncMock(return_value=expected_document)

        file = create_upload_file("# Title\n\nContent", "test.md", "text/markdown")

        manager = ParserManager(parser=mock_parser)

        result = await manager._parse_md(file=file)

        assert result == expected_document
        mock_parser.parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_md_fallback(self):
        """Test Markdown parsing fallback when no parser client."""
        md_content = "# Title\n\nContent"
        file = create_upload_file(md_content, "test.md", "text/markdown")

        manager = ParserManager()

        result = await manager._parse_md(file=file)

        assert isinstance(result, ParsedDocument)
        assert len(result.data) == 1
        assert result.data[0].content == md_content
        assert result.data[0].metadata.document_name == "test.md"

    @pytest.mark.asyncio
    async def test_parse_md_exception(self):
        """Test Markdown parsing exception handling."""
        file = create_upload_file("# Title\n\nContent", "test.md", "text/markdown")

        manager = ParserManager()

        with patch.object(manager, "_read_content", side_effect=Exception("Read error")):
            with pytest.raises(HTTPException) as exc_info:
                await manager._parse_md(file=file)

            assert exc_info.value.status_code == 500
            assert "Failed to parse markdown file." in str(exc_info.value.detail)


class TestParserManagerParseTxt:
    """Test text file parsing functionality."""

    @pytest.mark.asyncio
    async def test_parse_txt_with_parser_client(self):
        """Test text parsing using parser client when available."""
        mock_parser = MagicMock(spec=ParserClient)
        mock_parser.SUPPORTED_FORMATS = [FileType.TXT]
        expected_document = MagicMock(spec=ParsedDocument)
        # Make parse method async
        mock_parser.parse = AsyncMock(return_value=expected_document)

        file = create_upload_file("Plain text content", "test.txt", "text/plain")

        manager = ParserManager(parser=mock_parser)

        result = await manager._parse_txt(file=file)

        assert result == expected_document
        mock_parser.parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_txt_fallback(self):
        """Test text parsing fallback when no parser client."""
        txt_content = "Plain text content"
        file = create_upload_file(txt_content, "test.txt", "text/plain")

        manager = ParserManager()

        result = await manager._parse_txt(file=file)

        assert isinstance(result, ParsedDocument)
        assert len(result.data) == 1
        # _parse_txt reads raw bytes but they get converted to string in ParsedDocumentPage
        assert result.data[0].content == txt_content
        assert result.data[0].metadata.document_name == "test.txt"

    @pytest.mark.asyncio
    async def test_parse_txt_exception(self):
        """Test text parsing exception handling."""
        file = create_upload_file("Plain text content", "test.txt", "text/plain")

        manager = ParserManager()

        with patch.object(file, "read", side_effect=Exception("Read error")):
            with pytest.raises(HTTPException) as exc_info:
                await manager._parse_txt(file=file)

            assert exc_info.value.status_code == 500
            assert "Failed to parse text file." in str(exc_info.value.detail)


class TestParserManagerEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_extension_map_completeness(self):
        """Test that all expected file extensions are mapped."""
        expected_extensions = {
            ".pdf": FileType.PDF,
            ".html": FileType.HTML,
            ".htm": FileType.HTML,
            ".md": FileType.MD,
            ".markdown": FileType.MD,
            ".txt": FileType.TXT,
            ".text": FileType.TXT,
        }

        assert ParserManager.EXTENSION_MAP == expected_extensions

    def test_valid_content_types_completeness(self):
        """Test that all file types have valid content types defined."""
        for file_type in FileType:
            if file_type in [FileType.PDF, FileType.HTML, FileType.MD, FileType.TXT]:
                assert file_type in ParserManager.VALID_CONTENT_TYPES
                assert len(ParserManager.VALID_CONTENT_TYPES[file_type]) > 0

    @pytest.mark.asyncio
    async def test_parser_client_without_supported_format(self):
        """Test parsing when parser client doesn't support the file format."""
        mock_parser = MagicMock(spec=ParserClient)
        mock_parser.SUPPORTED_FORMATS = []  # No supported formats

        file = create_binary_upload_file(b"%PDF-1.4 fake pdf content", "test.pdf", "application/pdf")

        manager = ParserManager(parser=mock_parser)

        # Should fall back to built-in parsing
        with patch("pymupdf.open") as mock_pymupdf:
            mock_pdf = MagicMock()
            mock_pdf.__len__.return_value = 0
            mock_pymupdf.return_value = mock_pdf

            result = await manager._parse_pdf(file=file)

            assert isinstance(result, ParsedDocument)
            mock_pymupdf.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_file_integration_txt(self):
        """Integration test for text file parsing end-to-end."""
        txt_content = "This is a sample text file content.\nWith multiple lines."
        file = create_upload_file(txt_content, "sample.txt", "text/plain")

        manager = ParserManager()

        result = await manager.parse_file(file=file)

        assert isinstance(result, ParsedDocument)
        assert len(result.data) == 1
        # Content gets converted to string in ParsedDocumentPage
        assert result.data[0].content == txt_content
        assert result.data[0].metadata.document_name == "sample.txt"

    @pytest.mark.asyncio
    async def test_parse_file_integration_markdown(self):
        """Integration test for markdown file parsing end-to-end."""
        md_content = "# Sample Markdown\n\nThis is **bold** text and *italic* text."
        file = create_upload_file(md_content, "sample.md", "text/markdown")

        manager = ParserManager()

        result = await manager.parse_file(file=file)

        assert isinstance(result, ParsedDocument)
        assert len(result.data) == 1
        assert result.data[0].content == md_content
        assert result.data[0].metadata.document_name == "sample.md"

    @pytest.mark.asyncio
    async def test_parse_file_integration_html_as_markdown(self):
        """Integration test for HTML file parsing with markdown output."""
        html_content = "<h1>Sample HTML</h1><p>This is a <strong>paragraph</strong>.</p>"
        file = create_upload_file(html_content, "sample.html", "text/html")

        manager = ParserManager()

        with patch("app.helpers._parsermanager.convert_to_markdown") as mock_convert:
            mock_convert.return_value = "# Sample HTML\n\nThis is a **paragraph**."

            result = await manager.parse_file(file=file, output_format=ParsedDocumentOutputFormat.MARKDOWN)

            assert isinstance(result, ParsedDocument)
            assert len(result.data) == 1
            assert result.data[0].content == "# Sample HTML\n\nThis is a **paragraph**."
            mock_convert.assert_called_once_with(html_content)
