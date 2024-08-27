import argparse
import logging
import os
import sys

import requests
import wget

from app.schemas.files import Upload, Uploads, Files, File
from app.schemas.collections import Collections, Collection
from app.schemas.models import Models, Model
from app.schemas.config import PRIVATE_COLLECTION_TYPE, METADATA_COLLECTION, LANGUAGE_MODEL_TYPE, EMBEDDINGS_MODEL_TYPE
from app.utils.security import encode_string

parser = argparse.ArgumentParser(description="Test the response of a LLM model.")  # fmt: off
parser.add_argument("--base-url", type=str, default="http://localhost:8080/v1", help="Base URL of the API")  # fmt: off
parser.add_argument("--api-key", type=str, default="EMPTY", help="API key")  # fmt: off
parser.add_argument("--debug", action="store_true", help="Print debug logs")  # fmt: off

if __name__ == "__main__":
    args = parser.parse_args()
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        format="%(asctime)s:%(levelname)s:%(name)s: %(message)s", level=logging.DEBUG
    )

    COLLECTION = "test"
    FILE_NAME = "my_document.pdf"
    session = requests.session()
    session.headers = {"Authorization": f"Bearer {args.api_key}"}
    user = encode_string(input=args.api_key)
    logging.info(f"test user ID: {user}")

    response = session.get(f"{args.base_url}/models", timeout=10)
    logging.info("test: get_models response status code (200)")
    assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
    models = response.json()
    logging.debug(f"models: {models}")

    logging.info("test: get_models response schemas")
    models["data"] = [Model(**model) for model in models["data"]]
    models = Models(**models)

    EMBEDDINGS_MODEL = [model for model in models.data if model.type == EMBEDDINGS_MODEL_TYPE][0].id
    logging.debug(f"embeddings_model: {EMBEDDINGS_MODEL}")

    response = session.get(f"{args.base_url}/collections", timeout=10)

    logging.info("test: get_collections reponse status code (200)")
    assert response.status_code == 200, f"error: retrieve collections ({response.status_code})"

    collections = response.json()
    logging.debug(f"collections: {collections}")
    logging.info("test: get_files response schemas")
    collections["data"] = [Collection(**collection) for collection in collections["data"]]
    collections = Collections(**collections)

    logging.info("test: before upload file, collection does not exists")
    if COLLECTION in [collection.name for collection in collections.data]:
        response = session.delete(f"{args.base_url}/collections", params={"collection": COLLECTION}, timeout=10)
        assert response.status_code == 204, f"error: delete collection ({response.status_code})"

    logging.info("test: get_collections does not return metadata collection")
    assert METADATA_COLLECTION not in [
        collection.name for collection in collections.data
    ], f"{METADATA_COLLECTION} metadata collection is display in collections"


    if not os.path.exists(FILE_NAME):
        doc_url = "https://www.legifrance.gouv.fr/download/file/rxcTl0H4YnnzLkMLiP4x15qORfLSKk_h8QsSb2xnJ8Y=/JOE_TEXTE"
        wget.download(doc_url, out=FILE_NAME)

    params = {
        "embeddings_model": EMBEDDINGS_MODEL,
        "collection": COLLECTION,
    }
    files = {"files": (os.path.basename(FILE_NAME), open(FILE_NAME, "rb"), "application/pdf")}
    response = session.post(f"{args.base_url}/files", params=params, files=files, timeout=30)

    logging.info("test: upload file response status code (200)")
    assert response.status_code == 200, f"error: upload file ({response.status_code})"

    uploads = response.json()
    logging.debug(f"uploads: {uploads}")

    logging.info("test: get_uploads response schemas")
    uploads["data"] = [Upload(**upload) for upload in uploads["data"]]
    uploads = Uploads(**uploads)

    logging.info("test: upload file response number of uploads")
    assert len(uploads.data) == 1, f"error: number of uploads ({len(uploads)})"

    logging.info("test: upload file response status (success)")
    assert uploads.data[0].status == "success", f"error: upload file ({uploads.data[0].status})"
    file_id = uploads.data[0].id

    logging.info("test: get_files response status code (200)")
    response = session.get(f"{args.base_url}/files/{COLLECTION}", timeout=10)
    assert response.status_code == 200, f"error: retrieve files ({response.status_code})"

    files = response.json()
    logging.debug(f"files: {files}")

    logging.info("test: get_files response schemas")
    files["data"] = [File(**file) for file in files["data"]]
    files = Files(**files)

    logging.info("test: upload file response number of files")
    assert len(files.data) == 1, f"error: number of files ({len(files)})"

    logging.info("test: upload file response file name")
    assert files.data[0].filename == FILE_NAME, f"error: filename ({files.data[0].filename})"

    logging.info("test: upload file response file id")
    assert files.data[0].id == file_id, f"error: file id ({files.data[0].id})"

    response = session.get(f"{args.base_url}/files/{COLLECTION}/{file_id}", timeout=10)
    logging.info("test: get_files with specify file_id response status code (200)")
    assert response.status_code == 200, f"error: retrieve file ({response.status_code} - {response.text})"

    file = response.json()
    logging.debug(f"file: {file}")

    logging.info("test: get_files with specify file_id response schemas")
    file = File(**file)

    logging.info("test: upload file response file name")
    assert file.filename == FILE_NAME, f"error: filename ({file.filename})"

    logging.info("test: upload file response file id")
    assert file.id == file_id, f"error: file id ({file.id})"

    response = session.get(f"{args.base_url}/collections", timeout=10)
    assert response.status_code == 200, f"error: retrieve collections ({response.status_code})"

    collections = response.json()
    logging.debug(f"collections: {collections}")

    logging.info("test: get_collection response schemas")
    collections["data"] = [Collection(**collection) for collection in collections["data"]]
    collections = Collections(**collections)

    logging.info("test: upload file create a collection")
    assert COLLECTION in [
        collection.name for collection in collections.data
    ], f"{COLLECTION} collection does not exists"

    logging.info("test: upload file create a collection with private type")
    collection = [collection for collection in collections.data if collection.name == COLLECTION][0]
    assert (
        collection.type == PRIVATE_COLLECTION_TYPE
    ), f"{COLLECTION} collection type is not {PRIVATE_COLLECTION_TYPE}"

    logging.info("test: upload file create a collection with the right user")
    assert collection.user == user, f"{COLLECTION} collection user is not {user}"

    logging.info("test: upload file create a collection with the right model")
    assert (
        collection.model == EMBEDDINGS_MODEL
    ), f"{COLLECTION} collection model is not {EMBEDDINGS_MODEL}"

    language_model = [model for model in models.data if model.type == LANGUAGE_MODEL_TYPE][0].id
    logging.debug(f"language_model: {language_model}")
    params = {
        "embeddings_model": language_model,
        "collection": COLLECTION,
    }
    files = {"files": (os.path.basename(FILE_NAME), open(FILE_NAME, "rb"), "application/pdf")}
    response = session.post(f"{args.base_url}/files", params=params, files=files, timeout=10)

    logging.info("test: upload file with a language model")
    assert response.status_code == 400, f"error: upload file ({response.status_code} - {response.text})"

    other_embeddings_model = [model for model in models.data if model.type == EMBEDDINGS_MODEL_TYPE and model.id != EMBEDDINGS_MODEL][0].id
    logging.debug(f"other_embeddings_model: {other_embeddings_model}")
    params = {
        "embeddings_model": other_embeddings_model,
        "collection": COLLECTION,
    }
    files = {"files": (os.path.basename(FILE_NAME), open(FILE_NAME, "rb"), "application/pdf")}
    response = session.post(f"{args.base_url}/files", params=params, files=files, timeout=10)

    logging.info("test: upload file with another language model")
    assert response.status_code == 400, f"error: upload file ({response.status_code} - {response.text})"

    params = {
        "embeddings_model": "test",
        "collection": COLLECTION,
    }
    files = {"files": (os.path.basename(FILE_NAME), open(FILE_NAME, "rb"), "application/pdf")}
    response = session.post(f"{args.base_url}/files", params=params, files=files, timeout=10)

    logging.info("test: upload a file with a non existing model")
    assert response.status_code == 404, f"error: upload file ({response.status_code} - {response.text})"

    # upload a 2nd file in the same
    params = {
        "embeddings_model": EMBEDDINGS_MODEL,
        "collection": COLLECTION,
    }
    files = {"files": (os.path.basename(FILE_NAME), open(FILE_NAME, "rb"), "application/pdf")}
    response = session.post(f"{args.base_url}/files", params=params, files=files, timeout=10)

    logging.info("test: upload file response status code (200)")
    assert response.status_code == 200, f"error: upload file ({response.status_code})"

    uploads = response.json()
    logging.debug(f"uploads: {uploads}")
    uploads["data"] = [Upload(**upload) for upload in uploads["data"]]
    uploads = Uploads(**uploads)

    logging.info("test: upload a 2nd file in the same collection response status (success)")
    assert uploads.data[0].status == "success", f"error: upload file ({uploads.data[0].status})"
    file_id = uploads.data[0].id

    logging.info("test: get_files response status code (200)")
    response = session.get(f"{args.base_url}/files/{COLLECTION}", timeout=10)
    assert response.status_code == 200, f"error: retrieve files ({response.status_code})"

    files = response.json()
    logging.debug(f"files: {files}")
    files["data"] = [File(**file) for file in files["data"]]
    files = Files(**files)

    logging.info("test: upload a 2nd file in the same collection response number of files")
    assert len(files.data) == 2, f"error: number of files ({len(files)})"

    logging.info("test: delete a file don't delete the collection if there is another file in the collection")
    response = session.delete(f"{args.base_url}/files/{COLLECTION}/{file_id}", timeout=10)
    assert response.status_code == 204, f"error: delete file ({response.status_code})"

    response = session.get(f"{args.base_url}/collections/{COLLECTION}", timeout=10)
    assert response.status_code == 200, f"error: retrieve collection ({response.status_code})"
    
    # delete file delete collection if it's the last file in the collection
    response = session.get(f"{args.base_url}/files/{COLLECTION}", timeout=10)
    assert response.status_code == 200, f"error: retrieve files ({response.status_code})"
    files = response.json()
    logging.debug(f"files: {files}")
    files["data"] = [File(**file) for file in files["data"]]
    files = Files(**files)

    logging.info("test: delete a file delete the collection if it's the last file in the collection")
    assert len(files.data) == 1, f"error: number of files ({len(files)})"
    response = session.delete(f"{args.base_url}/files/{COLLECTION}/{files.data[0].id}", timeout=10)
    assert response.status_code == 204, f"error: delete file ({response.status_code})"

    logging.info("test: delete a collection delete all files in the collection")
    params = {
        "embeddings_model": EMBEDDINGS_MODEL,
        "collection": COLLECTION,
    }
    files = {"files": (os.path.basename(FILE_NAME), open(FILE_NAME, "rb"), "application/pdf")}
    response = session.post(f"{args.base_url}/files", params=params, files=files, timeout=10)
    assert response.status_code == 200, f"error: upload file ({response.status_code})"

    response = session.delete(f"{args.base_url}/collections/{COLLECTION}", timeout=10)
    assert response.status_code == 204, f"error: delete collection ({response.status_code})"

    response = session.get(f"{args.base_url}/files/{COLLECTION}", timeout=10)
    assert response.status_code == 404, f"error: retrieve files ({response.status_code})"

    # delete metadata collection is impossible
    response = session.delete(f"{args.base_url}/collections/{METADATA_COLLECTION}", timeout=10)
    logging.info("test: delete metadata collection is impossible")
    assert response.status_code == 404, f"error: retrieve collection ({response.status_code})"

    os.remove(FILE_NAME)