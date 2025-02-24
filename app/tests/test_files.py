import logging
import os

import pytest


from app.utils.variables import MODEL_TYPE__EMBEDDINGS, COLLECTION_TYPE__PRIVATE, COLLECTION_TYPE__PUBLIC, COLLECTION_DISPLAY_ID__INTERNET


@pytest.fixture(scope="module")
def setup(args, test_client):
    test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
    response = test_client.get(f"{args['base_url']}/models", timeout=10)
    models = response.json()
    EMBEDDINGS_MODEL_ID = [model for model in models["data"] if model["type"] == MODEL_TYPE__EMBEDDINGS][0]["id"]
    logging.info(f"test embedings model ID: {EMBEDDINGS_MODEL_ID}")

    response = test_client.post(
        f"{args['base_url']}/collections", json={"name": "pytest-private", "model": EMBEDDINGS_MODEL_ID, "type": COLLECTION_TYPE__PRIVATE}
    )
    assert response.status_code == 201
    PRIVATE_COLLECTION_ID = response.json()["id"]

    test_client.headers = {"Authorization": f"Bearer {args['api_key_admin']}"}
    response = test_client.post(
        f"{args['base_url']}/collections", json={"name": "pytest-public", "model": EMBEDDINGS_MODEL_ID, "type": COLLECTION_TYPE__PUBLIC}
    )
    assert response.status_code == 201
    PUBLIC_COLLECTION_ID = response.json()["id"]

    yield PRIVATE_COLLECTION_ID, PUBLIC_COLLECTION_ID


@pytest.mark.usefixtures("args", "setup", "cleanup_collections", "test_client")
class TestFiles:
    def test_upload_pdf_file(self, args, test_client, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/pdf.pdf"

        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/pdf")}
        data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        response = test_client.post(f"{args["base_url"]}/files", data=data, files=files)
        assert response.status_code == 201, f"error: upload file ({response.status_code} - {response.text})"

    def test_upload_internet_collection(self, args, test_client, setup, snapshot):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/pdf.pdf"

        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/pdf")}
        data = {"request": '{"collection": "%s"}' % COLLECTION_DISPLAY_ID__INTERNET}
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        response = test_client.post(f"{args["base_url"]}/files", data=data, files=files)
        assert response.status_code == 422
        snapshot.assert_match(str(response.json()), "upload_internet_collection")

    def test_upload_pdf_file_chunker_parameters(self, args, test_client, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/pdf.pdf"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/pdf")}
        data = {"request": '{"collection": "%s", "chunker": {"args": {"chunk_size": 1000}}}' % PRIVATE_COLLECTION_ID}
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        response = test_client.post(f"{args["base_url"]}/files", data=data, files=files)
        assert response.status_code == 201, f"error: upload file ({response.status_code} - {response.text})"

    def test_upload_html_file(self, args, test_client, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/html.html"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/html")}
        data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        response = test_client.post(f"{args["base_url"]}/files", data=data, files=files)
        assert response.status_code == 201, f"error: upload file ({response.status_code} - {response.text})"

    def test_upload_html_file_chunker_parameters(self, args, test_client, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/html.html"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/html")}
        data = {"request": '{"collection": "%s", "chunker": {"args": {"chunk_size": 1000}}}' % PRIVATE_COLLECTION_ID}
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        response = test_client.post(f"{args["base_url"]}/files", data=data, files=files)
        assert response.status_code == 201, f"error: upload file ({response.status_code} - {response.text})"

    def test_upload_mardown_file(self, args, test_client, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/markdown.md"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "text/mardown")}
        data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        response = test_client.post(f"{args["base_url"]}/files", data=data, files=files)
        assert response.status_code == 201, f"error: upload file ({response.status_code} - {response.text})"

    def test_upload_mardown_file_chunker_parameters(self, args, test_client, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/markdown.md"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "text/markdown")}
        data = {"request": '{"collection": "%s", "chunker": {"args": {"chunk_size": 1000}}}' % PRIVATE_COLLECTION_ID}
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        response = test_client.post(f"{args["base_url"]}/files", data=data, files=files)
        assert response.status_code == 201, f"error: upload file ({response.status_code} - {response.text})"

    def test_upload_json_file(self, args, test_client, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/json.json"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/json")}
        data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        response = test_client.post(f"{args["base_url"]}/files", data=data, files=files)
        assert response.status_code == 201, f"error: upload file ({response.status_code} - {response.text})"

    def test_upload_json_file_wrong_format(self, args, test_client, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/json_wrong_format.json"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/json")}
        data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        response = test_client.post(f"{args["base_url"]}/files", data=data, files=files)
        assert response.status_code == 422, f"error: upload file ({response.status_code} - {response.text})"

    def test_upload_too_large_file(self, args, test_client, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/pdf_too_large.pdf"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/pdf")}
        data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        response = test_client.post(f"{args["base_url"]}/files", data=data, files=files)
        assert response.status_code == 413, f"error: upload file ({response.status_code} - {response.text})"

    def test_upload_in_public_collection_with_admin(self, args, test_client, setup):
        _, PUBLIC_COLLECTION_ID = setup

        file_path = "app/tests/assets/pdf.pdf"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/pdf")}
        data = {"request": '{"collection": "%s"}' % PUBLIC_COLLECTION_ID}
        test_client.headers = {"Authorization": f"Bearer {args['api_key_admin']}"}
        response = test_client.post(f"{args["base_url"]}/files", data=data, files=files)
        assert response.status_code == 201, f"error: upload file ({response.status_code} - {response.text})"

    def test_upload_in_public_collection_with_user(self, args, test_client, setup):
        _, PUBLIC_COLLECTION_ID = setup

        file_path = "app/tests/assets/pdf.pdf"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/pdf")}
        data = {"request": '{"collection": "%s"}' % PUBLIC_COLLECTION_ID}
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        response = test_client.post(f"{args["base_url"]}/files", data=data, files=files)
        assert response.status_code == 403, f"error: upload file ({response.status_code} - {response.text})"
