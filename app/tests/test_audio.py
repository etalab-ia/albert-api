import logging
import os
import pytest

from app.schemas.audio import AudioTranscription
from app.utils.variables import MODEL_TYPE__AUDIO


@pytest.fixture(scope="module")
def setup(args, test_client):
    test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}
    # retrieve model
    response = test_client.get("/v1/models")
    assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
    response_json = response.json()
    model = [model for model in response_json["data"] if model["type"] == MODEL_TYPE__AUDIO][0]
    MODEL_ID = model["id"]
    logging.info(f"test model ID: {MODEL_ID}")

    yield MODEL_ID


@pytest.mark.usefixtures("args", "setup", "test_client")
class TestAudio:
    def test_audio_transcriptions_mp3(self, args, test_client, setup, snapshot):
        """Test the POST /audio/transcriptions endpoint with MP3 file"""
        MODEL_ID = setup

        file_path = "app/tests/assets/audio.mp3"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "audio/mpeg")}
            data = {"model": MODEL_ID, "language": "fr", "response_format": "json", "temperature": 0}
            response = test_client.post(
                "/v1/audio/transcriptions", files=files, data=data, headers={"Authorization": f"Bearer {args["api_key_user"]}"}
            )

        assert response.status_code == 200, response.text
        snapshot.assert_match(str(response.json()), "audio_transcriptions_mp3")
        AudioTranscription(**response.json())  # test output format

    def test_audio_transcriptions_text_output(self, args, test_client, setup, snapshot):
        """Test the POST /audio/transcriptions with text output"""
        MODEL_ID = setup

        file_path = "app/tests/assets/audio.mp3"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "audio/mpeg")}
            data = {"model": MODEL_ID, "language": "fr", "response_format": "text"}
            response = test_client.post(
                "/v1/audio/transcriptions", files=files, data=data, headers={"Authorization": f"Bearer {args["api_key_user"]}"}
            )

        assert response.status_code == 200, response.text
        snapshot.assert_match(str(response.text), "audio_transcriptions_text_output")
        assert isinstance(response.text, str)

    def test_audio_transcriptions_wav(self, args, test_client, setup, snapshot):
        """Test the POST /audio/transcriptions endpoint with WAV file"""
        MODEL_ID = setup

        file_path = "app/tests/assets/audio.wav"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "audio/wav")}
            data = {"model": MODEL_ID, "language": "fr", "response_format": "json", "temperature": 0}
            response = test_client.post(
                "/v1/audio/transcriptions", files=files, data=data, headers={"Authorization": f"Bearer {args["api_key_user"]}"}
            )

        assert response.status_code == 200, response.text
        snapshot.assert_match(str(response.json()), "audio_transcriptions_wav")
        AudioTranscription(**response.json())  # test output format

    def test_audio_transcriptions_invalid_model(self, args, test_client, snapshot):
        """Test the POST /audio/transcriptions with invalid model"""
        MODEL_ID = "invalid-model"

        file_path = "app/tests/assets/audio.mp3"

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "audio/mpeg")}
            data = {"model": MODEL_ID, "language": "fr"}
            response = test_client.post(
                "/v1/audio/transcriptions", files=files, data=data, headers={"Authorization": f"Bearer {args["api_key_user"]}"}
            )

        assert response.status_code == 404, response.text
        snapshot.assert_match(str(response.text), "audio_transcriptions_invalid_model")
