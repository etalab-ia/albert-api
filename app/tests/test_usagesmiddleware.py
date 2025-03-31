from datetime import datetime
from typing import Generator

from fastapi.testclient import TestClient
import pytest

from app.schemas.models import ModelType
from app.sql.models import Usage


@pytest.fixture(scope="module")
def setup(args, test_client):
    test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}
    # Get a language model for testing
    response = test_client.get("/v1/models")
    models = response.json()
    MODEL_ID = [model for model in models["data"] if model["type"] == ModelType.TEXT_GENERATION][0]["id"]
    yield MODEL_ID


@pytest.fixture(scope="session")
def test_client(app_with_test_db) -> Generator[TestClient, None, None]:
    with TestClient(app=app_with_test_db) as client:
        yield client


@pytest.mark.usefixtures("args", "setup", "test_client")
class TestUsagesMiddleware:
    def test_log_chat_completion(self, args, test_client, setup, db_session):
        """Test logging of chat completion request"""
        MODEL_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}

        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        }
        response = test_client.post("/v1/chat/completions", json=params)
        assert response.status_code == 200

        log = db_session.query(Usage).order_by(Usage.id.desc()).first()

        assert log.endpoint == "/v1/chat/completions"
        assert log.model == MODEL_ID
        assert isinstance(log.datetime, datetime)
        assert log.user == "Etalab (tests)"
        assert log.prompt_tokens is not None
        assert log.total_tokens is not None
        assert log.completion_tokens is not None
        assert log.duration is not None
        assert log.method == "POST"

    def test_log_embeddings(self, args, test_client, db_session):
        """Test logging of embeddings request"""
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}
        before = db_session.query(Usage).filter_by(endpoint="/v1/embeddings").count()

        # Get embeddings model
        response = test_client.get("/v1/models")
        models = response.json()["data"]
        model_id = [m for m in models if m["type"] == "text-embeddings-inference"][0]["id"]

        params = {
            "model": model_id,
            "input": "Test embeddings",
        }
        response = test_client.post("/v1/embeddings", json=params)
        assert response.status_code == 200

        # Check if log was created
        after = db_session.query(Usage).filter_by(endpoint="/v1/embeddings").count()
        assert after - before == 1
        log = db_session.query(Usage).filter_by(endpoint="/v1/embeddings").order_by(Usage.id.desc()).first()

        assert log.endpoint == "/v1/embeddings"
        assert log.model == model_id
        assert isinstance(log.datetime, datetime)
        assert log.user is not None
        assert log.duration is not None

    def test_no_log_for_non_model_endpoint(self, args, test_client, db_session):
        """Test that non-model endpoints are not logged"""
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}
        previous = db_session.query(Usage).count()

        response = test_client.get("/v1/models")
        assert response.status_code == 200

        # Check that no log was created
        current = db_session.query(Usage).count()
        assert current == previous

    def test_log_with_invalid_json(self, args, test_client, db_session):
        """Test handling of invalid JSON in request body"""
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}

        previous = db_session.query(Usage).count()
        invalid_json = "{"  # Invalid JSON
        response = test_client.post("/v1/chat/completions", data=invalid_json, headers={"Content-Type": "application/json"})
        assert response.status_code == 422

        # Check that no log was created due to invalid JSON
        current = db_session.query(Usage).count()
        assert current == previous
