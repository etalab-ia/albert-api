import time
from datetime import datetime

import pytest

from app.schemas.models import ModelType
from app.sql.models import Usage
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__MODELS, ENDPOINT__EMBEDDINGS


@pytest.mark.usefixtures("client")
class TestLogUsageDecorator:
    def test_chat_completion_streaming(self, client, db_session):
        """Test logging of a chat completion streaming response using stream_logger_decorator."""
        before = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__CHAT_COMPLETIONS}").count()

        # Use a test model id string for logging and force a StreamingResponse
        response = client.get_without_permissions(f"/v1{ENDPOINT__MODELS}")
        models = response.json()
        model_id = [model for model in models["data"] if model["type"] == ModelType.TEXT_GENERATION][0]["id"]
        params = {"model": model_id, "messages": [{"role": "user", "content": "Raconte moi une histoire"}], "stream": True}
        response = client.post_without_permissions(f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params)
        assert response.status_code == 200

        # Consume all lines from the streaming response to trigger the usage logging.
        try:
            for line in response.iter_lines():
                pass
        except Exception:
            pass
        finally:
            response.close()

        time.sleep(0.5)
        after = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__CHAT_COMPLETIONS}").count()
        assert after - before == 1

        log = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__CHAT_COMPLETIONS}").order_by(Usage.id.desc()).first()
        assert log.model == model_id
        assert isinstance(log.datetime, datetime)
        assert log.method == "POST"

    def test_chat_completion_non_streaming(self, client, db_session):
        """Test logging of a chat completion non-streaming response using stream_logger_decorator."""
        before = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__CHAT_COMPLETIONS}").count()

        response = client.get_without_permissions(f"/v1{ENDPOINT__MODELS}")
        models = response.json()
        model_id = [model for model in models["data"] if model["type"] == ModelType.TEXT_GENERATION][0]["id"]
        params = {"model": model_id, "messages": [{"role": "user", "content": "Raconte moi une histoire"}], "stream": False}
        response = client.post_without_permissions(f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params)
        assert response.status_code == 200

        try:
            for line in response.iter_lines():
                pass
        except Exception:
            pass
        finally:
            response.close()

        time.sleep(0.5)
        after = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__CHAT_COMPLETIONS}").count()
        assert after - before == 1

        log = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__CHAT_COMPLETIONS}").order_by(Usage.id.desc()).first()
        assert log.model == model_id
        assert isinstance(log.datetime, datetime)
        assert log.method == "POST"

    def test_log_embeddings(self, client, db_session):
        """Test logging of an embeddings request using stream_logger_decorator."""
        before = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__EMBEDDINGS}").count()

        # Get embeddings model id
        response = client.get_without_permissions(f"/v1{ENDPOINT__MODELS}")
        models = response.json()["data"]
        model_id = [m for m in models if m["type"] == ModelType.TEXT_EMBEDDINGS_INFERENCE][0]["id"]

        params = {"model": model_id, "input": "Test embeddings"}
        response = client.post_without_permissions(f"/v1{ENDPOINT__EMBEDDINGS}", json=params)
        assert response.status_code == 200

        try:
            for line in response.iter_lines():
                pass
        except Exception:
            pass
        finally:
            response.close()

        time.sleep(0.5)
        after = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__EMBEDDINGS}").count()
        assert after - before == 1

        log = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__EMBEDDINGS}").order_by(Usage.id.desc()).first()
        assert log.model == model_id
        assert isinstance(log.datetime, datetime)
        assert log.method == "POST"
