from app.schemas.chat import ChatCompletion
from app.schemas.config import EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE
from app.schemas.models import Model, Models
import logging
import os
import pytest
import wget


@pytest.mark.usefixtures("args", "session")
class TestTools:
    FILE_URL = "https://www.legifrance.gouv.fr/download/file/rxcTl0H4YnnzLkMLiP4x15qORfLSKk_h8QsSb2xnJ8Y=/JOE_TEXTE"
    FILE_PATH = "test.pdf"
    COLLECTION = "pytest"

    def test_baserag_tool_response_status_code(self, args, session):
        """Setup for other tests."""

        # delete collection if exists
        response = session.get(f"{args["base_url"]}/collections", params={"collection": self.COLLECTION}, timeout=10)
        if response.status_code == 200:
            response = session.delete(
                f"{args["base_url"]}/collections",
                params={"collection": self.COLLECTION},
                timeout=10,
            )
            assert response.status_code == 204, f"error: delete collection ({response.status_code})"
            logging.info(f"collection {self.COLLECTION} deleted")

        # download file
        if not os.path.exists(self.FILE_PATH):
            wget.download(self.FILE_URL, out=self.FILE_PATH)
            logging.info(f"file {self.FILE_PATH} downloaded")

        # get a embeddings_model
        response = session.get(f"{args["base_url"]}/models", timeout=10)
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
        models = response.json()
        models = Models(data=[Model(**model) for model in models["data"]])
        self.EMBEDDINGS_MODEL = [model for model in models.data if model.type == EMBEDDINGS_MODEL_TYPE][0].id
        logging.debug(f"embeddings_model: {self.EMBEDDINGS_MODEL}")

        # upload file
        params = {
            "embeddings_model": self.EMBEDDINGS_MODEL,
            "collection": self.COLLECTION,
        }
        files = {
            "files": (
                os.path.basename(self.FILE_PATH),
                open(self.FILE_PATH, "rb"),
                "application/pdf",
            )
        }
        response = session.post(f"{args["base_url"]}/files", params=params, files=files, timeout=30)
        assert response.status_code == 200, f"error: upload file ({response.status_code})"

        # get a language model
        response = session.get(f"{args["base_url"]}/models", timeout=10)
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
        models = response.json()
        models = Models(data=[Model(**model) for model in models["data"]])
        self.LANGUAGE_MODEL = [model for model in models.data if model.type == LANGUAGE_MODEL_TYPE][0].id
        logging.debug(f"language_model: {self.LANGUAGE_MODEL}")

        # test baserag tool
        data = {
            "model": self.LANGUAGE_MODEL,
            "messages": [{"role": "user", "content": "Qui est Ulrich Tan ?"}],
            "stream": False,
            "n": 1,
            "tools": [
                {
                    "function": {
                        "name": "BaseRAG",
                        "parameters": {
                            "embeddings_model": self.EMBEDDINGS_MODEL,
                            "collections": [self.COLLECTION],
                            "k": 2,
                        },
                    },
                    "type": "function",
                }
            ],
        }
        response = session.post(f"{args["base_url"]}/chat/completions", json=data, timeout=30)
        assert response.status_code == 200, f"error: chat completions ({response.status_code})"
        response = response.json()
        response = ChatCompletion(**response)

        assert response.choices[0].message.content is not None, "error: response content is None"
        logging.debug(response.choices[0].message.content)
        logging.debug(response.metadata)

        # check if metadata
        assert "BaseRAG" in response.metadata[0], "error: metadata BaseRAG not found"

        # test with wrong embeddings_model
        response = session.get(f"{args["base_url"]}/models", timeout=10)
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
        models = response.json()
        models = Models(data=[Model(**model) for model in models["data"]])
        wrong_embeddings_model = [model for model in models.data if model.type == EMBEDDINGS_MODEL_TYPE and model.id != self.EMBEDDINGS_MODEL][0].id
        logging.debug(f"wrong_embeddings_model: {wrong_embeddings_model}")

        data = {
            "model": self.LANGUAGE_MODEL,
            "messages": [{"role": "user", "content": "Qui est Ulrich Tan ?"}],
            "stream": False,
            "n": 1,
            "tools": [
                {
                    "function": {
                        "name": "BaseRAG",
                        "parameters": {
                            "embeddings_model": wrong_embeddings_model,
                            "collections": [self.COLLECTION],
                            "k": 2,
                        },
                    },
                    "type": "function",
                }
            ],
        }
        response = session.post(f"{args["base_url"]}/chat/completions", json=data, timeout=30)
        assert response.status_code == 400, f"error: chat completions ({response.status_code})"
