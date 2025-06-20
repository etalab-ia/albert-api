import os
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from app.schemas.collections import CollectionVisibility
from app.schemas.search import SearchMethod
from app.utils.variables import ENDPOINT__FILES, ENDPOINT__SEARCH, ENDPOINT__COLLECTIONS
from app.utils.context import global_context


@pytest.fixture(scope="module")
def collection_id(client: TestClient, record_with_vcr):
    """
    Create a private collection for the test and return its ID.
    """
    collection_name = f"test_collection_{str(uuid4())}"
    params = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE}
    response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json=params)
    assert response.status_code == 201, response.text
    collection_id = response.json()["id"]
    # Upload pdf.pdf into the new collection
    file_path = "app/tests/integ/assets/pdf.pdf"
    with open(file_path, "rb") as file:
        files = {"file": (os.path.basename(file_path), file, "application/pdf")}
        data = {"request": '{"collection": "%s"}' % collection_id}
        upload_response = client.post_without_permissions(url=f"/v1{ENDPOINT__FILES}", data=data, files=files)
        file.close()
    assert upload_response.status_code == 201, upload_response.text
    return collection_id


@pytest.mark.usefixtures("client", "collection_id")
class TestMultiAgents:
    def test_multiagent_rag(self, client: TestClient, collection_id: str):
        """
        Test the /multiagents endpoint after uploading a PDF file,
        then calling the endpoint similarly to test_multiagents_basic
        but using a different prompt.
        """

        # Now test the /multiagents endpoint with a different prompt
        payload = {
            "prompt": "Quel est le montant maximum des actes dont la signature de la première ministre peut être déléguée ?",
            "collections": [collection_id],
            "method": SearchMethod.MULTIAGENT,
            "k": 3,
            "rff_k": 1,
            "score_threshold": 0.5,
            "max_tokens": 50,
            "max_tokens_intermediate": 20,
            "model": "albert-small",
        }
        response = client.post_without_permissions(f"/v1{ENDPOINT__SEARCH}", json=payload)
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        # Check response schema
        assert len(data) > 0
        assert "choice" in data[0]["chunk"]["metadata"]
        assert "choice_desc" in data[0]["chunk"]["metadata"]

    @pytest.mark.vcr(record_mode="new_episodes")
    def test_multiagent_internet_search(self, client: TestClient, collection_id: str):
        """
        Test the /multiagents endpoint with internet search enabled using pytest marker approach.
        This test uses the @pytest.mark.vcr decorator to override VCR matching settings.
        """
        payload = {
            "prompt": "Recherchez des informations sur la réforme des retraites en France.",
            "collections": [collection_id],
            "method": SearchMethod.MULTIAGENT,
            "k": 3,
            "rff_k": 1,
            "score_threshold": 0.5,
            "max_tokens": 50,
            "max_tokens_intermediate": 20,
            "model": "albert-small",
            "web_search": True,
        }
        response = client.post_without_permissions(f"/v1{ENDPOINT__SEARCH}", json=payload)
        assert response.status_code == 200, response.text

    def test_multiagents_not_available(self, client: TestClient, monkeypatch, collection_id: str):
        """
        Test that MultiAgentsSearchNotAvailableException is raised when multi_agents_search setting is None.
        """
        # Disable multi-agents search in settings
        monkeypatch.setattr(global_context.documents, "multi_agents", None)

        # Build payload with MULTIAGENT method
        payload = {
            "prompt": "Test prompt when disabled",
            "collections": [collection_id],
            "method": SearchMethod.MULTIAGENT,
            "k": 1,
            "rff_k": 1,
            "score_threshold": 0.0,
            "max_tokens": 10,
            "max_tokens_intermediate": 5,
            "model": "albert-small",
        }
        # Expect 400 error due to disabled multi-agents search
        response = client.post_without_permissions(f"/v1{ENDPOINT__SEARCH}", json=payload)
        assert response.status_code == 400, response.text
        # Verify correct exception detail
        assert response.json().get("detail") == "Multi agents search is not available."

    def _run_multiagent_internet_search_test(self, client: TestClient, collection_id: str):
        """Helper method to run the actual test logic"""
        # Patch MultiAgents._get_rank to always return [4]
        with patch("app.utils.multiagents.MultiAgents._get_rank", return_value=[4]):
            # Test the /multiagents endpoint with a prompt
            payload = {
                "prompt": "Recherchez des informations sur la réforme des retraites en France.",
                "collections": [collection_id],
                "method": SearchMethod.MULTIAGENT,
                "k": 3,
                "rff_k": 1,
                "score_threshold": 0.5,
                "max_tokens": 50,
                "max_tokens_intermediate": 20,
                "model": "albert-small",
            }
            response = client.post_without_permissions(f"/v1{ENDPOINT__SEARCH}", json=payload)
            assert response.status_code == 200, response.text
