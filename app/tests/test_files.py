import logging
import os

import pytest

from app.schemas.files import File, Files
from app.utils.variables import EMBEDDINGS_MODEL_TYPE, PRIVATE_COLLECTION_TYPE, PUBLIC_COLLECTION_TYPE


@pytest.fixture(scope="function")
def setup(args, session_user, session_admin):
    response = session_user.get(f"{args["base_url"]}/models", timeout=10)
    models = response.json()
    EMBEDDINGS_MODEL_ID = [model for model in models["data"] if model["type"] == EMBEDDINGS_MODEL_TYPE][0]["id"]
    logging.info(f"test embedings model ID: {EMBEDDINGS_MODEL_ID}")

    response = session_user.post(
        f"{args["base_url"]}/collections", json={"name": "pytest-private", "model": EMBEDDINGS_MODEL_ID, "type": PRIVATE_COLLECTION_TYPE}
    )
    assert response.status_code == 201
    PRIVATE_COLLECTION_ID = response.json()["id"]

    response = session_admin.post(
        f"{args["base_url"]}/collections", json={"name": "pytest-public", "model": EMBEDDINGS_MODEL_ID, "type": PUBLIC_COLLECTION_TYPE}
    )
    assert response.status_code == 201
    PUBLIC_COLLECTION_ID = response.json()["id"]

    yield PRIVATE_COLLECTION_ID, PUBLIC_COLLECTION_ID

    session_user.delete(f"{args["base_url"]}/collections/{PRIVATE_COLLECTION_ID}")
    session_admin.delete(f"{args["base_url"]}/collections/{PUBLIC_COLLECTION_ID}")


@pytest.mark.usefixtures("args", "session_user", "setup", "cleanup_collections")
class TestFiles:
    def test_upload_pdf_file(self, args, session_user, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/pdf_small.pdf"

        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/pdf")}
        data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
        response = session_user.post(f"{args["base_url"]}/files", data=data, files=files)
        assert response.status_code == 201, f"error: upload file ({response.status_code} - {response.text})"
        assert "id" in response.json().keys()

    def test_upload_pdf_file_chunker_parameters(self, args, session_user, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/pdf_small.pdf"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/pdf")}
        data = {"request": '{"collection": "%s", "chunker": {"args": {"chunk_size": 1000}}}' % PRIVATE_COLLECTION_ID}
        response = session_user.post(f"{args["base_url"]}/files", data=data, files=files)
        assert response.status_code == 201, f"error: upload file ({response.status_code} - {response.text})"
        assert "id" in response.json().keys()

    def test_upload_too_large_file(self, args, session_user, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/pdf_large.pdf"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/pdf")}
        data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
        response = session_user.post(f"{args["base_url"]}/files", data=data, files=files)
        assert response.status_code == 413, f"error: upload file ({response.status_code} - {response.text})"

    def test_upload_in_public_collection_with_admin(self, args, session_admin, setup):
        _, PUBLIC_COLLECTION_ID = setup

        file_path = "app/tests/assets/pdf_small.pdf"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/pdf")}
        data = {"request": '{"collection": "%s"}' % PUBLIC_COLLECTION_ID}
        response = session_admin.post(f"{args["base_url"]}/files", data=data, files=files)
        assert response.status_code == 201, f"error: upload file ({response.status_code} - {response.text})"
        assert "id" in response.json().keys()

    def test_upload_in_public_collection_with_user(self, args, session_user, setup):
        _, PUBLIC_COLLECTION_ID = setup

        file_path = "app/tests/assets/pdf_small.pdf"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/pdf")}
        data = {"request": '{"collection": "%s"}' % PUBLIC_COLLECTION_ID}
        response = session_user.post(f"{args["base_url"]}/files", data=data, files=files)
        assert response.status_code == 400, f"error: upload file ({response.status_code} - {response.text})"

    def test_get_files(self, args, session_user, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/pdf_small.pdf"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/pdf")}
        data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
        session_user.post(f"{args["base_url"]}/files", data=data, files=files)

        response = session_user.get(f"{args["base_url"]}/files/{PRIVATE_COLLECTION_ID}")
        assert response.status_code == 200, f"error: upload file ({response.status_code} - {response.text})"

        response_json = response.json()
        files = Files(**response_json)
        assert isinstance(files, Files)

        assert len(files.data) == 1

    def test_get_file(self, args, session_user, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/pdf_small.pdf"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/pdf")}
        data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
        response = session_user.post(f"{args["base_url"]}/files", data=data, files=files)
        file_id = response.json()["id"]

        response = session_user.get(f"{args["base_url"]}/files/{PRIVATE_COLLECTION_ID}/{file_id}")
        assert response.status_code == 200, f"error: upload file ({response.status_code} - {response.text})"

        response_json = response.json()
        file = File(**response_json)
        assert isinstance(file, File)

    def test_delete_file(self, args, session_user, setup):
        PRIVATE_COLLECTION_ID, _ = setup

        file_path = "app/tests/assets/pdf_small.pdf"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/pdf")}
        data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
        response = session_user.post(f"{args["base_url"]}/files", data=data, files=files)
        file_id = response.json()["id"]

        response = session_user.delete(f"{args["base_url"]}/files/{PRIVATE_COLLECTION_ID}/{file_id}")
        assert response.status_code == 204, f"error: delete file ({response.status_code} - {response.text})"

        response = session_user.get(f"{args["base_url"]}/files/{PRIVATE_COLLECTION_ID}")
        files = response.json()["data"]
        assert file_id not in files

    def test_delete_file_in_public_collection_with_admin(self, args, session_admin, setup):
        _, PUBLIC_COLLECTION_ID = setup

        file_path = "app/tests/assets/pdf_small.pdf"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/pdf")}
        data = {"request": '{"collection": "%s"}' % PUBLIC_COLLECTION_ID}
        response = session_admin.post(f"{args["base_url"]}/files", data=data, files=files)
        file_id = response.json()["id"]

        response = session_admin.delete(f"{args["base_url"]}/files/{PUBLIC_COLLECTION_ID}/{file_id}")
        assert response.status_code == 204, f"error: delete file ({response.status_code} - {response.text})"

        response = session_admin.get(f"{args["base_url"]}/files/{PUBLIC_COLLECTION_ID}")
        files = response.json()["data"]
        assert file_id not in files

    def test_delete_file_in_public_collection_with_user(self, args, session_user, session_admin, setup):
        _, PUBLIC_COLLECTION_ID = setup

        file_path = "app/tests/assets/pdf_small.pdf"
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/pdf")}
        data = {"request": '{"collection": "%s"}' % PUBLIC_COLLECTION_ID}
        response = session_admin.post(f"{args["base_url"]}/files", data=data, files=files)
        file_id = response.json()["id"]

        response = session_user.delete(f"{args["base_url"]}/files/{PUBLIC_COLLECTION_ID}/{file_id}")
        assert response.status_code == 400, f"error: delete file ({response.status_code} - {response.text})"
