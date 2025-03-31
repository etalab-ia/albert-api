import logging
import os

from fastapi.testclient import TestClient
import pytest
from pytest_snapshot.plugin import Snapshot

from app.schemas.audio import AudioTranscription
from app.schemas.models import ModelType


@pytest.fixture(scope="module")
def setup(client: TestClient):
    response = client.get_without_permissions(url="/v1/models")
    assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
    response_json = response.json()
    model = [model for model in response_json["data"] if model["type"] == ModelType.AUTOMATIC_SPEECH_RECOGNITION][0]
    MODEL_ID = model["id"]
    logging.info(f"test model ID: {MODEL_ID}")

    yield MODEL_ID


@pytest.mark.usefixtures("client", "setup")
class TestAudio:
    def test_audio_transcriptions_mp3(self, client: TestClient, setup: str, snapshot: Snapshot) -> None:
        """Test the POST /audio/transcriptions endpoint with MP3 file"""
        MODEL_ID = setup

        file_path = "app/tests/assets/audio.mp3"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "audio/mpeg")}
            data = {"model": MODEL_ID, "language": "fr", "response_format": "json", "temperature": 0}
            response = client.post_without_permissions("/v1/audio/transcriptions", files=files, data=data)

        assert response.status_code == 200, response.text
        snapshot.assert_match(str(response.json()), snapshot_name="audio_transcriptions_mp3")
        AudioTranscription(**response.json())  # test output format

    def test_audio_transcriptions_text_output(self, client: TestClient, setup: str, snapshot: Snapshot) -> None:
        """Test the POST /audio/transcriptions with text output"""
        MODEL_ID = setup

        file_path = "app/tests/assets/audio.mp3"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "audio/mpeg")}
            data = {"model": MODEL_ID, "language": "fr", "response_format": "text"}
            response = client.post_without_permissions("/v1/audio/transcriptions", files=files, data=data)

        assert response.status_code == 200, response.text
        snapshot.assert_match(str(response.text), "audio_transcriptions_text_output")
        assert isinstance(response.text, str)

    def test_audio_transcriptions_wav(self, client: TestClient, setup: str, snapshot: Snapshot) -> None:
        """Test the POST /audio/transcriptions endpoint with WAV file"""
        MODEL_ID = setup

        file_path = "app/tests/assets/audio.wav"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "audio/wav")}
            data = {"model": MODEL_ID, "language": "fr", "response_format": "json", "temperature": 0}
            response = client.post_without_permissions("/v1/audio/transcriptions", files=files, data=data)

        assert response.status_code == 200, response.text
        snapshot.assert_match(str(response.json()), snapshot_name="audio_transcriptions_wav")
        AudioTranscription(**response.json())  # test output format

    def test_audio_transcriptions_invalid_model(self, client: TestClient, setup: str, snapshot: Snapshot) -> None:
        """Test the POST /audio/transcriptions with invalid model"""
        MODEL_ID = "invalid-model"

        file_path = "app/tests/assets/audio.mp3"

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "audio/mpeg")}
            data = {"model": MODEL_ID, "language": "fr"}
            response = client.post_without_permissions("/v1/audio/transcriptions", files=files, data=data)

        assert response.status_code == 404, response.text
        snapshot.assert_match(str(response.text), snapshot_name="audio_transcriptions_invalid_model")
