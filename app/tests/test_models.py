import urllib
import logging

import pytest

from app.schemas.models import Models, Model

@pytest.mark.usefixtures("args", "session")
class TestModels:
    def test_get_models_response_status_code(self, args, session):
        """Test the GET /models response status code."""
        response = session.get(f"{args['base_url']}/models")
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"

    def test_get_models_response_schemas(self, args, session):
        """Test the GET /models response schemas."""
        response = session.get(f"{args['base_url']}/models")
        response_json = response.json()

        models = Models(data=[Model(**model) for model in response_json["data"]])
        logging.debug(f"models: {models}")

        assert isinstance(models, Models)
        assert all(isinstance(model, Model) for model in models.data)

    def test_get_model_retrieve_model(self, args, session):
        """Test the GET /models/{model_id} response status code."""
        response = session.get(f"{args['base_url']}/models")
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
        response_json = response.json()
        model = response_json["data"][0]["id"]
        logging.debug(f"model: {model}")
        encoded_model = urllib.parse.quote(urllib.parse.quote(model, safe=""), safe="")
        
        response = session.get(f"{args['base_url']}/models/{encoded_model}")
        assert response.status_code == 200, f"error: retrieve model ({response.status_code})"
    
    def test_get_models_retrieve_model_schemas(self, args, session):
        """Test the GET /models/{model_id} response schemas."""
        response = session.get(f"{args['base_url']}/models")
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
        response_json = response.json()
        model = response_json["data"][0]["id"]
        logging.debug(f"model: {model}")
        encoded_model = urllib.parse.quote(urllib.parse.quote(model, safe=""), safe="")
        response = session.get(f"{args['base_url']}/models/{encoded_model}")
        response_json = response.json()
        model = Model(**response_json)

        assert isinstance(model, Model)

    def test_get_models_non_existing_model(self, args, session):
        """Test the GET /models response status code for a non-existing model."""
        response = session.get(f"{args['base_url']}/models/non-existing-model")
        assert response.status_code == 404, f"error: retrieve non-existing model ({response.status_code})"
    
