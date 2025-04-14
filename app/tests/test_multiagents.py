import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from app.schemas.collections import CollectionVisibility
from app.utils.variables import ENDPOINT__MULTIAGENTS, ENDPOINT__COLLECTIONS


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
            "writers_model": "writers_model_example",
            "supervisor_model": "supervisor_model_example",
            "max_tokens": 50,
            "max_tokens_intermediate": 20,
            "model": "albert-small",
        }

        # Post to /multiagents with the new collection
        response = client.post_with_permissions(f"/v1{ENDPOINT__MULTIAGENTS}", json=payload)
        assert response.status_code == 200, response.text
        data = response.json()

        # Check response schema
        assert "answer" in data
        assert "choice" in data
        assert "choice_desc" in data
        assert "n_retry" in data
        assert "sources_refs" in data
        assert "sources_content" in data
