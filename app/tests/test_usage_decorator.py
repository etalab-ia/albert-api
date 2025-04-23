from datetime import datetime
import time

import pytest

from app.schemas.models import ModelType
from app.sql.models import Usage
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__MODELS


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
        assert after - before > 0
        log = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__CHAT_COMPLETIONS}").order_by(Usage.id.desc()).first()
        assert log.model is not None
        assert log.request_model is not None
        assert isinstance(log.datetime, datetime)
        assert log.method == "POST"
        assert log.prompt_tokens > 0
        assert log.completion_tokens > 0
        assert log.total_tokens > 0
        assert log.duration > 0
        assert log.status == 200
        assert log.request_model is not None
        assert log.status == 200

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
        assert after - before > 0

        log = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__CHAT_COMPLETIONS}").order_by(Usage.id.desc()).first()
        assert log.model
        assert isinstance(log.datetime, datetime)
        assert log.method == "POST"
        assert log.prompt_tokens > 0
        assert log.completion_tokens > 0
        assert log.total_tokens > 0
        assert log.duration > 0
