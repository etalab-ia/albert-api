from unittest.mock import AsyncMock, MagicMock

from fastapi import Request
import pytest

from app.helpers._accesscontroller import AccessController


class MockUploadFile:
    """Mock UploadFile for testing"""

    def __init__(self, filename, content_type, content=b""):
        self.filename = filename
        self.content_type = content_type
        self.size = len(content)
        self._content = content


class TestAccessController:
    @pytest.fixture
    def access_controller(self):
        return AccessController()

    @pytest.mark.asyncio
    async def test_safely_parse_body_valid_json(self, access_controller):
        """Test parsing valid JSON body"""
        request = MagicMock(spec=Request)
        request.body = AsyncMock(return_value=b'{"key": "value"}')
        request.headers = {"content-type": "application/json"}

        result = await access_controller._safely_parse_body(request)

        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_safely_parse_body_empty_body(self, access_controller):
        """Test parsing empty body"""
        request = MagicMock(spec=Request)
        request.body = AsyncMock(return_value=b"")
        request.headers = {"content-type": "application/json"}

        result = await access_controller._safely_parse_body(request)

        assert result == {}

    @pytest.mark.asyncio
    async def test_safely_parse_body_multipart_form(self, access_controller):
        """Test parsing multipart form data with file upload"""
        request = MagicMock(spec=Request)
        request.headers = {"content-type": "multipart/form-data; boundary=something"}

        # Mock form data with file upload
        mock_file = MockUploadFile("test.pdf", "application/pdf", b"PDF content")
        mock_form = {"file": mock_file, "field": "value"}
        request.form = AsyncMock(return_value=mock_form)

        result = await access_controller._safely_parse_body(request)

        assert "file" in result
        assert result["file"]["filename"] == "test.pdf"
        assert result["file"]["content_type"] == "application/pdf"
        assert result["field"] == "value"

    @pytest.mark.asyncio
    async def test_safely_parse_body_url_encoded_form(self, access_controller):
        """Test parsing URL-encoded form data"""
        request = MagicMock(spec=Request)
        request.headers = {"content-type": "application/x-www-form-urlencoded"}

        mock_form = {"key1": "value1", "key2": "value2"}
        request.form = AsyncMock(return_value=mock_form)

        result = await access_controller._safely_parse_body(request)

        assert result == {"key1": "value1", "key2": "value2"}

    @pytest.mark.asyncio
    async def test_safely_parse_body_invalid_utf8(self, access_controller):
        """Test parsing body with invalid UTF-8 bytes (like PDF content)"""
        # This is the actual problematic body from the file upload
        pdf_multipart_body = (
            b"--660170e79ebf4c68cbb7fd12dd84478f\r\n"
            b'Content-Disposition: form-data; name="file"; filename="managerial_paye.pdf"\r\n'
            b"Content-Type: application/pdf\r\n\r\n"
            b"%PDF-1.5\r\n%\xb5\xb5\xb5\xb5\r\n"  # Invalid UTF-8 bytes
            b"1 0 obj\r\n"
            b"<</Type/Catalog/Pages 2 0 R/Lang(fr-FR) /StructTreeRoot 50 0 R/MarkInfo<</Marked true>>>>\r\n"
        )

        request = MagicMock(spec=Request)
        request.body = AsyncMock(return_value=pdf_multipart_body)
        request.headers = {"content-type": "application/json"}  # Mismatched content type

        # This should not raise UnicodeDecodeError anymore
        result = await access_controller._safely_parse_body(request)

        # Since it's not valid JSON, it should return empty dict
        assert result == {}

    @pytest.mark.asyncio
    async def test_safely_parse_body_form_parsing_error(self, access_controller):
        """Test handling of form parsing errors"""
        request = MagicMock(spec=Request)
        request.headers = {"content-type": "multipart/form-data"}
        request.form = AsyncMock(side_effect=Exception("Form parsing error"))

        result = await access_controller._safely_parse_body(request)

        assert result == {}

    @pytest.mark.asyncio
    async def test_safely_parse_body_invalid_json(self, access_controller):
        """Test parsing invalid JSON"""
        request = MagicMock(spec=Request)
        request.body = AsyncMock(return_value=b'{"invalid": json}')
        request.headers = {"content-type": "application/json"}

        result = await access_controller._safely_parse_body(request)

        assert result == {}

    @pytest.mark.asyncio
    async def test_safely_parse_body_utf8_with_replacement(self, access_controller):
        """Test that invalid UTF-8 bytes are replaced, not cause errors"""
        request = MagicMock(spec=Request)
        # Create a string with invalid UTF-8 that would still be parseable as JSON after replacement
        invalid_utf8_json = b'{"message": "Hello \xb5 World"}'
        request.body = AsyncMock(return_value=invalid_utf8_json)
        request.headers = {"content-type": "application/json"}

        result = await access_controller._safely_parse_body(request)

        # Should successfully parse with replacement character
        assert "message" in result
        assert "Hello" in result["message"]
        assert "World" in result["message"]

    @pytest.mark.asyncio
    async def test_safely_parse_body_none_body(self, access_controller):
        """Test parsing None body"""
        request = MagicMock(spec=Request)
        request.body = AsyncMock(return_value=None)
        request.headers = {"content-type": "application/json"}

        result = await access_controller._safely_parse_body(request)

        assert result == {}

    @pytest.mark.asyncio
    async def test_safely_parse_body_no_content_type(self, access_controller):
        """Test parsing when no content-type header is present"""
        request = MagicMock(spec=Request)
        request.body = AsyncMock(return_value=b'{"key": "value"}')
        request.headers = {}  # No content-type header

        result = await access_controller._safely_parse_body(request)

        # Should default to JSON parsing
        assert result == {"key": "value"}
