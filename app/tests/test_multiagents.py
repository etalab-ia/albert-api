import os
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from app.schemas.collections import CollectionVisibility
from app.utils.variables import ENDPOINT__FILES, ENDPOINT__MULTIAGENTS, ENDPOINT__COLLECTIONS


@pytest.mark.usefixtures("client")
class TestMultiAgents:
    def test_multiagents_basic(self, client: TestClient):
        """Test the /multiagents endpoint with basic request data."""
        # Create a private collection for the test
        collection_name = f"test_collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        # Retrieve the collection id
        collection_id = response.json()["id"]

        # Build payload with the new collection id
        payload = {
            "prompt": "Qui est Albert ?",
            "collections": [collection_id],
            "method": "semantic",
            "k": 3,
            "rff_k": 1,
            "score_threshold": 0.5,
            "max_tokens": 50,
            "max_tokens_intermediate": 20,
            "model": "albert-small",
        }

        # Post to /multiagents with the new collection
        response = client.post_without_permissions(f"/v1{ENDPOINT__MULTIAGENTS}", json=payload)
        assert response.status_code == 200, response.text
        data = response.json()

        # Check response schema
        assert "answer" in data
        assert "choice" in data
        assert "choice_desc" in data
        assert "n_retry" in data
        assert "sources_refs" in data
        assert "sources_content" in data

    def test_multiagent_rag(self, client: TestClient):
        """
        Test the /multiagents endpoint after uploading a PDF file,
        then calling the endpoint similarly to test_multiagents_basic
        but using a different prompt.
        """
        # Create a private collection for the test
        collection_name = f"test_collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text
        collection_id = response.json()["id"]

        # Upload pdf.pdf into the new collection
        file_path = "app/tests/assets/pdf.pdf"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            data = {"request": '{"collection": "%s"}' % collection_id}
            upload_response = client.post_without_permissions(url=f"/v1{ENDPOINT__FILES}", data=data, files=files)
            file.close()
        assert upload_response.status_code == 201, upload_response.text

        # Now test the /multiagents endpoint with a different prompt
        payload = {
            "prompt": "Quel est le montant maximum des actes dont la signature de la première ministre peut être déléguée ?",
            "collections": [collection_id],
            "method": "semantic",
            "k": 3,
            "rff_k": 1,
            "score_threshold": 0.5,
            "max_tokens": 50,
            "max_tokens_intermediate": 20,
            "model": "albert-small",
        }
        response = client.post_without_permissions(f"/v1{ENDPOINT__MULTIAGENTS}", json=payload)
        assert response.status_code == 200, response.text
        data = response.json()

        # Check response schema
        assert "answer" in data
        assert "choice" in data
        assert "choice_desc" in data
        assert "n_retry" in data
        assert "sources_refs" in data
        assert "sources_content" in data
