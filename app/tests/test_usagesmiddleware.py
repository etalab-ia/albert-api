from datetime import datetime

import pytest

from app.db.models import Log
from app.utils.variables import MODEL_TYPE__LANGUAGE


@pytest.fixture(scope="module")
def setup(args, test_client):
    test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
    # Get a language model for testing
    response = test_client.get("/v1/models")
    models = response.json()
    MODEL_ID = [model for model in models["data"] if model["type"] == MODEL_TYPE__LANGUAGE][0]["id"]
    yield MODEL_ID


@pytest.mark.usefixtures("args", "setup", "test_client")
class TestUsagesMiddleware:
    def test_log_chat_completion(self, args, test_client, setup, db_session):
        """Test logging of chat completion request"""
        MODEL_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}

        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        }
        response = test_client.post("/v1/chat/completions", json=params)
        assert response.status_code == 200

        logs = db_session.query(Log).all()
        assert len(logs) == 1
        log = logs[0]

        assert log.endpoint == "/v1/chat/completions"
        assert log.model == MODEL_ID
        assert isinstance(log.datetime, datetime)
        assert log.user is not None
        # assert log.token_per_sec is not None
        # assert log.req_tokens_nb is not None

    def test_log_embeddings(self, args, test_client, db_session):
        """Test logging of embeddings request"""
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}

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
        logs = db_session.query(Log).filter_by(endpoint="/v1/embeddings").all()
        assert len(logs) == 1
        log = logs[0]

        assert log.endpoint == "/v1/embeddings"
        assert log.model == model_id
        assert isinstance(log.datetime, datetime)
        assert log.user is not None

    def test_no_log_for_non_model_endpoint(self, args, test_client, db_session):
        """Test that non-model endpoints are not logged"""
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        previous = db_session.query(Log).count()

        response = test_client.get("/v1/models")
        assert response.status_code == 200

        # Check that no log was created
        current = db_session.query(Log).count()
        assert current == previous

    def test_log_with_invalid_json(self, args, test_client, db_session):
        """Test handling of invalid JSON in request body"""
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}

        previous = db_session.query(Log).count()
        invalid_json = "{"  # Invalid JSON
        response = test_client.post("/v1/chat/completions", data=invalid_json, headers={"Content-Type": "application/json"})
        assert response.status_code == 422

        # Check that no log was created due to invalid JSON
        current = db_session.query(Log).count()
        assert current == previous
