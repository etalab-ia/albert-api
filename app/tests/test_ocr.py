import ast
import json
import os

from fastapi.testclient import TestClient
import pytest

from app.utils.variables import ENDPOINT__OCR
from app.schemas.models import ModelType
from app.tests.utils.snapshot_assertions import assert_snapshot_almost_equal

current_path = os.path.dirname(__file__)


@pytest.fixture(scope="module")
def model_id(client: TestClient):
    """Fixture to get model ID for OCR tests. Should be the second model in config.yml."""
    response = client.get("/v1/models")
    assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
    response_json = response.json()
    model = [model for model in response_json["data"] if model["type"] == ModelType.IMAGE_TEXT_TO_TEXT][0]
    model_id = model["id"]

    yield model_id


@pytest.mark.usefixtures("client", "model_id")
class TestOCR:
    def test_ocr_pdf_successful(self, client: TestClient, model_id, snapshot):
        """Test successful OCR processing of a PDF file."""

        file_path = os.path.join(current_path, "assets/pdf.pdf")
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(f"/v1{ENDPOINT__OCR}", files=files, json={"model": model_id})

        assert response.status_code == 200, f"error: process OCR ({response.status_code})"
        # # Load the expected snapshot
        snapshot_path = os.path.join(current_path, "snapshots/test_ocr/test_ocr_pdf_successful/ocr_pdf_successful")
        if os.path.exists(snapshot_path):
            with open(snapshot_path) as f:
                expected_snapshot = ast.literal_eval(f.read())
                assert_snapshot_almost_equal(actual=json.dumps(response.json()), expected_snapshot=json.dumps(expected_snapshot), threshold=0.50)
        else:
            snapshot.assert_match(str(response.json()), "ocr_pdf_successful")

    def test_ocr_invalid_file_type(self, client: TestClient, model_id, snapshot):
        """Test OCR with invalid file type (not PDF)."""
        file_path = os.path.join(current_path, "assets/json.json")
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/json")}
            response = client.post_without_permissions(f"/v1{ENDPOINT__OCR}", files=files, json={"model": model_id, "dpi": 150})

        assert response.status_code == 400, response.text
        snapshot.assert_match(str(response.json()), "ocr_invalid_file_type")

    def test_ocr_too_large_file(self, client: TestClient, model_id, snapshot):
        """Test OCR with a file that exceeds size limit."""
        file_path = os.path.join(current_path, "assets/pdf_too_large.pdf")
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(f"/v1{ENDPOINT__OCR}", files=files, json={"model": model_id, "dpi": 150})

        assert response.status_code == 413, response.text
        snapshot.assert_match(str(response.json()), "ocr_too_large_file")

    def test_ocr_without_authentication(self, client, model_id, snapshot):
        """Test OCR without authentication."""
        client.headers = {}  # Remove auth headers

        file_path = os.path.join(current_path, "assets/pdf.pdf")
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post(f"/v1{ENDPOINT__OCR}", files=files, json={"model": model_id, "dpi": 150})

        assert response.status_code == 403, f"error: should require authentication ({response.status_code})"
        snapshot.assert_match(str(response.json()), "ocr_without_authentication")

    def test_ocr_custom_dpi(self, client, model_id, snapshot):
        """Test OCR with custom DPI setting."""
        file_path = os.path.join(current_path, "assets/pdf.pdf")
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(f"/v1{ENDPOINT__OCR}", files=files, json={"model": model_id, "dpi": 300})

        assert response.status_code == 200, f"process OCR with custom DPI ({response.status_code})"
        snapshot_path = os.path.join(current_path, "snapshots/test_ocr/test_ocr_custom_dpi/ocr_custom_dpi")
        if os.path.exists(snapshot_path):
            with open(snapshot_path) as f:
                expected_snapshot = ast.literal_eval(f.read())
                assert_snapshot_almost_equal(actual=json.dumps(response.json()), expected_snapshot=json.dumps(expected_snapshot), threshold=0.50)
        else:
            snapshot.assert_match(str(response.json()), "ocr_custom_dpi")
