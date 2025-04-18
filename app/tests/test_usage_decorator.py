import os
import time
from datetime import datetime

import pytest

from app.schemas.models import ModelType
from app.sql.models import Usage
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__MODELS, ENDPOINT__EMBEDDINGS, ENDPOINT__RERANK


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
        assert after - before > 0

        log = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__EMBEDDINGS}").order_by(Usage.id.desc()).first()
        assert log.model is not None
        assert isinstance(log.datetime, datetime)
        assert log.method == "POST"
        assert log.duration > 0

    def test_audio(self, client, db_session):
        """Test logging of an audio transcription request using log_usage decorator."""
        from app.utils.variables import ENDPOINT__AUDIO_TRANSCRIPTIONS

        before = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__AUDIO_TRANSCRIPTIONS}").count()

        # Get embeddings model id
        response = client.get_without_permissions(f"/v1{ENDPOINT__MODELS}")
        models = response.json()["data"]
        model_id = [m for m in models if m["type"] == ModelType.AUTOMATIC_SPEECH_RECOGNITION][0]["id"]

        file_path = "app/tests/assets/audio.mp3"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "audio/mpeg")}
            data = {"model": model_id, "language": "fr", "response_format": "json", "temperature": 0}
            response = client.post_without_permissions(f"/v1{ENDPOINT__AUDIO_TRANSCRIPTIONS}", files=files, data=data)

        assert response.status_code == 200

        try:
            for _ in response.iter_lines():
                pass
        except Exception:
            pass
        finally:
            response.close()

        # Allow some time for the asynchronous logging to complete.
        time.sleep(0.5)

        after = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__AUDIO_TRANSCRIPTIONS}").count()
        assert after - before > 0
        log = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__AUDIO_TRANSCRIPTIONS}").order_by(Usage.id.desc()).first()
        assert isinstance(log.datetime, datetime)
        assert log.method == "POST"
        assert log.model is not None

    def test_classification(self, client, db_session):
        """Test logging of a text classification request using log_usage decorator."""

        before = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__RERANK}").count()

        # Get a test classification model id.
        response = client.get_without_permissions(f"/v1{ENDPOINT__MODELS}")
        models = response.json()["data"]
        model_id = [m for m in models if m["type"] == ModelType.TEXT_CLASSIFICATION][0]["id"]

        params = {"model": model_id, "prompt": "Sort these sentences by relevance.", "input": ["Sentence 1", "Sentence 2", "Sentence 3"]}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__RERANK}", json=params)
        assert response.status_code == 200, response.text

        try:
            for _ in response.iter_lines():
                pass
        except Exception:
            pass
        finally:
            response.close()

        # Allow time for asynchronous logging to complete.
        import time

        time.sleep(0.5)

        after = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__RERANK}").count()
        assert after - before == 1

        log = db_session.query(Usage).filter_by(endpoint=f"/v1{ENDPOINT__RERANK}").order_by(Usage.id.desc()).first()
        assert isinstance(log.datetime, datetime)
        assert log.method == "POST"
        assert not log.prompt_tokens
        assert log.completion_tokens is None
        assert log.total_tokens is None
        assert log.duration > 0
        assert log.model is not None
