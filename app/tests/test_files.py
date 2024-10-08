import os
import logging
import pytest
import wget

from app.schemas.files import Upload, Uploads, Files, File
from app.schemas.collections import Collections, Collection
from app.schemas.models import Models, Model
from app.schemas.config import PRIVATE_COLLECTION_TYPE, METADATA_COLLECTION, LANGUAGE_MODEL_TYPE, EMBEDDINGS_MODEL_TYPE
from app.utils.security import encode_string


@pytest.fixture(scope="function")
def setup(args, session):
    COLLECTION = "pytest"
    FILE_NAME = "pytest.pdf"
    FILE_URL = "http://www.legifrance.gouv.fr/download/file/rxcTl0H4YnnzLkMLiP4x15qORfLSKk_h8QsSb2xnJ8Y=/JOE_TEXTE"

    if not os.path.exists(FILE_NAME):
        wget.download(FILE_URL, out=FILE_NAME)

    USER = encode_string(input=args["api_key"])
    logging.info(f"test user ID: {USER}")

    yield COLLECTION, FILE_NAME, USER

    if os.path.exists(FILE_NAME):
        os.remove(FILE_NAME)


@pytest.mark.usefixtures("args", "session", "setup")
class TestFiles:
    def get_models(self, args, session):
        response = session.get(f"{args['base_url']}/models", timeout=10)

        models = response.json()
        models["data"] = [Model(**model) for model in models["data"]]
        models = Models(**models)

        return models

    def test_get_collections(self, args, session, setup):
        COLLECTION, _, _ = setup
        response = session.get(f"{args['base_url']}/collections", timeout=10)
        assert response.status_code == 200, f"error: retrieve collections ({response.status_code} - {response.text})"

        collections = response.json()
        collections["data"] = [Collection(**collection) for collection in collections["data"]]
        collections = Collections(**collections)

        assert isinstance(collections, Collections)
        assert all(isinstance(collection, Collection) for collection in collections.data)

        if COLLECTION in [collection.id for collection in collections.data]:
            response = session.delete(f"{args['base_url']}/collections", params={"collection": COLLECTION}, timeout=10)
            assert response.status_code == 204, f"error: delete collection ({response.status_code})"

        assert METADATA_COLLECTION not in [
            collection.id for collection in collections.data
        ], f"{METADATA_COLLECTION} metadata collection is displayed in collections"

    def test_upload_file(self, args, session, setup):
        COLLECTION, FILE_NAME, _ = setup
        models = self.get_models(args, session)
        EMBEDDINGS_MODEL = [model for model in models.data if model.type == EMBEDDINGS_MODEL_TYPE][0].id

        params = {"embeddings_model": EMBEDDINGS_MODEL, "collection": COLLECTION}
        files = {"files": (os.path.basename(FILE_NAME), open(FILE_NAME, "rb"), "application/pdf")}
        response = session.post(f"{args['base_url']}/files", params=params, files=files, timeout=30)

        assert response.status_code == 200, f"error: upload file ({response.status_code} - {response.text})"

        uploads = response.json()
        uploads["data"] = [Upload(**upload) for upload in uploads["data"]]
        uploads = Uploads(**uploads)

        assert len(uploads.data) == 1, f"error: number of uploads ({len(uploads)})"
        assert uploads.data[0].status == "success", f"error: upload file ({uploads.data[0].status} - {response.text})"

        file_id = uploads.data[0].id

        response = session.get(f"{args['base_url']}/files/{COLLECTION}", timeout=10)
        assert response.status_code == 200, f"error: retrieve files ({response.status_code})"

        files = response.json()
        files["data"] = [File(**file) for file in files["data"]]
        assert len(files["data"]) == 1, f"error: number of files ({len(files)})"
        files = Files(**files)
        assert files.data[0].filename == FILE_NAME, f"error: filename ({files.data[0].filename})"
        assert files.data[0].id == file_id, f"error: file id ({files.data[0].id})"

    def test_collection_creation(self, args, session, setup):
        COLLECTION, _, USER = setup

        response = session.get(f"{args['base_url']}/collections", timeout=10)
        assert response.status_code == 200, f"error: retrieve collections ({response.status_code})"

        collections = response.json()
        collections["data"] = [Collection(**collection) for collection in collections["data"]]
        collections = Collections(**collections)

        assert COLLECTION in [collection.id for collection in collections.data], f"{COLLECTION} collection does not exist"

        collection = [collection for collection in collections.data if collection.id == COLLECTION][0]
        assert collection.type == PRIVATE_COLLECTION_TYPE, f"{COLLECTION} collection type is not {PRIVATE_COLLECTION_TYPE}"
        assert collection.user == USER, f"{COLLECTION} collection user is not {USER}"

    def test_upload_with_wrong_model(self, args, session, setup):
        COLLECTION, FILE_NAME, _ = setup
        models = self.get_models(args, session)

        language_model = [model for model in models.data if model.type == LANGUAGE_MODEL_TYPE][0].id
        params = {
            "embeddings_model": language_model,
            "collection": COLLECTION,
        }
        files = {"files": (os.path.basename(FILE_NAME), open(FILE_NAME, "rb"), "application/pdf")}
        response = session.post(f"{args['base_url']}/files", params=params, files=files, timeout=10)

        assert response.status_code == 400, f"error: upload file ({response.status_code} - {response.text})"

    def test_upload_with_non_existing_model(self, args, session, setup):
        COLLECTION, FILE_NAME, _ = setup

        params = {
            "embeddings_model": "test",
            "collection": COLLECTION,
        }
        files = {"files": (os.path.basename(FILE_NAME), open(FILE_NAME, "rb"), "application/pdf")}
        response = session.post(f"{args['base_url']}/files", params=params, files=files, timeout=10)

        assert response.status_code == 404, f"error: upload file ({response.status_code} - {response.text})"

    def test_delete_file(self, args, session, setup):
        COLLECTION, FILE_NAME, _ = setup
        models = self.get_models(args, session)
        EMBEDDINGS_MODEL = [model for model in models.data if model.type == EMBEDDINGS_MODEL_TYPE][0].id
        params = {"embeddings_model": EMBEDDINGS_MODEL, "collection": COLLECTION}
        files = {"files": (os.path.basename(FILE_NAME), open(FILE_NAME, "rb"), "application/pdf")}
        response = session.post(f"{args['base_url']}/files", params=params, files=files, timeout=30)

        uploads = response.json()
        uploads["data"] = [Upload(**upload) for upload in uploads["data"]]
        uploads = Uploads(**uploads)
        file_id = uploads.data[0].id

        response = session.delete(f"{args['base_url']}/files/{COLLECTION}/{file_id}", timeout=10)
        assert response.status_code == 204, f"error: delete file ({response.status_code})"

        response = session.get(f"{args['base_url']}/collections/{COLLECTION}", timeout=10)
        assert response.status_code == 200, f"error: retrieve collection ({response.status_code} - {response.text})"

        response = session.get(f"{args['base_url']}/files/{COLLECTION}", timeout=10)
        assert response.status_code == 200, f"error: retrieve files ({response.status_code} - {response.text})"
        files = response.json()
        assert len(files["data"]) == 1, "error: the first upload file must be still in the bucket"

        file_id = files["data"][0]["id"]

        response = session.delete(f"{args['base_url']}/files/{COLLECTION}/{file_id}", timeout=10)
        assert response.status_code == 204, f"error: delete last file ({response.status_code})"

        # delete last file must delete the collection
        response = session.get(f"{args['base_url']}/files/{COLLECTION}", timeout=10)
        assert response.status_code == 404, f"error: retrieve files ({response.status_code})"

    def test_delete_collection(self, args, session, setup):
        COLLECTION, _, _ = setup
        file_id = self.test_upload_file(args, session, setup)

        # Delete the collection
        response = session.delete(f"{args['base_url']}/collections/{COLLECTION}", timeout=10)
        assert response.status_code == 204, f"error: delete collection ({response.status_code})"

        # Verify the collection was deleted
        response = session.get(f"{args['base_url']}/collections/{COLLECTION}", timeout=10)
        assert response.status_code == 404, f"error: collection should not exist ({response.status_code} - {response.text})"

    def test_delete_metadata_collection(self, args, session):
        response = session.delete(f"{args['base_url']}/collections/{METADATA_COLLECTION}", timeout=10)
        assert response.status_code == 404, f"error: delete metadata collection ({response.status_code} - {response.text})"
