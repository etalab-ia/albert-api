import os
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.schemas.collections import CollectionVisibility
from app.schemas.documents import Document, Documents
from app.utils.variables import ENDPOINT__COLLECTIONS, ENDPOINT__DOCUMENTS


@pytest.fixture(scope="module")
def collection(client, record_with_vcr):
    response = client.post_without_permissions(
        url=f"/v1{ENDPOINT__COLLECTIONS}",
        json={"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PRIVATE},
    )
    assert response.status_code == 201, response.text
    collection_id = response.json()["id"]

    yield collection_id


@pytest.mark.usefixtures("client", "collection")
class TestDocuments:
    def test_post_document(self, client: TestClient, collection):
        file_path = "app/tests/integ/assets/pdf.pdf"

        data = {  # with metadata
            "collection": str(collection),
            "output_format": "markdown",
            "force_ocr": "false",
            "languages": "fr",
            "chunk_size": "1000",
            "chunk_overlap": "200",
            "use_llm": "false",
            "paginate_output": "false",
            "chunker": "RecursiveCharacterTextSplitter",
            "length_function": "len",
            "chunk_min_size": "0",
            "is_separator_regex": "false",
            "metadata": '{"string_metadata": "test", "int_metadata": 1, "float_metadata": 1.0, "bool_metadata": true}',
        }

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}", data=data, files=files)
            file.close()

        assert response.status_code == 201, response.text

    def test_get_documents(self, client: TestClient, collection):
        # Create document
        file_path = "app/tests/integ/assets/pdf.pdf"

        data = {  # with empty metadata
            "collection": str(collection),
            "output_format": "markdown",
            "force_ocr": "false",
            "languages": "fr",
            "chunk_size": "1000",
            "chunk_overlap": "200",
            "use_llm": "false",
            "paginate_output": "false",
            "chunker": "RecursiveCharacterTextSplitter",
            "length_function": "len",
            "chunk_min_size": "0",
            "is_separator_regex": "false",
            "metadata": "{}",
        }

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}", data=data, files=files)
            file.close()

        assert response.status_code == 201, response.text
        document_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}")
        assert response.status_code == 200, response.text

        documents = response.json()
        Documents(**documents)  # test output format

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}", params={"collection": collection})
        assert response.status_code == 200, response.text

        documents = response.json()
        Documents(**documents)  # test output format

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}/{document_id}")
        assert response.status_code == 200, response.text

        document = response.json()
        Document(**document)  # test output format

    def test_delete_document(self, client: TestClient, collection):
        # Create document
        file_path = "app/tests/integ/assets/pdf.pdf"

        data = {  # without metadata
            "collection": str(collection),
            "output_format": "markdown",
            "force_ocr": "false",
            "languages": "fr",
            "chunk_size": "1000",
            "chunk_overlap": "200",
            "use_llm": "false",
            "paginate_output": "false",
            "chunker": "RecursiveCharacterTextSplitter",
            "length_function": "len",
            "chunk_min_size": "0",
            "is_separator_regex": "false",
        }

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}", data=data, files=files)
            file.close()

        assert response.status_code == 201, response.text
        document_id = response.json()["id"]

        response = client.delete_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}/{document_id}")
        assert response.status_code == 204, response.text

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}/{document_id}")
        assert response.status_code == 404, response.text
