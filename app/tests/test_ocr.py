import os

from fastapi.testclient import TestClient
import pytest

from app.utils.variables import ENDPOINT__OCR


@pytest.fixture(scope="module")
def setup(client: TestClient):
    """Fixture to get model ID for OCR tests. Should be the second model in config.yml."""
    MODEL_ID = "mistralai/Mistral-Small-3.1-24B-Instruct-2503"

    yield MODEL_ID


@pytest.mark.usefixtures("client", "setup")
class TestOCR:
    def test_ocr_pdf_successful(self, client: TestClient, setup):
        """Test successful OCR processing of a PDF file."""
        MODEL_ID = setup
        file_path = "app/tests/assets/pdf.pdf"

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(f"/v1{ENDPOINT__OCR}", files=files, json={"model": MODEL_ID})

        assert response.status_code == 200, response.text

    def test_ocr_invalid_file_type(self, client: TestClient, setup, snapshot):
        """Test OCR with invalid file type (not PDF)."""
        MODEL_ID = setup
        file_path = "app/tests/assets/json.json"

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/json")}
            response = client.post_without_permissions(f"/v1{ENDPOINT__OCR}", files=files, json={"model": MODEL_ID, "dpi": 150})

        assert response.status_code == 400, response.text
        snapshot.assert_match(str(response.json()), "ocr_invalid_file_type")

    def test_ocr_too_large_file(self, client: TestClient, setup, snapshot):
        """Test OCR with a file that exceeds size limit."""
        MODEL_ID = setup
        file_path = "app/tests/assets/pdf_too_large.pdf"

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(f"/v1{ENDPOINT__OCR}", files=files, json={"model": MODEL_ID, "dpi": 150})

        assert response.status_code == 413, response.text
        snapshot.assert_match(str(response.json()), "ocr_too_large_file")

    def test_ocr_custom_dpi(self, client: TestClient, setup):
        """Test OCR with custom DPI setting."""
        MODEL_ID = setup
        file_path = "app/tests/assets/pdf.pdf"

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(f"/v1{ENDPOINT__OCR}", files=files, json={"model": MODEL_ID, "dpi": 300})

        assert response.status_code == 200, response.text
