import os
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.schemas.collections import CollectionVisibility
from app.utils.variables import ENDPOINT__COLLECTIONS, ENDPOINT__FILES


@pytest.fixture(scope="module")
def setup(client: TestClient):
    response = client.post_without_permissions(
        url=f"/v1{ENDPOINT__COLLECTIONS}",
        json={"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PRIVATE},
    )
    assert response.status_code == 201, response.text
    PRIVATE_COLLECTION_ID = response.json()["id"]

    response = client.post_with_permissions(
        url=f"/v1{ENDPOINT__COLLECTIONS}",
        json={"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PUBLIC},
    )
    assert response.status_code == 201, response.text
    PUBLIC_COLLECTION_ID = response.json()["id"]

    yield PRIVATE_COLLECTION_ID, PUBLIC_COLLECTION_ID


@pytest.mark.usefixtures("client", "setup")
class TestFiles:
    def test_upload_pdf_file(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, PUBLIC_COLLECTION_ID = setup

        file_path = "app/tests/integ/assets/pdf.pdf"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
            response = client.post_without_permissions(url=f"/v1{ENDPOINT__FILES}", data=data, files=files)
            file.close()

        assert response.status_code == 201, response.text

    def test_upload_pdf_file_chunker_parameters(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/integ/assets/pdf.pdf"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            data = {"request": '{"collection": "%s", "chunker": {"args": {"chunk_size": 1000}}}' % PRIVATE_COLLECTION_ID}
            response = client.post_without_permissions(url=f"/v1{ENDPOINT__FILES}", data=data, files=files)
            file.close()

        assert response.status_code == 201, response.text

    def test_upload_html_file(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/integ/assets/html.html"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/html")}
            data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
            response = client.post_without_permissions(url=f"/v1{ENDPOINT__FILES}", data=data, files=files)
            file.close()
        assert response.status_code == 201, response.text

    def test_upload_html_file_chunker_parameters(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/integ/assets/html.html"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/html")}
            data = {"request": '{"collection": "%s", "chunker": {"args": {"chunk_size": 1000}}}' % PRIVATE_COLLECTION_ID}
            response = client.post_without_permissions(url=f"/v1{ENDPOINT__FILES}", data=data, files=files)
            file.close()

        assert response.status_code == 201, response.text

    def test_upload_markdown_file(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/integ/assets/markdown.md"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "text/markdown")}
            data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
            response = client.post_without_permissions(url=f"/v1{ENDPOINT__FILES}", data=data, files=files)
            file.close()

        assert response.status_code == 201, response.text

    def test_upload_mardown_file_chunker_parameters(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, PUBLIC_COLLECTION_ID = setup

        file_path = "app/tests/integ/assets/markdown.md"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "text/markdown")}
            data = {"request": '{"collection": "%s", "chunker": {"args": {"chunk_size": 1000}}}' % PRIVATE_COLLECTION_ID}
            response = client.post_without_permissions(url=f"/v1{ENDPOINT__FILES}", data=data, files=files)
            file.close()

        assert response.status_code == 201, response.text

    def test_upload_json_file(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, PUBLIC_COLLECTION_ID = setup

        file_path = "app/tests/integ/assets/json.json"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/json")}
            data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
            response = client.post_without_permissions(url=f"/v1{ENDPOINT__FILES}", data=data, files=files)
            file.close()

        assert response.status_code == 201, response.text

    def test_upload_json_file_wrong_format(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, PUBLIC_COLLECTION_ID = setup

        file_path = "app/tests/integ/assets/json_wrong_format.json"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/json")}
            data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
            response = client.post_without_permissions(url=f"/v1{ENDPOINT__FILES}", data=data, files=files)
            file.close()

        assert response.status_code == 422, response.text

    def test_upload_too_large_file(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, PUBLIC_COLLECTION_ID = setup

        file_path = "app/tests/integ/assets/pdf_too_large.pdf"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
            response = client.post_without_permissions(url=f"/v1{ENDPOINT__FILES}", data=data, files=files)
            file.close()

        assert response.status_code == 413, response.text

    def test_upload_in_public_collection_with_admin(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, PUBLIC_COLLECTION_ID = setup

        file_path = "app/tests/integ/assets/pdf.pdf"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            data = {"request": '{"collection": "%s"}' % PUBLIC_COLLECTION_ID}
            response = client.post_with_permissions(url=f"/v1{ENDPOINT__FILES}", data=data, files=files)
            file.close()
        assert response.status_code == 201, response.text

    def test_upload_in_public_collection_with_user(self, client: TestClient, setup):
        PRIVATE_COLLECTION_ID, PUBLIC_COLLECTION_ID = setup

        file_path = "app/tests/integ/assets/pdf.pdf"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            data = {"request": '{"collection": "%s"}' % PUBLIC_COLLECTION_ID}
            response = client.post_without_permissions(url=f"/v1{ENDPOINT__FILES}", data=data, files=files)
            file.close()

        assert response.status_code == 404, response.text
