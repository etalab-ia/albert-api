import logging
import os

from fastapi.testclient import TestClient
import pytest

from app.utils.variables import COLLECTION_DISPLAY_ID__INTERNET, COLLECTION_TYPE__PRIVATE, COLLECTION_TYPE__PUBLIC, MODEL_TYPE__EMBEDDINGS


@pytest.fixture(scope="module")
def setup(client: TestClient):
    response = client.get_user(url="/v1/models", timeout=10)
    models = response.json()
    EMBEDDINGS_MODEL_ID = [model for model in models["data"] if model["type"] == MODEL_TYPE__EMBEDDINGS][0]["id"]
    logging.info(f"test embedings model ID: {EMBEDDINGS_MODEL_ID}")

    response = client.post_user(
        url="/v1/collections",
        json={"name": "test-collection-private", "model": EMBEDDINGS_MODEL_ID, "type": COLLECTION_TYPE__PRIVATE},
    )
    assert response.status_code == 201, response.text
    PRIVATE_COLLECTION_ID = response.json()["id"]

    response = client.post_admin(
        url="/v1/collections",
        json={"name": "test-collection-public", "model": EMBEDDINGS_MODEL_ID, "type": COLLECTION_TYPE__PUBLIC},
    )
    assert response.status_code == 201, response.text
    PUBLIC_COLLECTION_ID = response.json()["id"]

    yield PRIVATE_COLLECTION_ID, PUBLIC_COLLECTION_ID


@pytest.mark.usefixtures("client", "setup", "cleanup")
class TestFiles:
    def test_upload_pdf_file(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/pdf.pdf"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
            response = client.post_user(url="/v1/files", data=data, files=files)

        assert response.status_code == 201, response.text

    def test_upload_internet_collection(self, client: TestClient, setup, snapshot):
        _, _ = setup

        file_path = "app/tests/assets/pdf.pdf"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            data = {"request": '{"collection": "%s"}' % COLLECTION_DISPLAY_ID__INTERNET}
            response = client.post_user(url="/v1/files", data=data, files=files)

        assert response.status_code == 422, response.text
        snapshot.assert_match(str(response.json()), "upload_internet_collection")

    def test_upload_pdf_file_chunker_parameters(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/pdf.pdf"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            data = {"request": '{"collection": "%s", "chunker": {"args": {"chunk_size": 1000}}}' % PRIVATE_COLLECTION_ID}
            response = client.post_user(url="/v1/files", data=data, files=files)

        assert response.status_code == 201, response.text

    def test_upload_html_file(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/html.html"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/html")}
            data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
            response = client.post_user(url="/v1/files", data=data, files=files)

        assert response.status_code == 201, response.text

    def test_upload_html_file_chunker_parameters(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/html.html"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/html")}
            data = {"request": '{"collection": "%s", "chunker": {"args": {"chunk_size": 1000}}}' % PRIVATE_COLLECTION_ID}
            response = client.post_user(url="/v1/files", data=data, files=files)

        assert response.status_code == 201, response.text

    def test_upload_mardown_file(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/markdown.md"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "text/mardown")}
            data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
            response = client.post_user(url="/v1/files", data=data, files=files)

        assert response.status_code == 201, response.text

    def test_upload_mardown_file_chunker_parameters(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/markdown.md"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "text/markdown")}
            data = {"request": '{"collection": "%s", "chunker": {"args": {"chunk_size": 1000}}}' % PRIVATE_COLLECTION_ID}
            response = client.post_user(url="/v1/files", data=data, files=files)

        assert response.status_code == 201, response.text

    def test_upload_json_file(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/json.json"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/json")}
            data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
            response = client.post_user(url="/v1/files", data=data, files=files)

        assert response.status_code == 201, response.text

    def test_upload_json_file_wrong_format(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/json_wrong_format.json"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/json")}
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/json")}
            data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
            response = client.post_user(url="/v1/files", data=data, files=files)

        assert response.status_code == 422, response.text

    def test_upload_too_large_file(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/pdf_too_large.pdf"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
            response = client.post_user(url="/v1/files", data=data, files=files)

        assert response.status_code == 413, response.text

    def test_upload_in_public_collection_with_admin(self, client: TestClient, setup):
        _, PUBLIC_COLLECTION_ID = setup

        file_path = "app/tests/assets/pdf.pdf"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            data = {"request": '{"collection": "%s"}' % PUBLIC_COLLECTION_ID}
            response = client.post_admin(url="/v1/files", data=data, files=files)

        assert response.status_code == 201, response.text

    def test_upload_in_public_collection_with_user(self, client: TestClient, setup):
        _, PUBLIC_COLLECTION_ID = setup

        file_path = "app/tests/assets/pdf.pdf"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            data = {"request": '{"collection": "%s"}' % PUBLIC_COLLECTION_ID}
            response = client.post_user(url="/v1/files", data=data, files=files)

        assert response.status_code == 403, response.text

    # TODO: test no chunker
