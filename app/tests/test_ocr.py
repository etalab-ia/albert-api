import ast
import json
import os

import pytest

from app.utils.variables import ENDPOINT__OCR, MODEL_TYPE__LANGUAGE
from app.tests.utils.snapshot_assertions import assert_snapshot_almost_equal

current_path = os.path.dirname(__file__)


@pytest.fixture(scope="module")
def model_id(args, test_client):
    """Fixture to get model ID for OCR tests. Should be the second model in config.yml."""
    test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}
    # get a language model
    response = test_client.get("/v1/models")
    assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
    response_json = response.json()
    model = [model for model in response_json["data"] if model["type"] == MODEL_TYPE__LANGUAGE][1]
    MODEL_ID = model["id"]

    yield MODEL_ID


@pytest.mark.usefixtures("args", "model_id", "test_client")
class TestOCR:
    def test_ocr_pdf_successful(self, args, test_client, snapshot):
        """Test successful OCR processing of a PDF file."""
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}

        file_path = os.path.join(current_path, "assets/pdf.pdf")
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = test_client.post(
                f"/v1{ENDPOINT__OCR}",
                files=files,
            )

        assert response.status_code == 200, f"error: process OCR ({response.status_code})"
        # # Load the expected snapshot
        snapshot_path = os.path.join(
            current_path,
            "snapshots/test_ocr/test_ocr_pdf_successful/ocr_pdf_successful",
        )
        if os.path.exists(snapshot_path):
            with open(snapshot_path) as f:
                expected_snapshot = ast.literal_eval(f.read())
                assert_snapshot_almost_equal(actual=json.dumps(response.json()), expected_snapshot=json.dumps(expected_snapshot), threshold=0.90)
        else:
            snapshot.assert_match(str(response.json()), "ocr_pdf_successful")

    def test_ocr_invalid_file_type(self, args, test_client, model_id, snapshot):
        """Test OCR with invalid file type (not PDF)."""
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}

        file_path = os.path.join(current_path, "assets/json.json")
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/json")}
            response = test_client.post(f"/v1{ENDPOINT__OCR}", files=files, json={"model": model_id, "dpi": 150})

        assert response.status_code == 400, f"error: should reject non-PDF file ({response.status_code})"
        snapshot.assert_match(str(response.json()), "ocr_invalid_file_type")

    def test_ocr_too_large_file(self, args, test_client, model_id, snapshot):
        """Test OCR with a file that exceeds size limit."""
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}

        file_path = os.path.join(current_path, "assets/pdf_too_large.pdf")
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = test_client.post(f"/v1{ENDPOINT__OCR}", files=files, json={"model": model_id, "dpi": 150})

        assert response.status_code == 413, f"error: should reject too large file ({response.status_code})"
        snapshot.assert_match(str(response.json()), "ocr_too_large_file")

    def test_ocr_without_authentication(self, test_client, model_id, snapshot):
        """Test OCR without authentication."""
        test_client.headers = {}  # Remove auth headers

        file_path = os.path.join(current_path, "assets/pdf.pdf")
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = test_client.post(f"/v1{ENDPOINT__OCR}", files=files, json={"model": model_id, "dpi": 150})

        assert response.status_code == 403, f"error: should require authentication ({response.status_code})"
        snapshot.assert_match(str(response.json()), "ocr_without_authentication")

    def test_ocr_custom_dpi(self, args, test_client, model_id, snapshot):
        """Test OCR with custom DPI setting."""
        MODEL_ID = model_id
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}

        file_path = os.path.join(current_path, "assets/pdf.pdf")
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = test_client.post(f"/v1{ENDPOINT__OCR}", files=files, json={"model": MODEL_ID, "dpi": 300})

        assert response.status_code == 200, f"process OCR with custom DPI ({response.status_code})"
        snapshot_path = os.path.join(
            current_path,
            "snapshots/test_ocr/test_ocr_custom_dpi/ocr_custom_dpi",
        )
        if os.path.exists(snapshot_path):
            with open(snapshot_path) as f:
                expected_snapshot = ast.literal_eval(f.read())
                assert_snapshot_almost_equal(actual=json.dumps(response.json()), expected_snapshot=json.dumps(expected_snapshot), threshold=0.90)
        else:
            snapshot.assert_match(str(response.json()), "ocr_custom_dpi")
