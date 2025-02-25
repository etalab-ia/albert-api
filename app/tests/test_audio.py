import logging
import pytest

from app.schemas.audio import AudioTranscription, AudioTranscriptionVerbose
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
    def test_audio_transcriptions_mp3(self, args, test_client, setup):
        """Test the POST /audio/transcriptions endpoint with MP3 file"""
        MODEL_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}

        with open("app/tests/assets/audio.mp3", "rb") as f:
            files = {"file": ("test.mp3", f, "audio/mpeg")}
            data = {
                "model": MODEL_ID,
                "language": "fr",
                "prompt": "This is a test audio file",
                "response_format": "json",
                "temperature": 0,
                "timestamp_granularities[]": ["segment"],
            }
            response = test_client.post("/v1/audio/transcriptions", files=files, data=data)
            assert response.status_code == 200, f"error: audio transcription failed ({response.status_code})"

            response_json = response.json()
            if data["response_format"] == "verbose_json":
                transcription = AudioTranscriptionVerbose(**response_json)
                assert isinstance(transcription, AudioTranscriptionVerbose)
            else:
                transcription = AudioTranscription(**response_json)
                assert isinstance(transcription, AudioTranscription)

    def test_audio_transcriptions_text_output(self, args, test_client, setup):
        """Test the POST /audio/transcriptions with text output"""
        MODEL_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}

        with open("app/tests/assets/audio.mp3", "rb") as f:
            files = {"file": ("test.mp3", f, "audio/mpeg")}
            data = {"model": MODEL_ID, "language": "fr", "response_format": "text"}
            response = test_client.post("/v1/audio/transcriptions", files=files, data=data)
            assert response.status_code == 200, f"error: audio transcription failed ({response.status_code})"
            assert isinstance(response.text, str), f"error: expected text output ({response.text})"

    def test_audio_transcriptions_wav(self, args, test_client, setup):
        """Test the POST /audio/transcriptions endpoint with WAV file"""
        MODEL_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}

        with open("app/tests/assets/audio.wav", "rb") as f:
            files = {"file": ("test.wav", f, "audio/wav")}
            data = {
                "model": MODEL_ID,
                "language": "fr",
                "prompt": "This is a test audio file",
                "response_format": "json",
                "temperature": 0,
                "timestamp_granularities[]": ["segment"],
            }
            response = test_client.post("/v1/audio/transcriptions", files=files, data=data)
            assert response.status_code == 200, f"error: audio transcription failed ({response.status_code})"

            response_json = response.json()
            if data["response_format"] == "verbose_json":
                transcription = AudioTranscriptionVerbose(**response_json)
                assert isinstance(transcription, AudioTranscriptionVerbose)
            else:
                transcription = AudioTranscription(**response_json)
                assert isinstance(transcription, AudioTranscription)

    def test_audio_transcriptions_invalid_model(self, args, test_client):
        """Test the POST /audio/transcriptions with invalid model"""
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}

        with open("app/tests/assets/audio.mp3", "rb") as f:
            files = {"file": ("test.mp3", f, "audio/mpeg")}
            data = {"model": "invalid-model", "language": "fr"}
            response = test_client.post("/v1/audio/transcriptions", files=files, data=data)
            assert response.status_code == 404, f"error: expected 404 for invalid model ({response.status_code})"
