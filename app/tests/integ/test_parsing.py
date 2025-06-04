# Test à faire, regarder le test ocr
# Faire des tests pour le endpoint parse, le client marker ? la classe parse ?


import os

import pytest
from fastapi.testclient import TestClient

from app.utils.variables import ENDPOINT__PARSE

current_path = os.path.dirname(__file__)


@pytest.mark.usefixtures("client")
class TestParsingEndpoint:
    def test_parser_pdf_successful(self, client: TestClient):
        """Test successful OCR processing of a PDF file."""

        file_path = os.path.join(current_path, "assets/pdf.pdf")
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(f"/v1{ENDPOINT__PARSE}", files=files)

        assert response.status_code == 200, response.data[0].content
