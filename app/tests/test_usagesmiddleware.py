from datetime import datetime

import pytest

from app.schemas.models import ModelType
from app.sql.models import Usage
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__EMBEDDINGS, ENDPOINT__MODELS


@pytest.mark.usefixtures("client")
class TestUsagesMiddleware:
    def test_log_chat_completion(self, client, db_session):
        """Test logging of chat completion request"""
        # Get language model
        response = client.get_without_permissions(f"/v1{ENDPOINT__MODELS}")
        models = response.json()
        model_id = [model for model in models["data"] if model["type"] == ModelType.TEXT_GENERATION][0]["id"]

        params = {"model": model_id, "messages": [{"role": "user", "content": "Hello"}], "stream": False}
        response = client.post_without_permissions(f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params)
        assert response.status_code == 200

        log = db_session.query(Usage).order_by(Usage.id.desc()).first()

        assert log.model == model_id
        assert isinstance(log.datetime, datetime)
        assert log.user is not None
        assert log.prompt_tokens is not None
        assert log.total_tokens is not None
        assert log.completion_tokens is not None
        assert log.duration is not None
        assert log.method == "POST"

    def test_log_embeddings(self, client, db_session):
        """Test logging of embeddings request"""
        before = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__EMBEDDINGS}").count()

        # Get embeddings model
        response = client.get_without_permissions(f"/v1{ENDPOINT__MODELS}")
        models = response.json()["data"]
        model_id = [m for m in models if m["type"] == ModelType.TEXT_EMBEDDINGS_INFERENCE][0]["id"]

        params = {"model": model_id, "input": "Test embeddings"}
        response = client.post_without_permissions(f"/v1{ENDPOINT__EMBEDDINGS}", json=params)
        assert response.status_code == 200

        # Check if log was created
        after = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__EMBEDDINGS}").count()
        assert after - before == 1
        log = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__EMBEDDINGS}").order_by(Usage.id.desc()).first()

        assert log.model == model_id
        assert isinstance(log.datetime, datetime)
        assert log.user is not None
        assert log.duration is not None

    def test_no_log_for_non_model_endpoint(self, client, db_session):
        """Test that non-model endpoints are not logged"""
        previous = db_session.query(Usage).count()

        response = client.get_without_permissions(f"/v1{ENDPOINT__MODELS}")
        assert response.status_code == 200

        # Check that no log was created
        current = db_session.query(Usage).count()
        assert current == previous

    def test_log_with_invalid_json(self, client, db_session):
        """Test handling of invalid JSON in request body"""

        previous = db_session.query(Usage).count()
        invalid_json = "{"  # Invalid JSON
        response = client.post(f"/v1{ENDPOINT__CHAT_COMPLETIONS}", data=invalid_json, headers={"Content-Type": "application/json"})
        assert response.status_code == 422

        # Check that no log was created due to invalid JSON
        current = db_session.query(Usage).count()
        assert current == previous
